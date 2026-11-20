import 'dart:convert';
import 'session_vault.dart';

/// Read-only snapshots. Android persists these through the existing AES-GCM vault.
class SecureCache {
 static final Map<String,Map<String,dynamic>> _memory={};
 static String namespace(String? scope)=>scope=='merchant'?'merchant_cache':scope=='wallet'?'wallet_cache':'public_cache';
 static Future<Map<String,dynamic>> _load(String? scope)async{
  final name=namespace(scope);if(_memory.containsKey(name))return _memory[name]!;
  try{final raw=await SessionVault.read(name);if(raw!=null){final decoded=jsonDecode(raw);if(decoded is Map<String,dynamic>){_memory[name]=decoded;return decoded;}}}catch(_){}
  return _memory[name]={};
 }
 static Future<void> put(String? scope,String key,Map<String,dynamic> data)async{
  final entries=await _load(scope);entries[key]={'at':DateTime.now().millisecondsSinceEpoch,'data':data};
  while(entries.length>12){entries.remove(entries.keys.first);}
  var encoded=jsonEncode(entries);while(encoded.length>220000&&entries.length>1){entries.remove(entries.keys.first);encoded=jsonEncode(entries);}
  if(encoded.length<=220000)await SessionVault.write(namespace(scope),encoded);
 }
 static Future<Map<String,dynamic>?> read(String? scope,String key)async{
  final entry=(await _load(scope))[key];if(entry is! Map||entry['at'] is! num||entry['data'] is! Map)return null;
  if(DateTime.now().millisecondsSinceEpoch-(entry['at'] as num)>24*60*60*1000)return null;
  return {...Map<String,dynamic>.from(entry['data'] as Map),'_cached':true,'_savedAt':entry['at']};
 }
 static Future<void> clear(String? scope)async{_memory.remove(namespace(scope));await SessionVault.write(namespace(scope),null);}
}
