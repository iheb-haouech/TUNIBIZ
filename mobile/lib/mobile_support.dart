import 'api.dart';

/// Older servers remain usable; additional controls require advertised real APIs.
class MobileSupport {
 static final _instances=Expando<MobileSupport>();
 factory MobileSupport(Api api)=>_instances[api]??=MobileSupport._(api);
 MobileSupport._(this.api);
 final Api api;Map<String,dynamic> features={};bool loaded=false;Future<void>? _loading;
 bool has(String feature)=>features[feature]==true;
 Future<void> load({bool force=false}){
  if(_loading!=null)return _loading!;
  if(loaded&&!force)return Future.value();
  return _loading=_fetch();
 }
 Future<void> _fetch()async{
  try{final d=await api.cached('/mobile/capabilities');features=d['version']==1&&d['_cached']!=true&&d['features'] is Map?Map<String,dynamic>.from(d['features']):{};}
  catch(_){features={};}finally{loaded=true;_loading=null;}
 }
}
