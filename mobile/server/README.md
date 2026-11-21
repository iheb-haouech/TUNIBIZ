# Optional server support for TUNIBIZ Android 0.6.0

This module closes the identified API gaps without a database migration or web design change:

- Authenticated, shop-scoped QR scan history with filters and stable cursor pagination. Expiry is computed during reads without changing transactions.
- Category editing by the authenticated, active merchant, with server validation and an audit record. The flat subscription amount is unchanged.
- Public discovery of published partners and incomplete partners explicitly authorized through `TUNIBIZ_PUBLIC_PARTNER_SLUGS`. A whitelist entry authorizes public name, city, category and professional social links; private photos and customer data are excluded.

The Android app enables these controls only when `/api/mobile/capabilities` advertises them. An older server continues serving the existing native features; no fake history is generated.

## Deployment by the server owner

Review `mobile_support_v060.py` and `install_mobile_support.py` from this same source revision. Place both in a temporary folder on PythonAnywhere. From the **actual mvp directory used by WSGI**, run:

```bash
python /path/to/install_mobile_support.py --dry-run
python /path/to/install_mobile_support.py --database /absolute/path/to/existing/tunibiz.sqlite
```

The apply command requires the existing database path and verifies a consistent, read-only SQLite backup before changing source. It backs up the original app.py and rolls back source if a file write fails. No SQL updates or schema migrations are performed by installation. Reload the web app after applying.

To authorize the existing pilot as a public incomplete partner, explicitly configure the server environment:

```text
TUNIBIZ_PUBLIC_PARTNER_SLUGS=cd8f57567e0a88135bf84f51
```

Do not add a private shop without authorization. Published shops do not need this whitelist.

Verify `/api/mobile/capabilities` is 200 and unauthenticated `/api/mobile/business/scans` is denied. Test category changes and history with authorized test accounts only. Existing accounts, points, QR slugs, the APK download URL and website assets are retained.

FCM delivery still requires the existing trusted `mvp/fcm_dispatch.py --send` worker with server-side Google credentials. No service-account secret belongs in the APK. A configured client or successful device registration alone is not proof of delivery.
