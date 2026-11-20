'use strict';
(()=>{
const $=s=>document.querySelector(s),slug=location.pathname.split('/').pop(),status=$('#status'),button=$('#confirm-scan'),dialog=$('#scan-confirmation');
const hosts=new Set(['facebook.com','www.facebook.com','m.facebook.com','web.facebook.com','fb.com','www.fb.com','fb.me','www.fb.me']);
let csrf='',busy=false,timer=null;
function safeFacebook(value){try{const u=new URL(value);return u.protocol==='https:'&&hosts.has(u.hostname)&&!u.username&&!u.password&&!u.port&&u.pathname!=='/'?u.href:null}catch{return null}}
async function api(path,body){const r=await fetch('/api'+path,{credentials:'same-origin',cache:'no-store',...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)})});const d=await r.json();if(!r.ok)throw Object.assign(new Error(d.error||'Connexion indisponible. Réessayez.'),{status:r.status});return d}
function stopRedirect(){if(timer!==null){clearTimeout(timer);timer=null}$('#redirect-status').textContent='Vous pouvez ouvrir Facebook quand vous le souhaitez.'}
function confirmation(r){
 $('#scan-result').textContent=r.status==='welcome'?(r.points>0?'+'+r.points+' points de bienvenue crédités.':'Votre carte est disponible. Le bonus de bienvenue a déjà été attribué.'):'Votre demande est enregistrée. Les points d’achat restent en attente de validation par le commerçant.';
 const target=safeFacebook(r.facebook_url),link=$('#facebook-link');link.hidden=!target;
 if(target){link.href=target;$('#redirect-status').textContent='Ouverture de la page Facebook dans 3 secondes…'}
 else $('#redirect-status').textContent='Retrouvez votre fidélité dans votre portefeuille.';
 dialog.showModal();
 if(target)timer=setTimeout(()=>{timer=null;location.assign(target)},3000);
}
$('#stay').onclick=()=>{stopRedirect();dialog.close()};
dialog.addEventListener('close',stopRedirect);dialog.addEventListener('cancel',stopRedirect);
$('#facebook-link').onclick=stopRedirect;
window.addEventListener('pagehide',stopRedirect);
button.onclick=async()=>{
 if(busy)return;busy=true;button.disabled=true;status.className='';status.textContent='Enregistrement du scan…';
 try{const r=await api('/wallet/store-scan',{slug});status.textContent='Scan enregistré.';button.hidden=true;confirmation(r)}
 catch(e){status.className='error';status.textContent=e.message;if(e.status===401){button.hidden=true;$('#join').hidden=false}}
 finally{busy=false;button.disabled=false}
};
(async()=>{try{
 const info=await api('/store/'+encodeURIComponent(slug));$('#shop-name').textContent=info.shop.name;$('#shop-city').textContent=info.shop.city;
 $('#facebook-info').hidden=!safeFacebook(info.shop.facebook_url);$('#join').href='/wallet?store='+encodeURIComponent(slug);
 csrf=(await api('/session')).csrf;
 try{await api('/wallet');button.hidden=false;status.textContent='Confirmez votre scan pour l’enregistrer.'}
 catch(e){if(e.status!==401)throw e;$('#join').hidden=false;status.textContent='Connectez-vous à votre compte pour retrouver vos points.'}
}catch(e){status.className='error';status.textContent=e.message}})();
})();
