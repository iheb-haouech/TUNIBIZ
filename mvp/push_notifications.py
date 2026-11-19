"""Opt-in FCM device registration and transactional purchase notification outbox."""
import hashlib
import re
import time
from flask import jsonify, session

TOKEN = re.compile(r'[A-Za-z0-9_:\-]{20,4096}\Z')
DEVICE = re.compile(r'[a-f0-9]{32}\Z')

def install(app, db, payload, err, throttle):
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS push_devices (
          device_id TEXT PRIMARY KEY, token TEXT NOT NULL UNIQUE,
          session_digest TEXT NOT NULL REFERENCES wallet_sessions(digest) ON DELETE CASCADE,
          updated INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS push_outbox (
          id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL REFERENCES push_devices(device_id) ON DELETE CASCADE,
          scan_id TEXT NOT NULL REFERENCES store_scan_requests(id) ON DELETE CASCADE,
          created INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, next_attempt INTEGER NOT NULL DEFAULT 0, UNIQUE(device_id,scan_id)
        );
        CREATE INDEX IF NOT EXISTS push_device_session ON push_devices(session_digest);
        CREATE TRIGGER IF NOT EXISTS push_scan_decision
        AFTER UPDATE OF state ON store_scan_requests
        WHEN OLD.state='pending' AND NEW.state IN ('approved','rejected')
        BEGIN
          INSERT OR IGNORE INTO push_outbox(device_id,scan_id,created)
          SELECT d.device_id,NEW.id,CAST(strftime('%s','now') AS INTEGER)
          FROM push_devices d JOIN wallet_sessions s ON s.digest=d.session_digest
          WHERE s.account_id=NEW.account_id AND s.expires>CAST(strftime('%s','now') AS INTEGER);
        END;
        """)

        cols={r['name'] for r in c.execute('PRAGMA table_info(push_outbox)')}
        if 'attempts' not in cols:c.execute('ALTER TABLE push_outbox ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0')
        if 'next_attempt' not in cols:c.execute('ALTER TABLE push_outbox ADD COLUMN next_attempt INTEGER NOT NULL DEFAULT 0')

    def session_digest(c):
        raw = session.get('wallet_token')
        if not isinstance(raw,str):
            return None
        digest = hashlib.sha256(raw.encode()).hexdigest()
        row = c.execute('SELECT digest FROM wallet_sessions WHERE digest=? AND expires>?',(digest,int(time.time()))).fetchone()
        return row['digest'] if row else None

    @app.post('/api/push/register')
    def push_register():
        p=payload()
        device,token=p.get('device_id'),p.get('token')
        if p.get('consent') is not True or not isinstance(device,str) or not DEVICE.fullmatch(device) or not isinstance(token,str) or not TOKEN.fullmatch(token):
            return err('Consentement ou identifiant de notification invalide',400)
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            digest=session_digest(c)
            if not digest:
                return err('Connexion requise',401)
        if not throttle('push_register',digest,30):
            return err('Trop de tentatives',429)
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            digest=session_digest(c)
            if not digest:
                return err('Connexion requise',401)
            existing=c.execute('SELECT * FROM push_devices WHERE device_id=? OR token=?',(device,token)).fetchall()
            if any(r['session_digest']!=digest and r['token']!=token for r in existing):
                return err('Identifiant appareil indisponible',409)
            # Re-registration after a new login replaces any previous token binding.
            for r in existing:
                if r['device_id']!=device or r['session_digest']!=digest or r['token']!=token:
                    c.execute('DELETE FROM push_devices WHERE device_id=?',(r['device_id'],))
            c.execute('INSERT INTO push_devices VALUES(?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET updated=excluded.updated',(device,token,digest,int(time.time())))
        return jsonify(ok=True)

    @app.post('/api/push/unregister')
    def push_unregister():
        device=payload().get('device_id')
        if not isinstance(device,str) or not DEVICE.fullmatch(device):
            return err('Identifiant appareil invalide',400)
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            digest=session_digest(c)
            if not digest:
                return err('Connexion requise',401)
            c.execute('DELETE FROM push_devices WHERE device_id=? AND session_digest=?',(device,digest))
        return jsonify(ok=True)
