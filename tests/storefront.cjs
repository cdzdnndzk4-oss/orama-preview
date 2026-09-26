const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const html = fs.readFileSync('index.html', 'utf8');
const js = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
new vm.Script(js); // syntax check of actual inline storefront script
new vm.Script(fs.readFileSync('service/admin.js', 'utf8'));

const saved = new Map();
const record = id => ({id, brand:'ORAMA', model:id, category:'Γυαλιά Οράσεως', price_eur:120,
  dimensions_mm:{lens:52,bridge:18,temple:140}, availability:{'Αγία Παρασκευή':2,'Κυψέλη':3},
  inventory:{quantity:5,store:'Αγία Παρασκευή · Κυψέλη'}, images:['/img/a','/img/b','/img/c']});
const context = vm.createContext({
  document:{querySelector:()=>({textContent:'0',classList:{add(){},remove(){}}})},
  window:{addEventListener(){}}, location:{search:'?page=category',hash:''},
  localStorage:{getItem:key=>saved.get(key),setItem:(key,value)=>saved.set(key,value)},
  fetch:async url=>({ok:true,status:200,json:async()=>record(url.split('/').pop())}),
  URLSearchParams, Intl, setTimeout, clearTimeout, console,
});
vm.runInContext(js.replace(/fetchCatalog\(\{page:1\}\)\.then\(render\)\.catch\([^\n]+\);\s*$/, ''), context);
(async()=>{
  vm.runInContext("products=[fromCatalog("+JSON.stringify(record('frame-a'))+")]",context);
  vm.runInContext("add('frame-a')",context);
  vm.runInContext("products=[fromCatalog("+JSON.stringify(record('frame-b'))+")]",context);
  assert.equal(vm.runInContext('cart().length',context),1,'pagination must not clear saved cart');
  await vm.runInContext('loadCartProducts()',context);
  assert.equal(vm.runInContext("pById('frame-a').model",context),'frame-a');
  assert.match(vm.runInContext('cartPage()',context),/frame-a/);
  assert.equal(vm.runInContext("fromCatalog("+JSON.stringify(record('frame-c'))+").stock_agia",context),2);
  assert.equal(vm.runInContext("fromCatalog("+JSON.stringify(record('frame-c'))+").stock_kypseli",context),3);
  console.log('storefront syntax, cart/pagination and two-store stock: passed');
})().catch(error=>{console.error(error);process.exitCode=1});
