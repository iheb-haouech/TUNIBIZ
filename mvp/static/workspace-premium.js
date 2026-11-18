(()=>{const path=location.pathname;
const consumer=path==='/wallet'||path==='/loyalty'||path==='/nearby';
const links=path==='/admin'?[['/','Accueil'],['/crm','Business'],['/merchant-register','Inscription'],['/admin','Administration']]:consumer?[['/','Accueil'],['/wallet','Portefeuille'],['/nearby','Nearby'],['/loyalty','Carte individuelle'],['/download','Android'],['/crm','Business']]:[['/','Accueil'],['/crm','Business'],['/nearby/business','Nearby pro'],['/merchant-register','Inscription'],['/wallet','Portefeuille']];
const head=document.querySelector('body>header');if(head){let nav=head.querySelector('nav');if(!nav){nav=document.createElement('nav');head.append(nav)}nav.setAttribute('aria-label','Navigation principale');nav.replaceChildren(...links.map(([href,label])=>{const a=document.createElement('a');a.href=href;a.textContent=label;if(href===path)a.setAttribute('aria-current','page');return a}));}
let footer=document.querySelector('body>footer');if(!footer){footer=document.createElement('footer');document.body.append(footer)}footer.className='tn-footer';footer.innerHTML='<strong>TUNIBIZ · Tunisie</strong><nav aria-label="Assistance et informations"><a href="/forgot-password">Récupérer mon compte</a><a href="/privacy">Confidentialité</a><a href="/account-deletion">Suppression de compte</a><a href="/download">Android</a></nav>';
let seq=0;function enhance(){
 document.querySelectorAll('form').forEach(form=>{
  if(form.dataset.tnReady)return;form.dataset.tnReady='1';
  for(const el of form.querySelectorAll('input,select,textarea')){if(el.closest('label')||el.hasAttribute('aria-label')||el.hasAttribute('aria-labelledby'))continue;const label=el.previousElementSibling;if(label?.tagName==='LABEL'&&!label.htmlFor){if(!el.id)el.id='tn-field-'+(++seq);label.htmlFor=el.id}}
  const password=form.querySelector('input[type=password]');if(password&&password.name==='password'&&form.querySelectorAll('input[type=password]').length===1){const box=document.createElement('div');box.className='tn-pw';const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent='Afficher le mot de passe';button.setAttribute('aria-pressed','false');button.onclick=()=>{const show=password.type==='password';password.type=show?'text':'password';button.textContent=show?'Masquer le mot de passe':'Afficher le mot de passe';button.setAttribute('aria-pressed',String(show))};box.append(button);form.after(box);}
  if(form.id==='login'){const panel=form.closest('.panel');if(panel)panel.classList.add('tn-auth');}
 });
 document.querySelectorAll('#admin-app table').forEach(t=>{if(t.parentElement.classList.contains('tn-table-wrap'))return;const div=document.createElement('div');div.className='tn-table-wrap';t.before(div);div.append(t)});
}
enhance();let scheduled=false;new MutationObserver(()=>{if(scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;enhance()})}).observe(document.body,{childList:true,subtree:true});
})();
