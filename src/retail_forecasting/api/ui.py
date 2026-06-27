"""Self-contained HTML demo UI served at the API root."""

INDEX_HTML = """<!doctype html>
<html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<link rel='icon' href='data:,'>
<title>Retail Demand Forecast - Live Demo</title>
<style>
:root{--card:#1e293b;--muted:#94a3b8;--line:#334155;--accent:#38bdf8}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;background:linear-gradient(160deg,#0b1220,#0f172a);color:#e2e8f0;min-height:100vh}
.wrap{max-width:840px;margin:0 auto;padding:22px 20px 64px}
.top{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:.85rem;color:var(--muted);border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:22px}
.top b{color:#e2e8f0}.top a{color:var(--accent);text-decoration:none;margin-left:10px}
h1{font-size:1.6rem;margin:0 0 6px}.sub{color:var(--muted);margin:0 0 12px;font-size:.95rem}
.chips{margin:0 0 22px;display:flex;gap:8px;flex-wrap:wrap}
.chip{font-size:.72rem;padding:4px 10px;border-radius:999px;background:#0b1220;border:1px solid var(--line);color:#cbd5e1}
.chip.warn{border-color:#854d0e;color:#fde68a}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
label{display:block;font-size:.78rem;color:var(--muted);margin-bottom:5px}
input,select{width:100%;padding:9px 10px;border-radius:8px;border:1px solid var(--line);background:#0b1220;color:#e2e8f0;font-size:.92rem}
.row{display:flex;gap:10px;align-items:center;margin-top:18px;flex-wrap:wrap}
button{cursor:pointer;border:none;border-radius:9px;padding:11px 18px;font-weight:600;font-size:.92rem}
button:disabled{opacity:.6;cursor:wait}
.primary{background:var(--accent);color:#04263a}.ghost{background:transparent;border:1px solid var(--line);color:#cbd5e1}
.check{display:flex;align-items:center;gap:8px}.check input{width:auto}
.result{display:none}.score{font-size:3rem;font-weight:800;line-height:1;color:#38bdf8}
.badge{display:inline-block;padding:6px 14px;border-radius:999px;font-weight:700;font-size:.85rem}
.meter{height:14px;border-radius:999px;background:#0b1220;border:1px solid var(--line);overflow:hidden;margin:14px 0}
.fill{height:100%;width:0;transition:width .6s ease}
.muted{color:var(--muted);font-size:.85rem}
.why{margin-top:14px;border-top:1px solid var(--line);padding-top:12px}
.why h4{margin:0 0 8px;font-size:.8rem;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.factor{display:flex;align-items:center;gap:9px;padding:4px 0;font-size:.9rem}
.dot{width:9px;height:9px;border-radius:50%;flex:none;background:#38bdf8}
.err{color:#fca5a5}.foot{color:var(--muted);font-size:.8rem;text-align:center;margin-top:26px}a{color:var(--accent)}
</style></head>
<body><div class='wrap'>
<div class='top'><div><b>MD Minhazur Rahman</b> - Data Scientist / ML Engineer</div>
<div><a href='https://github.com/minhazda'>Portfolio</a><a href='https://www.linkedin.com/in/mohammadminhaz/'>LinkedIn</a><a href='https://fraud-detection-api-ude5vos6lq-uc.a.run.app/'>Fraud demo</a></div></div>
<h1>Retail Demand Forecast</h1>
<p class='sub'>Set the conditions for a store-hour and a LightGBM model predicts expected unit demand for that SKU. Try the presets.</p>
<div class='chips'><span class='chip'>LightGBM</span><span class='chip'>MAE -40.8% vs naive baseline</span><span class='chip'>GCP Cloud Run</span><span class='chip warn'>synthetic demo data</span></div>
<div class='card'><div class='grid'>
<div><label>Hour (0-23)</label><input id='hour' type='number' value='12'></div>
<div><label>Day</label><select id='day_of_week'><option value='0'>Monday</option><option value='1'>Tuesday</option><option value='2' selected>Wednesday</option><option value='3'>Thursday</option><option value='4'>Friday</option><option value='5'>Saturday</option><option value='6'>Sunday</option></select></div>
<div><label>Weather</label><select id='weather'><option>Sunny</option><option>Rainy</option><option>Cold</option><option>Snowy</option></select></div>
<div><label>Category</label><select id='category'><option>Fresh Produce</option><option>Dairy</option><option>Snacks</option><option>Cleaning</option></select></div>
<div><label>Foot traffic</label><input id='foot_traffic' type='number' value='52'></div>
<div><label>Stock level</label><input id='stock_level' type='number' value='190'></div>
<div><label>Recent hourly sales</label><input id='recent' type='number' value='2'></div>
<div class='check'><input id='promo' type='checkbox'><label style='margin:0'>Promotion active</label></div>
<div class='check'><input id='holiday' type='checkbox'><label style='margin:0'>Holiday</label></div>
</div>
<div class='row'><button class='primary' id='go' onclick='forecast()'>Forecast demand</button>
<button class='ghost' onclick=\"preset('busy')\">Busy promo hour</button>
<button class='ghost' onclick=\"preset('quiet')\">Quiet night</button></div></div>
<div class='card result' id='result'>
<div style='display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:10px'>
<div><div class='muted'>Predicted demand (units this hour)</div><div class='score' id='units'>-</div></div><div id='badge' class='badge'>-</div></div>
<div class='meter'><div class='fill' id='fill'></div></div>
<div class='muted' id='explain'></div>
<div class='why' id='why' style='display:none'><h4>Demand drivers in this scenario</h4><div id='factors'></div></div></div>
<p class='foot'>LightGBM - hourly per-SKU forecasting - <a href='/docs'>API docs</a> - <a href='https://github.com/minhazda/synthetic-retail-mlops-pipeline'>source</a></p>
</div>
<script>
function val(id){return document.getElementById(id).value;}
function preset(k){var busy={hour:18,day_of_week:'5',weather:'Sunny',category:'Snacks',foot_traffic:120,stock_level:200,recent:6,promo:true,holiday:false};
var quiet={hour:3,day_of_week:'2',weather:'Cold',category:'Cleaning',foot_traffic:8,stock_level:60,recent:0,promo:false,holiday:false};
var v=k==='busy'?busy:quiet;for(var key in v){var el=document.getElementById(key);if(!el)continue;if(el.type==='checkbox')el.checked=v[key];else el.value=v[key];}}
function drivers(o){var f=[];
if(o.promo)f.push('Promotion active');
if(o.holiday)f.push('Public holiday');
if(o.dow>=5)f.push('Weekend');
if((o.hour>=11&&o.hour<=14)||(o.hour>=17&&o.hour<=20))f.push('Peak shopping hour');
if(o.ft>=80)f.push('High foot traffic ('+o.ft+')');
if(o.recent>=4)f.push('Strong recent sales');
if(o.hour<6)f.push('Overnight - low activity');
return f;}
async function forecast(){var hour=+val('hour'),dow=+val('day_of_week'),ft=+val('foot_traffic'),stock=+val('stock_level'),recent=+val('recent');
var weather=val('weather'),cat=val('category');var promo=document.getElementById('promo').checked,holiday=document.getElementById('holiday').checked;
var row={stock_level:stock,promo_flag:promo?1:0,holiday_flag:holiday?1:0,foot_traffic:ft,hour:hour,day_of_week:dow,sales_lag_1h:recent,sales_lag_24h:recent,sales_lag_7d:recent,sales_roll_3h:recent,stock_lag_1h:stock,weather_Cold:weather==='Cold'?1:0,weather_Rainy:weather==='Rainy'?1:0,weather_Snowy:weather==='Snowy'?1:0,weather_Sunny:weather==='Sunny'?1:0,category_Cleaning:cat==='Cleaning'?1:0,category_Dairy:cat==='Dairy'?1:0,'category_Fresh Produce':cat==='Fresh Produce'?1:0,category_Snacks:cat==='Snacks'?1:0};
var go=document.getElementById('go');go.disabled=true;var old=go.textContent;go.textContent='Forecasting...';
var result=document.getElementById('result'),explain=document.getElementById('explain'),why=document.getElementById('why');
result.style.display='block';explain.className='muted';explain.textContent='Waking the model... the first request after idle can take ~10s.';why.style.display='none';document.getElementById('units').textContent='-';document.getElementById('fill').style.width='0';document.getElementById('badge').textContent='';
try{var res=await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows:[row]})});
if(!res.ok)throw new Error('HTTP '+res.status);var d=await res.json();var u=Math.max(0,d.predictions[0]);
document.getElementById('units').textContent=u.toFixed(2);
var level=u<1?['LOW','#94a3b8']:(u<4?['MODERATE','#38bdf8']:['HIGH','#22c55e']);
var badge=document.getElementById('badge');badge.textContent=level[0]+' DEMAND';badge.style.background='#0b1220';badge.style.color=level[1];badge.style.border='1px solid '+level[1];
var max=Math.max(8,u*1.3);var fill=document.getElementById('fill');fill.style.width=Math.min(u/max*100,100)+'%';fill.style.background=level[1];
explain.textContent='Expected units sold for this SKU during the selected hour, given the conditions above.';
var f=drivers({promo:promo,holiday:holiday,dow:dow,hour:hour,ft:ft,recent:recent}),box=document.getElementById('factors');box.innerHTML='';
if(f.length===0){box.innerHTML='<div class=\"factor\"><span class=\"dot\"></span>Baseline conditions - no strong demand drivers.</div>';}
else{f.forEach(function(x){box.innerHTML+='<div class=\"factor\"><span class=\"dot\"></span>'+x+'</div>';});}
why.style.display='block';
}catch(e){explain.className='err';explain.textContent='Could not reach the model ('+e.message+'). It may be waking from idle - please try again in a few seconds.';}
finally{go.disabled=false;go.textContent=old;}}
</script></body></html>"""
