#!/usr/bin/env python3
"""Self-contained iPhone review copy of the local admin, with temporary sample changes."""
import base64
import json
from pathlib import Path
from io import BytesIO
from PIL import Image
from importlib.util import module_from_spec, spec_from_file_location
root=Path(__file__).resolve().parents[1]
spec=spec_from_file_location('orama_description_library',root/'admin/description_library.py')
library=module_from_spec(spec);spec.loader.exec_module(library)
out=root.parent/'output/admin-preview.html';out.parent.mkdir(exist_ok=True)
products=json.loads((root/'catalog/products.json').read_text(encoding='utf-8'))['products']
for product in products:
    embedded=[]
    for name in product['images']:
        im=Image.open(root/name).convert('RGB')
        im.thumbnail((1000,750))
        buf=BytesIO();im.save(buf,format='JPEG',quality=87,optimize=True)
        embedded.append('data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode())
    product['images']=embedded
html=(root/'admin/index.html').read_text(encoding='utf-8')
html=html.replace('Το εργαλείο λειτουργεί μόνο στον τοπικό υπολογιστή. Δεν είναι ακόμη συνδεδεμένο με το δημόσιο κατάστημα, πληρωμές ή αυτόματο καθαρισμό φωτογραφιών.',
'''ΠΡΟΕΠΙΣΚΟΠΗΣΗ ΓΙΑ ΚΙΝΗΤΟ: Μπορείς να δεις τη φόρμα και να κάνεις δοκιμές. Οι αλλαγές σε αυτό το αρχείο δεν αποθηκεύονται και δεν επηρεάζουν το κατάστημα.''')
html=html.replace('<div id="list"></div>','<div id="list">'+''.join(f'<div class="product-row">{p["brand"]} {p["model"]} · {p["price_eur"]} €<small>{p["dimensions_mm"]["lens"]}-{p["dimensions_mm"]["bridge"]}-{p["dimensions_mm"]["temple"]} · Αγία Παρασκευή · 1 τεμάχιο</small></div>' for p in products)+'</div>')
script=(root/'admin/admin.js').read_text(encoding='utf-8').replace('slots();refresh().catch(error=>msg(error.message,true));','slots();refresh().then(()=>edit(products[0])).catch(error=>msg(error.message,true));')
mock='''const previewProducts=__PRODUCTS__;
const openings=__OPENINGS__,endings=__ENDINGS__,audiences=__AUDIENCES__;
function localDraft(p,existing=[]){
 const note=(p.visual_note||'').trim().replace(/[. ]+$/,'');
 if(!openings[p.style]||!audiences[p.audience])throw Error('Επίλεξε χαρακτήρα και κοινό για την περιγραφή');
 if(note.split(/\\s+/).length<8||note.split(/\\s+/).length>20)throw Error('Γράψε μία επιβεβαιωμένη οπτική πρόταση 8–20 λέξεων');
 let hash=0;for(const c of p.id)hash=(hash*31+c.charCodeAt(0))>>>0;
 let best=null;
 for(let offset=0;offset<50;offset++){
  const pos=(hash+(p.variant||0)+offset)%50;
  const first=openings[p.style][pos%5].replaceAll('{who}',audiences[p.audience]);
  const last=endings[Math.floor(pos/5)].replaceAll('{who}',audiences[p.audience]);
  const text=`${first} ${note}. ${last}`;
  if(text.split(/\\s+/).length>=35&&text.split(/\\s+/).length<=60&&!existing.includes(text)){
   const repeats=['προσωπικ','χαρακτήρ','κομψ','διακριτ','σύγχρον','θέλουν'].reduce((sum,stem)=>sum+Math.max(0,[first,note,last].filter(part=>part.toLowerCase().includes(stem)).length-1),0);
   const score=6*existing.filter(value=>value.includes(first)).length+5*existing.filter(value=>value.includes(last)).length+2*repeats;
   if(!best||score<best.score)best={score,text};
  }
 }
 if(best)return best.text;
 throw Error('Δεν βρέθηκε κατάλληλη διαφορετική περιγραφή');
}
window.fetch=async (path,options={})=>{
 const method=options.method||'GET',body=options.body?JSON.parse(options.body):null;
 let status=200,result={};
 if(path==='/api/products'&&method==='GET')result={products:previewProducts};
 else if(path==='/api/upload'&&method==='POST'){status=201;result={url:'data:image/jpeg;base64,'+body.data};}
 else if(path==='/api/draft-description'&&method==='POST'){try{result={description:localDraft(body,[...previewProducts.map(p=>p.short_description),...(body.exclude||[])]),review:'suggested_pending_owner_review'};}catch(error){status=400;result={error:error.message};}}
 else if(path==='/api/products'&&method==='POST'){if(previewProducts.some(p=>p.id===body.id)){status=409;result={error:'Υπάρχει ήδη προϊόν με αυτόν τον κωδικό'};}else{const p={...body,description_review:body.description_confirmed?'approved_by_owner':'suggested_pending_owner_review',material_review:body.material&&body.material_confirmed?'approved_by_owner':'pending_owner_review'};previewProducts.push(p);status=201;result=p;}}
 else if(path.startsWith('/api/products/')&&method==='PUT'){const i=previewProducts.findIndex(p=>p.id===body.id);if(i<0){status=404;result={error:'Δεν βρέθηκε'};}else{const p={...body,description_review:body.description_confirmed?'approved_by_owner':'suggested_pending_owner_review',material_review:body.material&&body.material_confirmed?'approved_by_owner':'pending_owner_review'};previewProducts[i]=p;result=p;}}
 else if(path==='/api/import'&&method==='POST'){
  const ids=new Set(previewProducts.map(p=>p.id));
  if(body.products.some(p=>ids.has(p.id))){status=400;result={error:'Υπάρχει ήδη ένας κωδικός'};}
  else try{const rows=[];for(const p of body.products){const desc=p.short_description||(p.style&&p.audience&&p.visual_note?localDraft(p,[...previewProducts,...rows].map(x=>x.short_description)):'');rows.push({...p,short_description:desc,description_review:desc?'suggested_pending_owner_review':'needs_description',material_review:'pending_owner_review'});}previewProducts.push(...rows);status=201;result={imported:rows.length};}catch(error){status=400;result={error:error.message};}
 }
 return {ok:status<400,status,json:async()=>result};
};'''.replace('__PRODUCTS__',json.dumps(products,ensure_ascii=False)).replace('__OPENINGS__',json.dumps(library.OPENINGS,ensure_ascii=False)).replace('__ENDINGS__',json.dumps(library.ENDINGS,ensure_ascii=False)).replace('__AUDIENCES__',json.dumps(library.AUDIENCES,ensure_ascii=False))
html=html.replace('<script src="/admin.js" defer></script>','<script>'+mock+'\n'+script+'</script>')
out.write_text(html,encoding='utf-8')
print(out,out.stat().st_size)
