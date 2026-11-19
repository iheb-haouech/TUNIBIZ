/* TUNIBIZ basic consent mode: no Google loader before explicit agreement. */
(()=>{
 const original=window.fetch.bind(window);
 let consent=false,mid='',container='',loaded=false,pageSent=false,configReady=false;
 try{consent=localStorage.getItem('tn_analytics')==='yes'}catch{}
 const pages={'/':'home_view','/solutions':'solutions_view','/download':'download_view','/stores':'stores_open','/storefront':'storefront_open','/wallet':'wallet_open','/crm':'business_open','/business':'business_open','/nearby':'nearby_open','/nearby/business':'business_open','/loyalty':'loyalty_open','/merchant-register':'merchant_registration_view','/privacy':'privacy_view'};
 const uiEvents=new Set([...Object.values(pages),'nearby_discovery','nearby_offer_view','nearby_map_enabled','nearby_alert_enabled','app_update_open']);
 const protectedPage=!Object.hasOwn(pages,location.pathname);
 const safeUrl=()=>location.origin+location.pathname; // No query, fragment, referrer or user fields.
 const denied={analytics_storage:'denied',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',personalization_storage:'denied'};
 window.dataLayer=window.dataLayer||[];
 window.gtag=function(){window.dataLayer.push(arguments)};
 gtag('consent','default',denied);
 gtag('set','ads_data_redaction',true);
 gtag('set','url_passthrough',false);
 gtag('set',{page_location:safeUrl(),page_referrer:'',allow_google_signals:false,allow_ad_personalization_signals:false,send_page_view:false});
 function google(event){
  if(!consent||!loaded||protectedPage||!/^[a-z_]{1,37}$/.test(event))return;
  const name=event==='page_view'?'page_view':'tn_'+event;
  gtag('event',name,{send_to:mid,page_location:safeUrl(),page_referrer:'',page_path:location.pathname,tn_platform:'web'});
  // This object is for GTM inspection. GA4 is sent once by gtag above.
  window.dataLayer.push({event:'tunibiz_event',tn_event_name:name,tn_page_path:location.pathname,tn_platform:'web'});
 }
 function loadGoogle(){
  if(!consent||!mid||loaded||protectedPage)return;
  loaded=true;window['ga-disable-'+mid]=false;
  gtag('consent','update',{...denied,analytics_storage:'granted'});
  gtag('js',new Date());
  gtag('config',mid,{send_page_view:false,page_location:safeUrl(),page_referrer:'',allow_google_signals:false,allow_ad_personalization_signals:false});
  const script=document.createElement('script');script.async=true;script.id='tn-google-loader';script.referrerPolicy='no-referrer';
  if(container){window.dataLayer.push({'gtm.start':Date.now(),event:'gtm.js'});script.src='https://www.googletagmanager.com/gtm.js?id='+encodeURIComponent(container)}
  else script.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(mid);
  script.onerror=()=>{loaded=false;script.remove()};document.head.append(script);
  if(!pageSent){pageSent=true;google('page_view')}
 }
 window.fetch=async function(input,init){
  let url;try{url=new URL(typeof input==='string'?input:input.url||input,location.origin)}catch{return original(input,init)}
  if(!consent||url.origin!==location.origin||!url.pathname.startsWith('/api/')||url.pathname.startsWith('/api/admin/'))return original(input,init);
  const headers=new Headers(init?.headers||(input instanceof Request?input.headers:undefined));
  headers.set('X-Tunibiz-Analytics','yes');headers.set('X-Tunibiz-Platform','web');
  const response=await original(input,{...init,headers});
  if(response.ok&&consent){const event=response.headers.get('X-Tunibiz-Event');if(event)google(event)}
  return response;
 };
 async function ui(event){
  if(!consent||!uiEvents.has(event))return;
  try{
   const response=await original('/api/session');const csrf=(await response.json()).csrf;if(!consent)return;
   const sent=await original('/api/analytics/event',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Tunibiz-Analytics':'yes','X-Tunibiz-Platform':'web'},body:JSON.stringify({event})});
   if(sent.ok)google(event);
  }catch{}
 }
 window.tunibizAnalytics=ui;
 function clearCookies(){
  for(const cookie of document.cookie.split(';')){
   const key=cookie.split('=')[0].trim();if(!/^_ga(?:_|$)/.test(key))continue;
   for(const domain of ['', '; Domain='+location.hostname,'; Domain=.'+location.hostname])
    document.cookie=key+'=; Max-Age=0; Path=/; SameSite=Lax'+domain;
  }
 }
 function apply(choice,persist=true){
  const previous=consent;consent=choice==='yes';
  if(persist){try{localStorage.setItem('tn_analytics',choice)}catch{}}
  if(consent){loadGoogle();if(!previous&&configReady){const event=pages[location.pathname];if(event)ui(event)}}
  else{
   if(mid)window['ga-disable-'+mid]=true;
   gtag('consent','update',denied);clearCookies();
   // Unload installed automatic listeners, preserving the app session cookie.
   if(loaded)location.reload();
  }
 }
 window.addEventListener('storage',event=>{if(event.key==='tn_analytics')apply(event.newValue==='yes'?'yes':'no',false)});
 function prefs(){
  const dialog=document.createElement('dialog');dialog.style.cssText='max-width:440px;width:calc(100% - 32px);padding:24px;border:1px solid #dce5ee;border-radius:18px;background:#fff;color:#091628';
  dialog.innerHTML='<h2>Statistiques facultatives</h2><p>Autoriser TUNIBIZ et Google Analytics à mesurer les fonctions utilisées ? Les événements TUNIBIZ ne contiennent ni email, mot de passe, QR, identifiant de compte ni coordonnées GPS. Les fonctions de publicité restent désactivées. Le service fonctionne sans statistiques.</p><button type="button" data-choice="yes">Accepter</button> <button type="button" data-choice="no">Refuser / désactiver</button> <button type="button" data-choice="close">Fermer</button>';
  document.body.append(dialog);dialog.querySelectorAll('button').forEach(button=>button.onclick=()=>{const choice=button.dataset.choice;dialog.close();dialog.remove();if(choice!=='close')apply(choice)});
  dialog.showModal();
 }
 document.addEventListener('DOMContentLoaded',async()=>{
  const button=document.createElement('button');button.type='button';button.textContent='Préférences de statistiques';button.style.cssText='display:block;margin:18px auto;background:#fff;color:#091628;border:1px solid #dce5ee;border-radius:12px;padding:9px 15px;font-size:13px';button.onclick=prefs;document.body.append(button);
  let known=false;try{known=localStorage.getItem('tn_analytics')!==null}catch{}
  if(!known&&!protectedPage){
   const notice=document.createElement('aside');notice.id='tn-consent-choice';notice.setAttribute('aria-label','Statistiques facultatives');notice.style.cssText='max-width:1100px;margin:12px auto;padding:16px;border:1px solid #dce5ee;border-radius:16px;background:#fff;color:#091628';
   notice.innerHTML='<strong>Votre choix pour les statistiques</strong><p>Autoriser les statistiques facultatives TUNIBIZ et Google Analytics ? Vous pouvez utiliser tous les services sans les accepter.</p><button type="button" data-consent="yes">Accepter</button> <button type="button" data-consent="no">Refuser</button> <button type="button" data-consent="later">Plus tard</button>';
   notice.querySelectorAll('button').forEach(b=>b.onclick=()=>{const choice=b.dataset.consent;notice.remove();if(choice!=='later')apply(choice)});
   document.body.prepend(notice);
  }
  try{
   const response=await original('/api/analytics/config');const config=await response.json();
   mid=/^G-[A-Z0-9]+$/.test(config.measurement_id)?config.measurement_id:'';
   container=/^GTM-[A-Z0-9]+$/.test(config.gtm_container_id)?config.gtm_container_id:'';
   configReady=true;
   if(mid)window['ga-disable-'+mid]=!consent;
   if(consent){loadGoogle();const event=pages[location.pathname];if(event)ui(event)}
  }catch{}
 });
})();