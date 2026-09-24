const $=selector=>document.querySelector(selector);
const make=(tag,text,className)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;};
const size=p=>['lens','bridge','temple'].map(k=>p.dimensions_mm[k]).join('–');
const views=['Μπροστά','Τρία τέταρτα','Πλάι'];
async function api(path,method='GET',body){
  const response=await fetch(path,{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
  const value=await response.json();if(!response.ok)throw new Error(value.error||'Η αποθήκευση απέτυχε');return value;
}
function card(product){
  let p=product;
  const article=make('article',undefined,'card');article.append(make('h2',`${p.brand} ${p.model}`));
  article.append(make('p',`${p.color_code?`Χρώμα ${p.color_code} · `:''}${size(p)} mm · ${p.price_eur} € · ${p.inventory.store} · 1 τεμάχιο`,'meta'));
  const photos=make('div',undefined,'photo-strip');p.images.forEach((path,i)=>{
    const figure=make('figure'),image=make('img');image.src='/'+path;image.alt=`${p.brand} ${p.model} — ${views[i]}`;image.loading='lazy';
    figure.append(image,make('figcaption',views[i]));photos.append(figure);
  });article.append(photos);
  const descriptionLabel=make('label','Περιγραφή ORAMA');const description=make('textarea');description.value=p.short_description||'';
  descriptionLabel.append(description);article.append(descriptionLabel);
  const descriptionCheck=make('label',undefined,'check'),dc=make('input');dc.type='checkbox';dc.checked=p.description_review==='approved_by_owner';
  descriptionCheck.append(dc,document.createTextNode(' Εγκρίνω αυτή την περιγραφή'));article.append(descriptionCheck);
  const materialLabel=make('label','Υλικό σκελετού');const material=make('input');material.type='text';material.setAttribute('list','frameMaterials');material.value=p.material||'';
  materialLabel.append(material);article.append(materialLabel);
  const materialCheck=make('label',undefined,'check'),mc=make('input');mc.type='checkbox';mc.checked=p.material_review==='approved_by_owner';
  materialCheck.append(mc,document.createTextNode(' Επιβεβαιώνω αυτό το υλικό'));article.append(materialCheck);
  const actions=make('div',undefined,'actions'),save=make('button','Αποθήκευση ελέγχου'),status=make('span','Οι προτάσεις περιμένουν τον έλεγχό σου.','saved');
  description.addEventListener('input',()=>{dc.checked=false;status.textContent='Η αλλαγμένη περιγραφή χρειάζεται νέα έγκριση και αποθήκευση.';});
  material.addEventListener('input',()=>{mc.checked=false;status.textContent='Το αλλαγμένο υλικό χρειάζεται νέα επιβεβαίωση και αποθήκευση.';});
  for(const checkbox of [dc,mc])checkbox.addEventListener('change',()=>{status.textContent='Αποθήκευσε την επιλογή σου.';});
  save.type='button';save.onclick=async()=>{
    save.disabled=true;status.textContent='Αποθήκευση…';status.className='saved';
    try{
      const updated=await api(`/api/products/${encodeURIComponent(p.id)}`,'PUT',{
        ...p,short_description:description.value.trim(),material:material.value.trim()||null,
        description_confirmed:dc.checked,material_confirmed:mc.checked
      });p=updated;status.textContent='Αποθηκεύτηκε τοπικά. Τα εγκεκριμένα πεδία εμφανίζονται στην τοπική όψη επισκέπτη μετά από ανανέωση.';
    }catch(error){status.className='error';status.textContent=error.message;}finally{save.disabled=false;}
  };
  actions.append(save,status);article.append(actions);return article;
}
api('/api/products').then(data=>{
  const list=$('#reviewList');list.replaceChildren();data.products.forEach(p=>list.append(card(p)));
  $('#loadStatus').textContent=`${data.products.length} προϊόντα προς έλεγχο`;
}).catch(error=>{$('#loadStatus').className='error';$('#loadStatus').textContent=error.message;});
