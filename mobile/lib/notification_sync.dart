import 'api.dart';

/// A cloud message is a hint. Its account and data are revalidated by the server.
class ConfirmedNotificationSync {
 final Api api;final Future<void> Function() refresh;final Future<bool> Function() allowed;final Future<void> Function(String) show;
 bool busy=false;
 ConfirmedNotificationSync({required this.api,required this.refresh,required this.allowed,required this.show});
 Future<void> receive()async{
  if(busy||!api.signedIn)return;busy=true;final epoch=api.sessionEpoch;
  bool current()=>api.signedIn&&epoch==api.sessionEpoch;
  try{
   if(!await allowed()||!current())return;
   final data=await api.call('/commerce/profile');if(!current())return;
   await refresh();if(!await allowed()||!current())return;
   final rows=data['notifications'];if(rows is! List||rows.isEmpty||rows.first is! Map)return;
   final id=rows.first['id'];if(id is int&&id>0)await show('notice:$id');
  }catch(_){/* No notification can be confirmed by a failed or unauthorized read. */}finally{busy=false;}
 }
}
