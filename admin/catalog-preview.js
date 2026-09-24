const $ = selector => document.querySelector(selector);
let products = [];
const dimensions = p => ['lens','bridge','temple'].map(key => p.dimensions_mm?.[key] ?? '—').join('–');
const price = value => new Intl.NumberFormat('el-GR',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(value);
const imageUrl = value => '/' + value;
function node(tag, className, value){const element=document.createElement(tag);if(className)element.className=className;if(value!=null)element.textContent=value;return element;}
function render(){
  const query=$('#search').value.trim().toLocaleLowerCase('el-GR'),category=$('#category').value;
  const matches=products.filter(p=>(!category||p.category===category)&&[p.brand,p.model,p.color_code,p.id].join(' ').toLocaleLowerCase('el-GR').includes(query));
  $('#count').textContent=`${matches.length} προϊόντα`;
  const grid=$('#grid');grid.replaceChildren();
  if(!matches.length){grid.append(node('p','empty','Δεν βρέθηκαν προϊόντα.'));return;}
  matches.forEach(p=>{
    const card=node('article','card'),image=node('div','image'),img=node('img');img.src=imageUrl(p.images[0]);img.alt=`${p.brand} ${p.model} — μπροστά`;img.loading='lazy';image.append(img);
    const details=node('div','details');details.append(node('h2','',`${p.brand} ${p.model}`));
    details.append(node('div','muted',`${p.color_code?`Χρώμα ${p.color_code} · `:''}${dimensions(p)} mm`));
    details.append(node('div','price',price(p.price_eur)));
    details.append(node('div','muted',`1 τεμάχιο · ${p.inventory.store}`));
    const button=node('button','', 'Δες τις 3 φωτογραφίες');button.type='button';button.addEventListener('click',()=>openProduct(p));details.append(button);
    card.append(image,details);grid.append(card);
  });
}
function openProduct(p){
  const content=$('#detailContent');content.replaceChildren();content.append(node('h2','',`${p.brand} ${p.model}`));
  const hero=node('div','hero'),image=node('img');image.src=imageUrl(p.images[0]);image.alt=`${p.brand} ${p.model} — μπροστά`;hero.append(image);content.append(hero);
  const thumbs=node('div','thumbs');['Μπροστά','Τρία τέταρτα','Πλάι'].forEach((label,i)=>{
    const button=node('button',''),thumb=node('img');button.type='button';button.setAttribute('aria-label',label);thumb.src=imageUrl(p.images[i]);thumb.alt=label;
    button.append(thumb);button.addEventListener('click',()=>{image.src=thumb.src;image.alt=`${p.brand} ${p.model} — ${label}`;});thumbs.append(button);
  });content.append(thumbs);
  content.append(node('p','specs',`${p.category} · ${dimensions(p)} mm · ${price(p.price_eur)} · 1 τεμάχιο στην ${p.inventory.store}`));
  if(p.short_description){content.append(node('p','description',p.short_description));if(p.description_review!=='approved_by_owner')content.append(node('span','review','Περιγραφή προς έλεγχο'));}
  if(p.material){content.append(node('p','specs',`Υλικό: ${p.material}`));if(p.material_review!=='approved_by_owner')content.append(node('span','review','Υλικό προς επιβεβαίωση'));}
  $('#detail').showModal();
}
$('#close').addEventListener('click',()=>$('#detail').close());
$('#search').addEventListener('input',render);$('#category').addEventListener('change',render);
fetch('/api/catalog-preview').then(response=>{if(!response.ok)throw new Error('Ο κατάλογος δεν φορτώθηκε');return response.json();})
  .then(data=>{products=data.products;render();})
  .catch(error=>{$('#count').textContent=error.message;});
