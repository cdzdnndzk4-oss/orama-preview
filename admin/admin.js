const $ = s => document.querySelector(s);
let products = [], editing = null, photoPaths = [null, null, null], descriptionVariant = 0, seenDrafts = [];
let photoDrafts = [null,null,null], photoGeneration = [0,0,0];
const views = ['Μπροστά', 'Τρία τέταρτα', 'Πλάι'];
const msg = (text, error=false) => { $('#message').className = text ? `message ${error?'error':''}` : ''; $('#message').textContent = text; };
const api = async (path, method='GET', body) => {
  const response = await fetch(path, {method, headers:body?{'Content-Type':'application/json'}:{}, body:body?JSON.stringify(body):undefined});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Η αποθήκευση απέτυχε');
  return value;
};
function slots(){
  const box = $('#photos'); box.replaceChildren();
  views.forEach((label,i)=>{
    const section=document.createElement('div'); section.className='photo-slot';
    const title=document.createElement('strong'); title.textContent=label;
    const current=document.createElement('img');current.alt=`${label} - αποθηκευμένη φωτογραφία`;
    if(photoPaths[i])current.src='/'+photoPaths[i];
    const input=document.createElement('input'); input.type='file'; input.accept='image/jpeg,image/png'; input.id=`photo${i}`;
    input.setAttribute('aria-label',`Νέα φωτογραφία: ${label}`);
    const choices=document.createElement('div');choices.className='photo-choices';
    const status=document.createElement('small');status.setAttribute('role','status');
    function option(kind,text,src){
      const labelElement=document.createElement('label');labelElement.className='photo-option';
      const radio=document.createElement('input');radio.type='radio';radio.name=`photo-choice-${i}`;radio.value=kind;radio.checked=kind==='original';
      const image=document.createElement('img');image.src=src;image.alt=`${label} - ${text}`;
      const caption=document.createElement('span');caption.textContent=text;
      labelElement.append(radio,image,caption);choices.append(labelElement);
    }
    input.addEventListener('change',async()=>{
      const file=input.files[0];if(!file)return;
      const generation=++photoGeneration[i];
      if(photoDrafts[i]?.objectURL)URL.revokeObjectURL(photoDrafts[i].objectURL);
      const objectURL=URL.createObjectURL(file);photoDrafts[i]={file,objectURL,processed:null};
      choices.replaceChildren();option('original','Αρχική',objectURL);status.textContent='Ετοιμάζεται η επεξεργασμένη πρόταση…';
      try{
        const result=await api('/api/photo-preview','POST',{data:await fileData(file)});
        if(generation!==photoGeneration[i])return;
        photoDrafts[i].processed=result.data;
        option('processed',`Λευκό φόντο · ${result.dimensions.fill_percent}% πλάτος`,'data:image/png;base64,'+result.data);
        status.textContent='Σύγκρινε προσεκτικά τους φακούς και τις άκρες. Επίλεξε την εικόνα που θέλεις να αποθηκευτεί.';
      }catch(error){if(generation===photoGeneration[i])status.textContent=`Η πρόταση δεν έγινε: ${error.message} Η αρχική φωτογραφία παραμένει διαθέσιμη.`;}
    });
    section.append(title,current,input,choices,status); box.append(section);
  });
}
function clearPhotoDrafts(){photoDrafts.forEach(draft=>{if(draft?.objectURL)URL.revokeObjectURL(draft.objectURL);});photoDrafts=[null,null,null];photoGeneration=photoGeneration.map(n=>n+1);}
function reset(){clearPhotoDrafts();editing=null;photoPaths=[null,null,null];descriptionVariant=0;seenDrafts=[];$('#productForm').reset();$('#productForm').elements.id.disabled=false;$('#formTitle').textContent='Νέο προϊόν';$('#generate').textContent='Πρόταση από τη βιβλιοθήκη';slots();msg('');}
function edit(product){
  clearPhotoDrafts();
  editing=product.id;photoPaths=[...product.images];descriptionVariant=0;seenDrafts=[]; const f=$('#productForm').elements;
  for(const key of ['id','brand','model','category','price_eur','color_code','material','short_description','style','audience','visual_note']) f[key].value=product[key]??'';
  f.description_confirmed.checked=product.description_review==='approved_by_owner';
  f.material_confirmed.checked=product.material_review==='approved_by_owner';
  for(const key of ['lens','bridge','temple']) f[key].value=product.dimensions_mm[key];
  f.store.value=product.inventory.store;f.id.disabled=true;$('#formTitle').textContent=`Διόρθωση: ${product.brand} ${product.model}`;$('#generate').textContent='Πρόταση από τη βιβλιοθήκη';slots();msg('');window.scrollTo({top:0,behavior:'smooth'});
}
async function refresh(){
  products=(await api('/api/products')).products;$('#count').textContent=`(${products.length})`;
  const list=$('#list');list.replaceChildren();
  products.forEach(p=>{const button=document.createElement('button');button.type='button';button.className='product-row';
    button.textContent=`${p.brand} ${p.model} · ${p.price_eur} €`;
    const small=document.createElement('small');small.textContent=`${p.dimensions_mm.lens}-${p.dimensions_mm.bridge}-${p.dimensions_mm.temple} · ${p.inventory.store} · 1 τεμάχιο · ${p.description_review==='approved_by_owner'?'Περιγραφή εγκεκριμένη':p.short_description?'Περιγραφή προς έλεγχο':'Χρειάζεται περιγραφή'}`;
    button.append(small);button.onclick=()=>edit(p);list.append(button);
  });
}
function productFromForm(){
  const f=$('#productForm').elements;
  return {id:editing||f.id.value.trim(),brand:f.brand.value.trim(),model:f.model.value.trim(),color_code:f.color_code.value.trim()||null,
    category:f.category.value,price_eur:Number(f.price_eur.value),material:f.material.value.trim()||null,style:f.style.value||null,audience:f.audience.value||null,visual_note:f.visual_note.value.trim(),short_description:f.short_description.value.trim(),description_confirmed:f.description_confirmed.checked,material_confirmed:f.material_confirmed.checked,dimensions_mm:{lens:Number(f.lens.value),bridge:Number(f.bridge.value),temple:Number(f.temple.value)},
    images:photoPaths,inventory:{quantity:1,store:f.store.value}};
}
function fileData(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);});}
async function uploadSelectedPhotos(){
  for(let i=0;i<3;i++){
    const input=$(`#photo${i}`),file=input.files[0];if(!file)continue;
    const draft=photoDrafts[i];
    if(!draft||draft.file!==file)throw new Error('Περίμενε να εμφανιστεί η προεπισκόπηση φωτογραφίας');
    const choice=document.querySelector(`input[name="photo-choice-${i}"]:checked`)?.value;
    const data=choice==='processed'&&draft.processed?draft.processed:await fileData(file);
    const upload=await api('/api/upload','POST',{name:`${editing||$('#productForm').elements.id.value}-${i}`,data});
    photoPaths[i]=upload.url;input.value='';
  }
  if(photoPaths.some(x=>!x)) throw new Error('Διάλεξε και τις τρεις φωτογραφίες');
}
$('#generate').onclick=async()=>{
  const button=$('#generate');button.disabled=true;msg('Επιλέγεται περιγραφή από τη βιβλιοθήκη…');
  try{
    if(photoPaths.some((path,i)=>!path&&!$(`#photo${i}`).files[0])) throw new Error('Διάλεξε πρώτα τις τρεις φωτογραφίες για να βλέπεις το γυαλί');
    const product=productFromForm();
    const result=await api('/api/draft-description','POST',{...product,variant:descriptionVariant,exclude:seenDrafts});
    const f=$('#productForm').elements;f.short_description.value=result.description;f.description_confirmed.checked=false;
    seenDrafts.push(result.description);descriptionVariant=(descriptionVariant+1)%50;button.textContent='Δημιουργία άλλης περιγραφής';
    msg('Η πρόταση είναι έτοιμη χωρίς εξωτερική υπηρεσία. Έλεγξέ την, άλλαξέ την αν θέλεις και αποθήκευσε το προϊόν.');
    f.short_description.scrollIntoView({behavior:'smooth',block:'center'});
  }catch(error){msg(error.message,true);}finally{button.disabled=false;}
};
$('#productForm').addEventListener('submit',async event=>{
  event.preventDefault();const save=$('#save');save.disabled=true;
  try{
    await uploadSelectedPhotos();
    const product=productFromForm();
    await api(editing?`/api/products/${editing}`:'/api/products',editing?'PUT':'POST',product);
    await refresh();reset();msg(product.short_description?'Το προϊόν αποθηκεύτηκε.':'Το προϊόν αποθηκεύτηκε ως πρόχειρο. Μπορείς να προσθέσεις περιγραφή αργότερα.');
  }catch(error){msg(error.message,true);}finally{save.disabled=false;}
});
$('#new').onclick=reset;
const columns=['id','brand','model','color_code','category','price_eur','lens','bridge','temple','store','material','style','audience','visual_note','short_description','front','three_quarter','side'];
$('#template').onclick=()=>{
  const csv='\uFEFF'+columns.join(',')+'\n';const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);a.download='orama-products-template.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
};
function parseCSV(text){
  const rows=[];let row=[],value='',quoted=false;
  for(let i=0;i<text.length;i++){const ch=text[i];
    if(quoted){if(ch==='"'&&text[i+1]==='"'){value+='"';i++;}else if(ch==='"')quoted=false;else value+=ch;}
    else if(ch==='"')quoted=true;else if(ch===','){row.push(value);value='';}
    else if(ch==='\n'){row.push(value.replace(/\r$/,''));rows.push(row);row=[];value='';}else value+=ch;
  }
  if(quoted)throw new Error('Το CSV έχει μη κλεισμένα εισαγωγικά');
  if(value||row.length){row.push(value.replace(/\r$/,''));rows.push(row);}
  return rows;
}
$('#csv').addEventListener('change',async event=>{
  const file=event.target.files[0];if(!file)return;
  try{
    const rows=parseCSV((await file.text()).replace(/^\uFEFF/,''));
    if(rows[0]?.join('|')!==columns.join('|'))throw new Error('Οι στήλες δεν ταιριάζουν με το υπόδειγμα');
    const items=rows.slice(1).filter(row=>row.some(value=>value.trim())).map((row,index)=>{
      if(row.length!==columns.length)throw new Error(`Λάθος πλήθος στηλών στη γραμμή ${index+2}`);
      const p=Object.fromEntries(columns.map((key,i)=>[key,row[i].trim()]));
      return {id:p.id,brand:p.brand,model:p.model,color_code:p.color_code||null,category:p.category,price_eur:Number(p.price_eur),material:p.material||null,style:p.style||null,audience:p.audience||null,visual_note:p.visual_note,short_description:p.short_description,
        dimensions_mm:{lens:Number(p.lens),bridge:Number(p.bridge),temple:Number(p.temple)},images:[p.front,p.three_quarter,p.side],inventory:{quantity:1,store:p.store}};
    });
    const result=await api('/api/import','POST',{products:items});await refresh();msg(`Εισήχθησαν ${result.imported} προϊόντα.`);
  }catch(error){msg(error.message,true);}finally{event.target.value='';}
});
slots();refresh().catch(error=>msg(error.message,true));
