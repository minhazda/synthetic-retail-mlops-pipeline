"""Self-contained HTML demo UI served at the API root."""

INDEX_HTML = """<!doctype html>
<html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Retail Demand Forecast - Live Demo</title>
<style>
:root{--card:#1e293b;--muted:#94a3b8;--line:#334155;--accent:#38bdf8}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;background:linear-gradient(160deg,#0b1220,#0f172a);color:#e2e8f0;min-height:100vh}
.wrap{max-width:820px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:1.6rem;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 24px;font-size:.95rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
label{display:block;font-size:.78rem;color:var(--muted);margin-bottom:5px}
input,select{width:100%;padding:9px 10px;border-radius:8px;border:1px solid var(--line);background:#0b1220;color:#e2e8f0;font-size:.92rem}
.row{display:flex;gap:10px;align-items:center;margin-top:18px;flex-wrap:wrap}
button{cursor:pointer;border:none;border-radius:9px;padding:11px 18px;font-weight:600;font-size:.92rem}
.primary{background:var(--accent);color:#04263a}.ghost{background:transparent;border:1px solid var(--line);color:#cbd5e1}
.check{display:flex;align-items:center;gap:8px}.check input{width:auto}
.result{display:none}.score{font-size:3rem;font-weight:800;line-height:1;color:#38bdf8}
.meter{height:14px;border-radius:999px;background:#0b1220;border:1px solid var(--line);overflow:hidden;margin:14px 0}
.fill{height:100%;width:0;transition:width .6s ease}
.muted{color:var(--muted);font-size:.85rem}.foot{color:var(--muted);font-size:.8rem;text-align:center;margin-top:26px}
a{color:var(--accent)}
</style></head>
<body><div class='wrap'>
<h1>Retail Demand Forecast</h1>
<p class='sub'>Set the conditions for a store-hour and a LightGBM model served on GCP Cloud Run predicts expected unit demand for that SKU. Try the presets.</p>
<div class='card'><div class='grid'>
<div><label>Hour (0-23)</label><input id='hour' type='number' value='12'></div>
<div><label>Day of week (0-6)</label><input id='day_of_week' type='number' value='2'></div>
<div><label>Weather</label><select id='weather'><option>Sunny</option><option>Rainy</option><option>Cold</option><option>Snowy</option></select></div>
<div><label>Category</label><select id='category'><option>Fresh Produce</option><option>Dairy</option><option>Snacks</option><option>Cleaning</option></select></div>
<div><label>Foot traffic</label><input id='foot_traffic' type='number' value='52'></div>
<div><label>Stock level</label><input id='stock_level' type='number' value='190'></div>
<div><label>Recent hourly sales</label><input id='recent' type='number' value='2'></div>
<div class='check'><input id='promo' type='checkbox'><label style='margin:0'>Promotion active</label></div>
<div class='check'><input id='holiday' type='checkbox'><label style='margin:0'>Holiday</label></div>
</div>
<div class='row'><button class='primary' onclick='forecast()'>Forecast demand</button>
<button class='ghost' onclick=\"preset('busy')\">Busy promo hour</button>
<button class='ghost' onclick=\"preset('quiet')\">Quiet night</button></div></div>
<div class='card result' id='result'>
<div class='muted'>Predicted demand (units this hour)</div>
<div class='score' id='units'>-</div>
<div class='meter'><div class='fill' id='fill'></div></div>
<div class='muted' id='explain'></div></div>
<p class='foot'>LightGBM - hourly per-SKU forecasting - <a href='/docs'>API docs</a> - <a href='https://github.com/minhazda/synthetic-retail-mlops-pipeline'>source</a></p>
</div>
<script>
function val(id){return document.getElementById(id).value;}
function preset(k){var busy={hour:18,day_of_week:5,weather:'Sunny',category:'Snacks',foot_traffic:120,stock_level:200,recent:6,promo:true,holiday:false};
var quiet={hour:3,day_of_week:2,weather:'Cold',category:'Cleaning',foot_traffic:8,stock_level:60,recent:0,promo:false,holiday:false};
var v=k==='busy'?busy:quiet;for(var key in v){var el=document.getElementById(key);if(!el)continue;if(el.type==='checkbox')el.checked=v[key];else el.value=v[key];}}
async function forecast(){var hour=+val('hour'),dow=+val('day_of_week'),ft=+val('foot_traffic'),stock=+val('stock_level'),recent=+val('recent');
var weather=val('weather'),cat=val('category');var promo=document.getElementById('promo').checked?1:0,holiday=document.getElementById('holiday').checked?1:0;
var row={stock_level:stock,promo_flag:promo,holiday_flag:holiday,foot_traffic:ft,hour:hour,day_of_week:dow,sales_lag_1h:recent,sales_lag_24h:recent,sales_lag_7d:recent,sales_roll_3h:recent,stock_lag_1h:stock,weather_Cold:weather==='Cold'?1:0,weather_Rainy:weather==='Rainy'?1:0,weather_Snowy:weather==='Snowy'?1:0,weather_Sunny:weather==='Sunny'?1:0,category_Cleaning:cat==='Cleaning'?1:0,category_Dairy:cat==='Dairy'?1:0,'category_Fresh Produce':cat==='Fresh Produce'?1:0,category_Snacks:cat==='Snacks'?1:0};
var res=await fetch('/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows:[row]})});
if(!res.ok){alert('Error '+res.status);return;}var d=await res.json();var u=Math.max(0,d.predictions[0]);
document.getElementById('result').style.display='block';document.getElementById('units').textContent=u.toFixed(2);
var max=Math.max(8,u*1.3);document.getElementById('fill').style.width=Math.min(u/max*100,100)+'%';document.getElementById('fill').style.background='#38bdf8';
document.getElementById('explain').textContent='Expected units sold for this SKU during the selected hour, given the conditions above.';}
</script></body></html>"""
