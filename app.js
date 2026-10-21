const $=s=>document.querySelector(s), app=$('#app');
const fmt=n=>n==null?'—':Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})+' EGP';
let me=null, prices=null, chart=null;
async function api(url,method='GET',body){
  try{const r=await fetch('/api'+url,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
    const d=await r.json(); if(!r.ok) throw new Error(d.error||'Request failed'); return d;}
  catch(e){toast(e.message==='Failed to fetch'?'Network error. Check your connection.':e.message);throw e;}}
function toast(m){const t=$('#toast');t.textContent=m;t.style.display='block';setTimeout(()=>t.style.display='none',3500)}
$('#theme').onclick=()=>{document.documentElement.classList.toggle('light');$('#theme').textContent=document.documentElement.classList.contains('light')?'Dark mode':'Light mode'};
const card=k=>{const p=prices.karats[k];if(!p)return`<div class=card><b>${k}K</b><p class=mute>No price yet</p></div>`;
  const c=p.pct>=0?'up':'down';return`<div class=card><b>${k}K Gold</b><div class=big>${fmt(p.price)}<small> /g</small></div>
  <div class=${c}>${p.pct>=0?'↑ +':'↓ '}${p.pct}% (${fmt(p.change)})</div><div class=mute>Previous ${fmt(p.previous)}<br>Updated ${new Date(p.updated_at).toLocaleString()}</div></div>`};
const pricesHtml=()=>`${prices.api_ok===false?'<p class=down>Price feed unavailable — showing the last valid price.</p>':''}
  <div class=grid>${[24,21,18].map(card).join('')}</div>
  <p class=mute>Gold pound: ${fmt(prices.gold_pound)} · Ounce (24K): ${fmt(prices.ounce_24k)}</p>`;
const form=(id,fields,btn)=>`<form id=${id} class=card>${fields.map(([n,l,t,o])=>`<label>${l}${o?`<select name=${n}>${o.map(x=>`<option value="${x[0]}">${x[1]}</option>`).join('')}</select>`:`<input name=${n} type=${t||'number'} step=any required>`}</label>`).join('')}<button class=go>${btn}</button></form>`;
const K=[[24,'24K'],[21,'21K'],[18,'18K']];
const data=f=>Object.fromEntries(new FormData(f));
const bind=(id,fn)=>{const f=$('#'+id);if(f)f.onsubmit=async e=>{e.preventDefault();await fn(data(f))}};
const routes={
 async home(){return`<h1>Track Gold. Calculate Value. Make Better Decisions.</h1><p class=mute>Real-time Egyptian gold prices, smart calculators, historical charts, and personal gold tracking — all in one place.</p>
  <p><a class=go href="#prices"><button class=go>View Gold Prices</button></a> <a href="#calc"><button>Calculate Gold Value</button></a></p>${pricesHtml()}`},
 async prices(){return`<h1>Gold prices</h1>${pricesHtml()}<p><button class=go id=ref>Refresh price</button></p>`},
 async calc(){return`<h1>Calculators</h1><div class=grid>
  ${form('f1',[['karat','Karat','',K],['weight','Weight (g)'],['making_pct','Making charge (%)'],['fees','Extra fees (EGP)']],'Calculate value')}
  ${form('f2',[['karat','Karat','',K],['budget','Budget (EGP)'],['making_pct','Making charge (%)']],'How much gold can I buy?')}
  ${form('f3',[['karat','Karat','',K],['weight','Weight (g)'],['buy_price','Purchase price per gram'],['fees','Purchase fees']],'Calculate profit / loss')}
  </div><div id=out class="card big" style="margin-top:1rem">Results appear here</div>`},
 async portfolio(){if(!me)return needLogin();const p=await api('/portfolio');
  return`<h1>My Gold Portfolio</h1><div class=grid><div class=card>Total value<div class=big>${fmt(p.total_value)}</div></div>
  <div class=card>Investment<div class=big>${fmt(p.total_investment)}</div></div>
  <div class=card>Profit<div class="big ${p.profit>=0?'up':'down'}">${fmt(p.profit)} (${p.pct}%)</div></div><div class=card>Total gold<div class=big>${p.grams} g</div></div></div>
  <div class="card scroll" style="margin:1rem 0"><table><tr><th>Karat<th>Grams<th>Bought at<th>Value<th>P/L<th></tr>${p.items.map(i=>`<tr><td>${i.karat}K<td>${i.weight}<td>${fmt(i.purchase_price)}<td>${fmt(i.value)}<td class=${i.profit>=0?'up':'down'}>${fmt(i.profit)}<td><button data-del=${i.id}>Delete</button></tr>`).join('')||'<tr><td colspan=6 class=mute>No holdings yet. Add your first one below.'}</table></div>
  ${form('fp',[['karat','Karat','',K],['weight','Weight (g)'],['purchase_price','Purchase price per gram'],['date','Purchase date','date'],['fees','Fees']],'Add gold')}`},
 async history(){return`<h1>History</h1><div class=card><select id=hk>${K.map(k=>`<option value=${k[0]}>${k[1]}</option>`)}</select>
  <select id=hd><option value=1>Today<option value=7>7 days<option value=30>1 month<option value=180>6 months<option value=365>1 year</select>
  <canvas id=cv height=120></canvas><p id=hs class=mute></p></div>`},
 async analysis(){const a=await api('/analysis?karat=21');const s=a.d30||{};
  return`<h1>Market analysis (21K)</h1><div class=grid>${[['Daily',a.d1],['Weekly',a.d7],['Monthly',a.d30]].map(([n,x])=>`<div class=card>${n} change<div class=big>${x&&x.pct!=null?x.pct+'%':'—'}</div></div>`).join('')}
  <div class=card>30-day high / low<div class=big>${fmt(s.high)}<br>${fmt(s.low)}</div></div><div class=card>Volatility<div class=big>${a.volatility_pct??'—'}%</div></div></div>
  <p>${a.vs_avg_pct!=null?`21K gold is ${Math.abs(a.vs_avg_pct)}% ${a.vs_avg_pct>=0?'above':'below'} its 30-day average.`:'Not enough data yet.'}</p><p class=mute>Informational only. This is not financial advice and does not predict future prices.</p>`},
 async alerts(){if(!me)return needLogin();const a=await api('/alerts'),n=await api('/notifications');
  return`<h1>Price alerts</h1><div class=grid>${form('fa',[['karat','Karat','',K],['target','Target price (EGP/g)'],['condition','Notify when price','',[['above','reaches above'],['below','falls below']]]],'Create alert')}
  <div class=card><b>Your alerts</b>${a.map(x=>`<p>${x.karat}K ${x.condition} ${fmt(x.target)} — <b>${x.status}</b> <button data-tg=${x.id}>Enable/disable</button><button data-da=${x.id}>Delete</button></p>`).join('')||'<p class=mute>None yet.</p>'}</div>
  <div class=card><b>Notifications</b>${n.map(x=>`<p>${x.message}</p>`).join('')||'<p class=mute>Nothing yet.</p>'}</div></div>`},
 async admin(){if(!me||!me.is_admin)return'<h1>Admins only</h1>';const s=await api('/admin/stats');
  return`<h1>Admin</h1><div class=grid><div class=card>Users<div class=big>${s.users}</div></div><div class=card>Holdings<div class=big>${s.holdings}</div></div>
  <div class=card>Alerts<div class=big>${s.alerts}</div></div><div class=card>API<div class=big>${s.api_ok?'OK':'Down'}</div><small class=mute>Last: ${s.last_ok}</small></div></div>
  ${form('fm',[['price_24k','Manual 24K price (EGP/g)']],'Set price manually')}
  <div class="card scroll"><table>${s.user_list.map(u=>`<tr><td>${u.name}<td>${u.email}<td><button data-us=${u.id}>${u.active?'Disable':'Enable'}</button></tr>`).join('')}</table></div>`},
 async login(){return`<h1>Log in</h1>${form('fl',[['email','Email','email'],['password','Password','password']],'Log in')}<p><a href="#register">Create an account</a></p>`},
 async register(){return`<h1>Create account</h1>${form('fr',[['name','Name','text'],['email','Email','email'],['password','Password (8+ chars)','password']],'Register')}`},
 async dashboard(){if(!me)return needLogin();const p=await api('/portfolio');
  return`<h1>Welcome, ${me.name}</h1>${pricesHtml()}<div class=grid style="margin-top:1rem"><div class=card>Portfolio value<div class=big>${fmt(p.total_value)}</div></div>
  <div class=card>Profit / loss<div class="big ${p.profit>=0?'up':'down'}">${fmt(p.profit)}</div></div></div>
  <p><a href="#portfolio"><button>Add gold</button></a> <a href="#alerts"><button>Set price alert</button></a> <a href="#history"><button>View history</button></a></p>`}
};
const needLogin=()=>'<h1>Please log in</h1><p><a href="#login">Log in</a> or <a href="#register">register</a> to use this page.</p>';
async function loadChart(){const k=$('#hk').value,d=$('#hd').value;const h=await api(`/history?karat=${k}&days=${d}`);
  if(chart)chart.destroy();chart=new Chart($('#cv'),{type:'line',data:{labels:h.points.map(p=>new Date(p.t).toLocaleString()),datasets:[{label:k+'K EGP/g',data:h.points.map(p=>p.p),borderColor:'#d4a73a',tension:.3,pointRadius:0}]}});
  const s=h.stats;$('#hs').textContent=s.high?`High ${fmt(s.high)} · Low ${fmt(s.low)} · Avg ${fmt(s.avg)} · Now ${fmt(s.current)} · Change ${s.pct}%`:'No history collected yet.'}
function wire(page){
  if(page==='history'){$('#hk').onchange=$('#hd').onchange=loadChart;loadChart()}
  if(page==='prices')$('#ref').onclick=async()=>{await api('/prices/refresh','POST');render()};
  if(page==='calc'){const run=(id,kind,fn)=>bind(id,async d=>{const r=await api('/calc/'+kind,'POST',d);$('#out').innerHTML=fn(r)});
    run('f1','value',r=>`Gold ${fmt(r.value)}<br>Making ${fmt(r.making)}<br>Total ${fmt(r.total)}`);
    run('f2','budget',r=>`${r.grams_before} g before making charges<br>${r.grams_after} g after`);
    run('f3','profit',r=>`<span class=${r.profit>=0?'up':'down'}>${fmt(r.profit)} (${r.pct}%)</span><br><small>Now ${fmt(r.current)} vs ${fmt(r.investment)}</small>`)}
  bind('fl',async d=>{me=(await api('/login','POST',d));await boot();location.hash='dashboard'});
  bind('fr',async d=>{await api('/register','POST',d);await boot();location.hash='dashboard'});
  bind('fp',async d=>{await api('/portfolio','POST',d);render()});
  bind('fa',async d=>{await api('/alerts','POST',d);render()});
  bind('fm',async d=>{await api('/admin/prices','POST',d);toast('Price saved');render()});
  document.querySelectorAll('[data-del]').forEach(b=>b.onclick=async()=>{await api('/portfolio/'+b.dataset.del,'DELETE');render()});
  document.querySelectorAll('[data-da]').forEach(b=>b.onclick=async()=>{await api('/alerts/'+b.dataset.da,'DELETE');render()});
  document.querySelectorAll('[data-tg]').forEach(b=>b.onclick=async()=>{await api('/alerts/'+b.dataset.tg,'PATCH');render()});
  document.querySelectorAll('[data-us]').forEach(b=>b.onclick=async()=>{await api('/admin/users/'+b.dataset.us+'/toggle','POST');render()});}
async function render(){const page=(location.hash.slice(1)||'home');prices=(await api('/prices'));
  app.innerHTML=await (routes[page]||routes.home)();wire(page);
  document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('on',a.hash==='#'+page))}
async function boot(){me=(await api('/me')).user;
  const L=[['home','Home'],['prices','Gold Prices'],['calc','Calculators'],['portfolio','Portfolio'],['history','History'],['analysis','Analysis'],['alerts','Alerts'],['dashboard','Dashboard']];
  if(me&&me.is_admin)L.push(['admin','Admin']);
  $('#nav').innerHTML=L.map(([h,t])=>`<a href="#${h}">${t}</a>`).join('')+(me?'<a href="#" id=lo>Log out</a>':'<a href="#login">Login</a><a href="#register">Register</a>');
  if($('#lo'))$('#lo').onclick=async e=>{e.preventDefault();await api('/logout','POST');me=null;await boot();location.hash='home'};render()}
addEventListener('hashchange',render);setInterval(()=>{if(['home','prices','dashboard'].includes(location.hash.slice(1)||'home'))render()},60000);boot();
