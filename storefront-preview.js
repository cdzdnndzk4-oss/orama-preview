const $=selector=>document.querySelector(selector);
let products=[];
const money=value=>new Intl.NumberFormat('el-GR',{style:'currency',currency:'EUR'}).format(value);
const size=p=>['lens','bridge','temple'].map(k=>p.dimensions_mm[k]).join('–');
const make=(tag,text,className)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;};
const photo=url=>url.startsWith('data:')?url:url;
function render(){
  const q=$('#search').value.trim().toLocaleLowerCase('el-GR'),category=$('#category').value;
  const visible=products.filter(p=>(!category||p.category===category)&&[p.brand,p.model,p.color_code,p.id].join(' ').toLocaleLowerCase('el-GR').includes(q));
  $('#count').textContent=`${visible.length} προϊόντα`;
  const grid=$('#grid');grid.replaceChildren();
  if(!visible.length){grid.append(make('p','Δεν βρέθηκαν προϊόντα.','empty'));return;}
  for(const p of visible){
    const card=make('article',undefined,'card'),img=make('img');img.src=photo(p.images[0]);img.alt=`${p.brand} ${p.model} — μπροστά`;img.loading='lazy';
    const body=make('div',undefined,'card-body');body.append(make('h2',`${p.brand} ${p.model}`));
    body.append(make('span',`${p.category} · ${size(p)} mm`,'muted'));
    body.append(make('span',money(p.price_eur),'price'));
    body.append(make('span',`1 τεμάχιο · ${p.inventory.store}`,'muted'));
    const button=make('button','Δες τις 3 όψεις');button.type='button';button.onclick=()=>openProduct(p);
    body.append(button);card.append(img,body);grid.append(card);
  }
}
function openProduct(p){
  $('#dialogTitle').textContent=`${p.brand} ${p.model}`;
  const hero=$('#hero');hero.src=photo(p.images[0]);hero.alt=`${p.brand} ${p.model} — μπροστά`;
  const thumbs=$('#thumbs');thumbs.replaceChildren();
  ['Μπροστά','Τρία τέταρτα','Πλάι'].forEach((label,i)=>{
    const button=make('button');button.type='button';button.setAttribute('aria-label',label);
    const img=make('img');img.src=photo(p.images[i]);img.alt='';button.append(img);
    button.onclick=()=>{hero.src=img.src;hero.alt=`${p.brand} ${p.model} — ${label}`;};thumbs.append(button);
  });
  const details=$('#details');details.replaceChildren();
  details.append(make('p',`${size(p)} mm · ${money(p.price_eur)} · 1 τεμάχιο στην ${p.inventory.store}`));
  if(p.color_code)details.append(make('p',`Κωδικός χρώματος: ${p.color_code}`));
  if(p.short_description)details.append(make('p',p.short_description));
  if(p.material)details.append(make('p',`Υλικό: ${p.material}`));
  $('#productDialog').showModal();
}
$('#close').onclick=()=>$('#productDialog').close();
$('#search').addEventListener('input',render);$('#category').addEventListener('change',render);
async function load(){
  // Local admin is the latest working catalog. Static JSON is the checked
  // fallback for a standalone read-only preview. Neither enables checkout.
  let response;
  try{response=await fetch('/api/catalog-preview');if(!response.ok)throw new Error();}
  catch{response=await fetch('catalog/storefront-preview.json');}
  if(!response.ok)throw new Error('Ο κατάλογος δεν φορτώθηκε');
  const data=await response.json();products=data.products.map(p=>({
    ...p,
    short_description:!('description_review' in p)||p.description_review==='approved_by_owner'?p.short_description:null,
    material:!('material_review' in p)||p.material_review==='approved_by_owner'?p.material:null
  }));render();
}
load().catch(error=>{$('#count').textContent=error.message;});
