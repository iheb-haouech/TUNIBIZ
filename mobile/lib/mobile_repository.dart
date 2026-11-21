import 'mobile_support.dart';
import 'api.dart';
import 'secure_cache.dart';

/// Seeds are existing, owner-approved public QR links, never invented partners.
const pilotPartners=<String,String>{'cd8f57567e0a88135bf84f51':'assets/makhzen_djerbi.jpg'};
class MobileHome {
 final Map<String,dynamic> home;final Map<String,dynamic>? wallet,profile;
 final bool offline;
 const MobileHome(this.home,this.wallet,this.profile,this.offline);
}
class MobileRepository {
 final Api api;MobileRepository(this.api);
 Future<Map<String,dynamic>> partner(String slug)async{
  final response=await api.cached('/store/$slug'),raw=response['shop'];
  if(raw is! Map||raw['slug']!=slug||raw['id'] is! int)throw const ApiUnavailable('Établissement indisponible.');
  return summary(Map<String,dynamic>.from(raw),cached:response['_cached']==true);
 }
 Map<String,dynamic> summary(Map<String,dynamic> raw,{bool cached=false})=>{...raw,'partial':true,'photoAsset':pilotPartners[raw['slug']],'category':raw['category']??'other','category_detail':raw['category_detail']??'Établissement partenaire','address':'','offers_count':0,'offers':<dynamic>[],'nearby':<dynamic>[],'gallery':<dynamic>[],'rewards':<dynamic>[],'history':<dynamic>[],'coupons':<dynamic>[],'joined':false,'favorite':false,'description':'','hours':'','social':raw['social']??'','_cached':cached};
 Future<List<Map<String,dynamic>>> approvedPartners()async{
  final support=MobileSupport(api);await support.load();if(!support.has('public_partners'))return [];
  try{final d=await api.cached('/mobile/partners');return [for(final raw in d['stores'] as List)if(raw is Map&&raw['id'] is int&&raw['slug'] is String&&raw['name'] is String)summary(Map<String,dynamic>.from(raw),cached:d['_cached']==true)];}on SessionExpired{rethrow;}catch(_){return [];}
 }
 Future<MobileHome> home()async{
  Map<String,dynamic> h;
  try{h=await api.cached('/commerce/home');}
  on ApiUnavailable catch(error) {if(!error.cacheable)rethrow;final saved=await SecureCache.read(api.scope,'/commerce/home');if(saved==null)rethrow;h=saved;}
  Map<String,dynamic>? wallet,profile;
  if(h['profile']!=null){final values=await Future.wait([api.cached('/wallet'),api.cached('/commerce/profile')]);wallet=values[0];profile=values[1];}
  final stores=<Map<String,dynamic>>[for(final row in h['stores'] as List? ?? [])Map<String,dynamic>.from(row as Map)];
  if(h['_cached']!=true&&wallet?['_cached']!=true&&profile?['_cached']!=true){for(final row in await approvedPartners()){if(!stores.any((s)=>s['id']==row['id']))stores.add(row);}}
  for(final slug in pilotPartners.keys){
   if(stores.any((row)=>row['slug']==slug))continue;
   try{final row=await partner(slug);if(!stores.any((s)=>s['id']==row['id']))stores.add(row);}on SessionExpired{rethrow;}catch(_){/* No active public QR response means no fallback listing. */}
  }
  for(final card in wallet?['cards'] as List? ?? []){for(final row in stores){if(row['id']==card['shop_id']){row['joined']=true;row['points']=card['points'];row['card_id']=card['id'];}}}
  h={...h,'stores':stores,'categories':stores.map((s)=>s['category']).whereType<String>().toSet().toList()};
  final offline=h['_cached']==true||wallet?['_cached']==true||profile?['_cached']==true||stores.any((s)=>s['_cached']==true);
  return MobileHome(h,wallet,profile,offline);
 }
 Future<Map<String,dynamic>?> publicPartnerById(int id)async{
  for(final slug in pilotPartners.keys){try{final row=await partner(slug);if(row['id']==id)return row;}catch(_){}}
  for(final row in await approvedPartners()){if(row['id']==id)return row;}
  return null;
 }
}
