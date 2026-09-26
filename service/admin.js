const $=s=>document.querySelector(s);
let csrf=sessionStorage.getItem('oramaCsrf')||'',page=1,total=0,current=null,photos={};
function note(s){$('#message').textContent=s;}
async function api(path,method='GET',body){
  const options={method,credentials:'same-origin',headers:{}};
  if(method!=='GET')options.headers['X-CSRF-Token']=csrf;
  if(body instanceof FormData)options.body=body;
  else if(body!==undefined){options.headers['Content-Type']='application/json';options.body=JSON.stringify(body);}
  const r=await fetch(path,options),value=await r.json();
  if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:'Το αίτημα απέτυχε ('+r.status+')');
  return value;
}
function show(){ $('#loginBox').classList.add('hidden');$('#workspace').classList.remove('hidden');list(); }
$('#login').onsubmit=async e=>{e.preventDefault();try{const f=e.target.elements;const v=await api('/admin/api/login','POST',{email:f.email.value,password:f.password.value});csrf=v.csrf;sessionStorage.setItem('oramaCsrf',csrf);f.password.value='';show();note('Συνδέθηκες.');}catch(err){note(err.message)}};
$('#logout').onclick=async()=>{try{await api('/admin/api/logout','POST');}finally{csrf='';sessionStorage.removeItem('oramaCsrf');location.reload()}};
async function list(){try{const data=await api('/admin/api/products?'+new URLSearchParams({q:$('#find').value,page}));total=data.total;$('#total').textContent=total+' προϊόντα';$('#page').textContent='Σελίδα '+page;$('#prev').disabled=page===1;$('#next').disabled=page*24>=total;$('#items').replaceChildren();for(const p of data.products){const b=document.createElement('button');b.type='button';b.textContent=p.brand+' '+p.model+' · '+(p.published?'Δημοσιευμένο':'Πρόχειρο');b.onclick=()=>edit(p);$('#items').append(b)}}catch(err){if(err.message.includes('401')){$('#loginBox').classList.remove('hidden');$('#workspace').classList.add('hidden')}else note(err.message)}}
$('#find').oninput=()=>{page=1;list()};$('#prev').onclick=()=>{page--;list()};$('#next').onclick=()=>{page++;list()};
$('#new').onclick=()=>{current=null;photos={};$('#product').reset();$('#product').elements.id.disabled=false;$('#title').textContent='Νέο προϊόν';renderPhotos();$('#product').closest('.panel').scrollIntoView({behavior:'smooth',block:'start'});};
function edit(p){current=p;photos=Object.fromEntries((p.photos||[]).map(x=>[x.view,x]));const f=$('#product').elements;
  for(const k of ['id','brand','model','color_code','frame_color','material','category','price_eur','audience','description'])f[k].value=p[k]??'';
  for(const k of ['lens','bridge','temple'])f[k].value=p.dimensions_mm[k];
  f.agia.value=p.availability['Αγία Παρασκευή']||0;f.kypseli.value=p.availability['Κυψέλη']||0;
  f.material_verified.checked=p.material_review==='approved_by_owner';f.audience_verified.checked=p.audience_review==='approved_by_owner';f.description_verified.checked=p.description_review==='approved_by_owner';
  f.selection.checked=p.selection;f.published.checked=p.published;f.id.disabled=true;$('#title').textContent=p.brand+' '+p.model;renderPhotos();$('#product').closest('.panel').scrollIntoView({behavior:'smooth',block:'start'});
}
function payload(){const f=$('#product').elements;return {id:current?.id||f.id.value.trim(),brand:f.brand.value.trim(),model:f.model.value.trim(),color_code:f.color_code.value.trim()||null,frame_color:f.frame_color.value.trim()||null,material:f.material.value.trim()||null,material_verified:f.material_verified.checked,audience:f.audience.value.trim()||null,audience_verified:f.audience_verified.checked,category:f.category.value,selection:f.selection.checked,price_eur:Number(f.price_eur.value),lens:Number(f.lens.value),bridge:Number(f.bridge.value),temple:Number(f.temple.value),availability:{'Αγία Παρασκευή':Number(f.agia.value),'Κυψέλη':Number(f.kypseli.value)},description:f.description.value.trim(),description_verified:f.description_verified.checked,published:f.published.checked};}
$('#product').onsubmit=async e=>{e.preventDefault();try{const p=payload();const saved=await api('/admin/api/products/'+encodeURIComponent(p.id),'PUT',p);edit(saved);await list();note('Το προϊόν αποθηκεύτηκε.')}catch(err){note(err.message)}};
function renderPhotos(){const box=$('#photos');box.replaceChildren();for(const [view,label] of [['front','Μπροστά'],['three-quarter','Τρία τέταρτα'],['side','Πλάι']]){
 const panel=document.createElement('article'),heading=document.createElement('h3');heading.textContent=label;panel.append(heading);
 const old=current?.images?.[['front','three-quarter','side'].indexOf(view)];if(old){const img=document.createElement('img');img.src=old;img.alt='Τρέχουσα εικόνα '+label;panel.append(img)}
 const input=document.createElement('input');input.type='file';input.accept='image/jpeg,image/png';input.setAttribute('aria-label','Ανέβασμα '+label);input.disabled=!current;
 input.onchange=async()=>{if(!input.files[0])return;try{const form=new FormData();form.append('file',input.files[0]);const result=await api('/admin/api/products/'+encodeURIComponent(current.id)+'/photos/'+view,'POST',form);photos[view]={id:result.photo_id,original:result.original,processed:result.processed};current.published=false;$('#product').elements.published.checked=false;renderPhotos();note('Πρόταση έτοιμη. Επίλεξε πρωτότυπο ή επεξεργασμένο για '+label+'.')}catch(err){note(err.message)}};panel.append(input);
 const draft=photos[view];if(draft){const compare=document.createElement('div');compare.className='compare';for(const [choice,src] of [['original',draft.original],['processed',draft.processed]]){if(!src)continue;const option=document.createElement('label'),image=document.createElement('img'),radio=document.createElement('input');radio.type='radio';radio.name='choice-'+view;radio.checked=draft.chosen===choice;radio.onchange=async()=>{try{await api('/admin/api/photos/'+draft.id+'/choice','PUT',{chosen:choice});draft.chosen=choice;note('Επιλέχθηκε η όψη '+label+'. Αποθήκευσε ξανά για δημοσίευση.')}catch(err){note(err.message)}};image.src=src;image.alt=choice==='original'?'Πρωτότυπο':'Πρόταση επεξεργασίας';option.append(radio,image,document.createTextNode(choice==='original'?'Πρωτότυπο':'Επεξεργασμένο'));compare.append(option)}panel.append(compare);const review=document.createElement('button');review.type='button';review.textContent='Σύγκριση σε πλήρη ανάλυση / zoom';review.onclick=()=>openReview(draft,label);panel.append(review)}box.append(panel)}}
function openReview(draft,label){$('#reviewTitle').textContent='Έλεγχος: '+label+' · '+(current?.brand||'')+' '+(current?.model||'');$('#reviewOriginal').src=draft.original;$('#reviewProcessed').src=draft.processed;$('#reviewPair').classList.remove('zoom');$('#reviewZoom').textContent='Μεγέθυνση 100%';$('#photoReview').showModal();}
$('#reviewZoom').onclick=()=>{const zoom=$('#reviewPair').classList.toggle('zoom');$('#reviewZoom').textContent=zoom?'Προσαρμογή στο παράθυρο':'Μεγέθυνση 100%'};
$('#reviewClose').onclick=()=>{$('#photoReview').close();$('#reviewOriginal').removeAttribute('src');$('#reviewProcessed').removeAttribute('src')};
$('#import').onclick=async()=>{const file=$('#bulk').files[0];if(!file)return;try{const data=JSON.parse(await file.text());if(!Array.isArray(data))throw Error('Χρειάζεται πίνακας JSON');const result=await api('/admin/api/import','POST',data);page=1;await list();note('Εισήχθησαν '+result.imported+' πρόχειρα προϊόντα.')}catch(err){note(err.message)}};
if(csrf)show();else renderPhotos();
