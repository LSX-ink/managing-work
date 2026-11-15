/* Shiftnote: tracking (site map, in/out photo log, programme, delays, warnings, actions, resources, team) */
(function(){
"use strict";
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const D=window.SN_DATES, SN=()=>window.SN;
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const sum=(a,f)=>a.reduce((t,x)=>t+(+f(x)||0),0);
const r1=n=>(Math.round(n*10)/10).toString();
const gbp=n=>"£"+Math.round(n).toLocaleString("en-GB");
const ls={get(k,d){try{const v=localStorage.getItem(k);return v?JSON.parse(v):d}catch(e){return d}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v));return true}catch(e){return false}}};
const at=(wd,hm)=>{const d=D.wdAgo(wd);const[h,m]=hm.split(":");d.setHours(+h,+m,0,0);return d};
const hm=d=>d.toTimeString().slice(0,5);
const dayLabel=d=>{const t=new Date();if(d.toDateString()===t.toDateString())return "Today";const y=new Date(t);y.setDate(t.getDate()-1);if(d.toDateString()===y.toDateString())return "Yesterday";return D.fShort(d)};
function dur(ms){const m=Math.max(0,Math.round(ms/60000));if(m<60)return m+" min";const h=Math.floor(m/60),mm=m%60;if(h<24)return h+" h"+(mm?" "+mm+" m":"");const d=Math.floor(h/24),hh=h%24;return d+" day"+(d>1?"s":"")+(hh?" "+hh+" h":"")}

/* ---------- people (stable tints) ---------- */
const PEOPLE={
  "Sam Okafor":{i:"SO",c:"#F6DCCB"},"Priya Nair":{i:"PN",c:"#D6E6F5"},"Mark Turner":{i:"MT",c:"#DDEFD9"},
  "Leah Brooks":{i:"LB",c:"#EEDDF0"},"Joe Hart":{i:"JH",c:"#F3EBC8"}
};
const av=n=>{const p=PEOPLE[n]||{i:(n||"?").split(" ").map(x=>x[0]).join("").slice(0,2),c:"#E6E3DC"};return `<span class="av" style="background:${p.c}" title="${esc(n)}">${esc(p.i)}</span>`};

/* ---------- piers ---------- */
const STAGES=["Piles","Pile cap","Stem","Crosshead","Bearings"];
const PIERS=[
 [1,1,1,1,0],[1,1,1,1,0],[1,1,1,1,0],[1,1,1,0,0],[1,1,1,.3,0],[1,1,0,0,0],
 [1,.7,0,0,0],[1,.35,0,0,0],[1,.15,0,0,0],[1,0,0,0,0],[1,0,0,0,0],[1,0,0,0,0]
].map((st,i)=>({n:i+1,st,stopped:i===8}));
const PIER_EVENTS={
 9:[{wd:0,t:"Excavation stopped at 1.2 m: live duct at 0.9 m, not on drawings",hi:1,ref:"EW-C4-015"},{wd:0,t:"Excavation started (4 groundworkers, 13 t excavator)"},{wd:24,t:"Piles complete and tested"}],
 8:[{wd:0,t:"Blinding poured, 6 m³ (wagon 50 min late)",hi:1},{wd:1,t:"Excavated to formation"},{wd:4,t:"Excavation started; pump 0.5 h late"},{wd:25,t:"Piles complete and tested"}],
 7:[{wd:0,t:"Pile cap rebar complete, ready for inspection"},{wd:1,t:"Pile cap rebar 70%"},{wd:3,t:"Blinding poured"},{wd:26,t:"Piles complete and tested"}],
 6:[{wd:0,t:"Backfill to pile cap 40%"},{wd:2,t:"Pile cap poured; crane stood 1.5 h for wind",hi:1,ref:"EW-C4-014"},{wd:3,t:"Shutters struck on blinding"},{wd:27,t:"Piles complete and tested"}],
 5:[{wd:6,t:"Crosshead rebar started"},{wd:8,t:"RFI-077 answered: crosshead rebar details",ref:"EW-C4-012"},{wd:11,t:"Waited 4 h for crosshead rebar details",hi:1,ref:"EW-C4-012"},{wd:15,t:"Stem poured"}],
 4:[{wd:9,t:"Stem poured"},{wd:14,t:"Water main stand-off: 2.5 h lost",hi:1,ref:"EW-C4-011"},{wd:18,t:"Pile cap poured"}]
};
function pierEvents(n){if(PIER_EVENTS[n])return PIER_EVENTS[n];const p=PIERS[n-1];const ev=[];if(p.st[3]>=1)ev.push({wd:10+n,t:"Crosshead poured"});if(p.st[2]>=1)ev.push({wd:16+n,t:"Stem poured"});if(p.st[1]>=1)ev.push({wd:22+n,t:"Pile cap poured"});ev.push({wd:30+n,t:"Piles complete and tested"});return ev}
const pierPct=p=>sum(p.st,x=>x)/STAGES.length;
const progressNow=()=>sum(PIERS,p=>sum(p.st,x=>x))/(PIERS.length*STAGES.length)*100;
const PLAN=[0,3,7,12,18,24,30,36,42,49,55,61,67];const CW=9;
function behindDays(){const a=progressNow();for(let w=1;w<PLAN.length;w++){if(PLAN[w]>=a){const wf=w-1+(a-PLAN[w-1])/(PLAN[w]-PLAN[w-1]);return Math.round((CW-wf)*5)}}return 0}

/* ---------- delays log ---------- */
const RATE=35, PLANT_RATE={"13 t excavator":55,"90 t crane":180};
const BASE_DELAYS=[
 {wd:2,cause:"Weather",loc:"Pier 6",what:"Crane stood: wind over lift limit",h:1.5,ppl:5,plant:"90 t crane",ew:"EW-C4-014"},
 {wd:4,cause:"Supplier",loc:"Pier 8",what:"Concrete pump arrived late",h:.5,ppl:3},
 {wd:6,cause:"Weather",loc:"Piers 4–5",what:"Heavy rain, work stopped",h:2,ppl:6},
 {wd:8,cause:"Plant breakdown",loc:"Pier 7",what:"Excavator hydraulic hose burst",h:3,ppl:2,plant:"13 t excavator"},
 {wd:11,cause:"Design information",loc:"Pier 5",what:"Waiting for crosshead rebar details (RFI-077)",h:4,ppl:4,ew:"EW-C4-012"},
 {wd:14,cause:"Utilities",loc:"Pier 4",what:"Water main stand-off",h:2.5,ppl:4,ew:"EW-C4-011"},
 {wd:17,cause:"Supplier",loc:"Pier 3",what:"Rebar delivery late",h:1,ppl:6}
];
function delays(){
 const out=BASE_DELAYS.slice();const f=SN()&&SN().filed;
 if(f){(f.diary.delays||[]).forEach(x=>{
   const m=/(\d+)/.exec(x.affected||"");const ppl=m?+m[1]:1;
   const plant=/excavator/i.test(x.affected||"")?"13 t excavator":/crane/i.test(x.affected||"")?"90 t crane":null;
   const c=/duct|cable|service|utilit|main/i.test(x.cause)?"Utilities":/wagon|concrete|deliver|supplier|pump/i.test(x.cause)?"Supplier":/rain|wind|weather|snow/i.test(x.cause)?"Weather":/broke|breakdown/i.test(x.cause)?"Plant breakdown":"Other";
   out.unshift({wd:0,cause:c,loc:x.location,what:x.cause.split(".")[0],h:x.hours||0,ppl,plant,ew:c==="Utilities"?"EW-C4-015":null});
 })}
 out.forEach(d=>d.cost=d.h*d.ppl*RATE+(d.plant?d.h*(PLANT_RATE[d.plant]||0):0));
 return out;
}

/* ---------- early warnings ---------- */
const EW_STAGES=["Raised","Sent","Meeting","Agreed","Closed"];
function warnings(){
 const w=[
  {ref:"EW-C4-014",title:"Pier 6 crane lift plan: wind limits",wd:2,stage:1,next:"Hold early warning meeting",who:"Joe Hart"},
  {ref:"EW-C4-013",title:"Bearing delivery lead time, piers 1–3",wd:7,stage:2,next:"Meeting booked: supplier dates",who:"Leah Brooks"},
  {ref:"EW-C4-012",title:"Pier 5 crosshead rebar details missing",wd:11,stage:3,next:"Agreed: re-sequence; record time lost",who:"Priya Nair"},
  {ref:"EW-C4-011",title:"Water main stand-off at pier 4",wd:14,stage:4,next:"Closed",who:"Mark Turner"}
 ];
 const f=SN()&&SN().filed;
 if(f)(f.ews||[]).forEach((e,i)=>w.unshift({ref:"EW-C4-0"+(15+i),title:e.title,wd:0,stage:1,next:"Hold early warning meeting",who:"Sam Okafor",fresh:1}));
 w.forEach(x=>{x.age=x.wd;x.overdue=x.stage<2&&x.age>=2});
 return w;
}

/* ---------- actions ---------- */
function actions(){
 const base=[
  {id:"a1",t:"Chase bearing delivery dates for piers 1–3",who:"Leah Brooks",due:-1},
  {id:"a2",t:"Revise pier 6 lift plan for wind limits",who:"Joe Hart",due:2},
  {id:"a3",t:"Close out RFI-077 answers on site",who:"Sam Okafor",due:-3,done0:1},
 ];
 const f=SN()&&SN().filed;
 const extra=f?(f.diary.actions||[]).map((t,i)=>({id:"t"+i,t,who:/drawing|design/i.test(t)?"Priya Nair":/diversion|owner|utilit/i.test(t)?"Mark Turner":"Sam Okafor",due:1,fresh:1})):[];
 const done=ls.get("shiftnote-actions",{});
 return [...extra,...base].map(a=>({...a,done:done[a.id]!=null?done[a.id]:!!a.done0}));
}

/* ---------- in / out log ---------- */
const SK=(path)=>`<svg viewBox="0 0 92 92" aria-hidden="true"><rect width="92" height="92" fill="#D9D5CC"/><path d="M0 70h92v22H0z" fill="#B9B3A6"/>${path}</svg>`;
const ART={
 exc:SK('<path d="M18 62h40v-12H30z" fill="#6E675B"/><path d="M46 50l14-18 16 8-4 6-12-4-8 10" fill="none" stroke="#5B5348" stroke-width="4" stroke-linejoin="round"/><rect x="14" y="62" width="48" height="8" rx="4" fill="#3E3a33"/>'),
 truck:SK('<rect x="10" y="40" width="46" height="24" fill="#8E877A"/><path d="M56 48h14l8 8v8H56z" fill="#6E675B"/><circle cx="24" cy="66" r="5" fill="#3E3a33"/><circle cx="66" cy="66" r="5" fill="#3E3a33"/>'),
 mixer:SK('<ellipse cx="34" cy="48" rx="22" ry="13" fill="#9A9385" transform="rotate(-12 34 48)"/><path d="M58 46h12l8 10v8H58z" fill="#6E675B"/><rect x="10" y="60" width="66" height="5" fill="#5B5348"/><circle cx="22" cy="68" r="5" fill="#3E3a33"/><circle cx="68" cy="68" r="5" fill="#3E3a33"/>'),
 rebar:SK('<g stroke="#5B5348" stroke-width="2.5"><path d="M8 58h76M8 62h76M8 66h76M10 54h72"/></g><rect x="20" y="52" width="4" height="16" fill="#E25A0E"/><rect x="66" y="52" width="4" height="16" fill="#E25A0E"/>'),
 dumper:SK('<path d="M14 48h30l6 14H14z" fill="#E2A33A"/><rect x="50" y="44" width="16" height="18" fill="#6E675B"/><circle cx="24" cy="66" r="6" fill="#3E3a33"/><circle cx="60" cy="66" r="6" fill="#3E3a33"/>'),
 skip:SK('<path d="M14 50h64l-8 18H22z" fill="#C7A12A"/><path d="M22 50l6-8h18l-4 8" fill="#8E877A"/>')
};
const BASE_GATE=[
 {id:"g1",cat:"Delivery",desc:"Concrete wagon: 6 m³ blinding for pier 8",ref:"Ticket 48812",inAt:at(0,"09:00"),outAt:at(0,"09:48"),art:"mixer",who:"Sam Okafor"},
 {id:"g2",cat:"Plant",desc:"13 t tracked excavator (hired)",ref:"Hire HC-2291",inAt:at(9,"07:40"),outAt:null,art:"exc",who:"Sam Okafor"},
 {id:"g3",cat:"Plant",desc:"6 t forward-tip dumper",ref:"Fleet D-06",inAt:at(4,"07:15"),outAt:null,art:"dumper",who:"Sam Okafor"},
 {id:"g4",cat:"Materials",desc:"Rebar for pier 7 pile cap, 4.2 t",ref:"Delivery note 7731",inAt:at(2,"10:15"),outAt:at(2,"11:05"),art:"rebar",who:"Sam Okafor"},
 {id:"g5",cat:"Waste",desc:"8 yd skip, mixed waste (swapped)",ref:"WTN 0912",inAt:at(5,"08:30"),outAt:at(1,"13:20"),art:"skip",who:"Sam Okafor"},
 {id:"g6",cat:"Delivery",desc:"Shuttering ply and timber",ref:"DN 22018",inAt:at(3,"07:55"),outAt:at(3,"08:25"),art:"truck",who:"Sam Okafor"}
];
function gate(){
 const mine=ls.get("shiftnote-gate",[]).map(g=>({...g,inAt:new Date(g.inAt),outAt:g.outAt?new Date(g.outAt):null,mine:1}));
 const outs=ls.get("shiftnote-gate-outs",{});
 const base=BASE_GATE.map(g=>outs[g.id]?{...g,outAt:new Date(outs[g.id].at),outPhoto:outs[g.id].photo,outGps:outs[g.id].gps}:g);
 return [...mine,...base].sort((a,b)=>b.inAt-a.inAt);
}
window.SNGate={today(){const t=new Date().toDateString();return gate().filter(g=>g.inAt.toDateString()===t||(g.outAt&&g.outAt.toDateString()===t))}};

/* ---------- photo stamping ---------- */
let geo=null;
function getGeo(){return new Promise(res=>{if(!navigator.geolocation)return res(null);navigator.geolocation.getCurrentPosition(p=>{geo={lat:p.coords.latitude,lon:p.coords.longitude,acc:Math.round(p.coords.accuracy)};res(geo)},()=>res(null),{enableHighAccuracy:true,timeout:8000,maximumAge:60000})})}
const gpsTxt=g=>g?`${Math.abs(g.lat).toFixed(4)}° ${g.lat>=0?"N":"S"}, ${Math.abs(g.lon).toFixed(4)}° ${g.lon>=0?"E":"W"}`:"Location not shared";
function stampPhoto(file,label,when,g){
 return new Promise((res,rej)=>{
  const img=new Image();const url=URL.createObjectURL(file);
  img.onload=()=>{
   const max=720, k=Math.min(1,max/Math.max(img.width,img.height));
   const w=Math.round(img.width*k), h=Math.round(img.height*k);
   const c=document.createElement("canvas");c.width=w;c.height=h;const x=c.getContext("2d");
   x.drawImage(img,0,0,w,h);
   const bh=Math.max(46,Math.round(h*.11));x.fillStyle="rgba(22,24,26,.78)";x.fillRect(0,h-bh,w,bh);
   x.fillStyle=label==="IN"?"#2C7A4B":"#E25A0E";x.fillRect(0,h-bh,Math.round(bh*1.25),bh);
   x.fillStyle="#fff";x.font=`600 ${Math.round(bh*.38)}px "IBM Plex Sans",sans-serif`;x.textBaseline="middle";x.textAlign="center";
   x.fillText(label,Math.round(bh*.625),h-bh/2);x.textAlign="left";
   x.font=`500 ${Math.round(bh*.3)}px "IBM Plex Mono",monospace`;
   x.fillText(when.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"})+"  "+when.toTimeString().slice(0,8),Math.round(bh*1.25)+10,h-bh*.68);
   x.fillStyle="#C9CCD0";x.fillText(gpsTxt(g)+"  ·  Viaduct C4",Math.round(bh*1.25)+10,h-bh*.3);
   URL.revokeObjectURL(url);res(c.toDataURL("image/jpeg",.72));
  };
  img.onerror=()=>{URL.revokeObjectURL(url);rej()};img.src=url;
 });
}
async function aiDescribe(dataUrl){
 try{const ctl=new AbortController();setTimeout(()=>ctl.abort(),15000);
  const r=await fetch("/api/photo",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({image:dataUrl.split(",")[1]}),signal:ctl.signal});
  if(!r.ok)return null;const j=await r.json();return j.description||null}catch(e){return null}
}

/* ---------- sheet ---------- */
let sheet,bg;
function openSheet(html){
 if(!sheet){bg=document.createElement("div");bg.className="sheet-bg";sheet=document.createElement("div");sheet.className="sheet";sheet.setAttribute("role","dialog");document.body.append(bg,sheet);bg.onclick=closeSheet}
 sheet.innerHTML='<div class="grab"></div>'+html;sheet.scrollTop=0;
 requestAnimationFrame(()=>{bg.classList.add("on");sheet.classList.add("on")});
}
function closeSheet(){if(sheet){sheet.classList.remove("on");bg.classList.remove("on")}}
document.addEventListener("click",e=>{if(e.target.closest("[data-sheet-close]"))closeSheet()});

/* ---------- render ---------- */
let tab="site", selPier=9;
const TABS=[["site","Site map"],["gate","In / Out"],["prog","Programme"],["delays","Delays"],["ew","Warnings"],["act","Actions"],["res","Labour & plant"],["team","Team"]];
function render(){
 if(!$("#s-track"))return;
 const prog=progressNow(), bd=behindDays(), dl=delays(), ews=warnings().filter(w=>w.stage<4), acts=actions(), od=acts.filter(a=>!a.done&&a.due<0).length;
 const month=dl.filter(d=>d.wd<=20);
 const stopped=PIERS.filter(p=>p.stopped).map(p=>"Pier "+p.n);
 $("#trFinding").innerHTML=`<i class="dot"></i><div><b>Viaduct C4 is ${bd} working day${bd===1?"":"s"} behind plan.</b> <span class="muted">${stopped.length?stopped.join(", ")+" stopped by the live duct.":""}</span></div>`;
 $("#trKv").innerHTML=`<div><span>Built</span><b>${Math.round(prog)}%<small> of ${PLAN[CW]}% planned</small></b></div><div><span>Lost, last 4 weeks</span><b>${r1(sum(month,d=>d.h))} h<small> · ${gbp(sum(month,d=>d.cost))}</small></b></div><div><span>Open early warnings</span><b>${ews.length}</b></div><div><span>Actions overdue</span><b style="${od?"color:var(--hi-ink)":""}">${od}</b></div>`;
 const onSite=gate().filter(g=>!g.outAt).length;
 $("#trTabs").innerHTML=TABS.map(([k,l])=>`<button role="tab" data-tr="${k}" class="${tab===k?"on":""}">${l}${k==="gate"?`<span class="n" style="background:var(--ink3)">${onSite}</span>`:k==="ew"&&ews.some(w=>w.overdue)?'<span class="n">!</span>':""}</button>`).join("");
 const B=$("#trBody");
 B.innerHTML=({site:siteHTML,gate:gateHTML,prog:progHTML,delays:delaysHTML,ew:ewHTML,act:actHTML,res:resHTML,team:teamHTML})[tab]();
}
document.addEventListener("click",e=>{
 const t=e.target.closest("[data-tr]");if(t){tab=t.dataset.tr;render();t.scrollIntoView({inline:"center",block:"nearest",behavior:"smooth"});return}
 const p=e.target.closest("[data-pier]");if(p){selPier=+p.dataset.pier;render();openPier(selPier);return}
 const a=e.target.closest("[data-act]");if(a){const d=ls.get("shiftnote-actions",{});const cur=actions().find(x=>x.id===a.dataset.act);d[a.dataset.act]=!cur.done;ls.set("shiftnote-actions",d);render();if(!cur.done)SN().toast("Action done. The owner is told.");return}
 const g=e.target.closest("[data-gate-in]");if(g){startGate("in");return}
 const go=e.target.closest("[data-gate-out]");if(go){startGate("out",go.dataset.gateOut);return}
 const gv=e.target.closest("[data-gate-view]");if(gv){viewGate(gv.dataset.gateView);return}
 const pdf=e.target.closest("[data-print]");if(pdf){window.print();return}
});

function vmap(){
 const W=360,H=196,G=132,x0=18,dx=29.5;
 const fillFor=(v,stopped)=>v>=1?"var(--ink)":v>0?(stopped?"url(#hatch)":"var(--hi)"):"none";
 const strokeFor=(v)=>v>=1?"var(--ink)":v>0?"var(--hi)":"var(--line2)";
 let s=`<svg class="vmap" viewBox="0 0 ${W} ${H}" role="img" aria-label="Viaduct C4 elevation, piers 1 to 12"><defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="#FCE9DC"/><rect width="2.2" height="5" fill="#E25A0E"/></pattern></defs>`;
 s+=`<path d="M0 ${G}H${W}" stroke="var(--ink3)" stroke-width="1"/><rect x="0" y="${G}" width="${W}" height="${H-G}" fill="#E7E4DD"/>`;
 s+=`<path d="M6 34H${W-6}" stroke="var(--line2)" stroke-width="5" stroke-dasharray="6 5"/><text x="8" y="26">Deck (to come)</text>`;
 PIERS.forEach((p,i)=>{
  const cx=x0+i*dx+dx/2-14;const sel=p.n===selPier;const [pl,cap,st,ch]=p.st;
  s+=`<g class="${sel?"sel":""}">`;
  if(sel)s+=`<rect x="${cx-12}" y="40" width="${dx-1}" height="${H-46}" rx="6" fill="#fff" stroke="var(--line2)"/>`;
  // piles
  s+=`<path d="M${cx-5} ${G+6}v34M${cx+5} ${G+6}v34" stroke="${pl>=1?"var(--ink)":"var(--line2)"}" stroke-width="3"/>`;
  // cap (partial fills from bottom)
  s+=`<rect x="${cx-10}" y="${G-12}" width="20" height="12" fill="none" stroke="${strokeFor(cap)}" stroke-width="1.2" ${cap?"":'stroke-dasharray="2 2"'}/>`;
  if(cap>0)s+=`<rect x="${cx-10}" y="${G-12*Math.min(1,cap)}" width="20" height="${12*Math.min(1,cap)}" fill="${fillFor(cap,p.stopped)}"/>`;
  // stem
  s+=`<rect x="${cx-5}" y="56" width="10" height="${G-12-56}" fill="none" stroke="${strokeFor(st)}" stroke-width="1.2" ${st?"":'stroke-dasharray="2 2"'}/>`;
  if(st>0)s+=`<rect x="${cx-5}" y="${56+(G-12-56)*(1-st)}" width="10" height="${(G-12-56)*st}" fill="${fillFor(st,0)}"/>`;
  // crosshead
  s+=`<rect x="${cx-11}" y="46" width="22" height="10" fill="none" stroke="${strokeFor(ch)}" stroke-width="1.2" ${ch?"":'stroke-dasharray="2 2"'}/>`;
  if(ch>0)s+=`<rect x="${cx-11}" y="46" width="${22*ch}" height="10" fill="${fillFor(ch,0)}"/>`;
  s+=`<text x="${cx}" y="${H-4}" text-anchor="middle">P${p.n}</text>`;
  if(p.stopped)s+=`<circle cx="${cx+9}" cy="${G-22}" r="5" fill="var(--hi)"/><text x="${cx+9}" y="${G-19}" text-anchor="middle" style="fill:#fff;font-size:8px;font-weight:600">!</text>`;
  s+=`<rect class="hit" data-pier="${p.n}" x="${cx-13}" y="20" width="${dx}" height="${H-20}"><title>Pier ${p.n}</title></rect></g>`;
 });
 return s+"</svg>";
}
function siteHTML(){
 return `<div class="card" style="padding:12px 10px 8px">
  <div class="row between" style="padding:0 4px"><h2>Viaduct C4</h2><span class="small muted">Tap a pier</span></div>
  ${vmap()}
  <div class="legend" style="padding:0 4px"><span><i style="background:var(--ink)"></i>Built</span><span><i style="background:var(--hi)"></i>In progress</span><span><i style="background:repeating-linear-gradient(135deg,var(--hi) 0 2px,var(--hi-soft) 2px 5px)"></i>Stopped</span><span><i style="border:1px dashed var(--line2)"></i>To build</span></div>
 </div>
 <h3 style="margin:16px 0 8px">Needs attention</h3>
 <div class="list">
  <button class="li" data-pier="9"><i class="dot"></i><div><div class="t">Pier 9: excavation stopped</div><div class="s">Live duct at 0.9 m, not on drawings · EW-C4-015</div></div></button>
  <button class="li" data-pier="7"><i class="dot" style="background:var(--ink3)"></i><div><div class="t">Pier 7: pile cap inspection</div><div class="s">Rebar complete · due ${D.fShort(D.wdAhead(1))}</div></div></button>
  <button class="li" data-pier="5"><i class="dot" style="background:var(--ink3)"></i><div><div class="t">Pier 5: crosshead 30%</div><div class="s">Re-sequenced after RFI-077 · EW-C4-012 agreed</div></div></button>
 </div>`;
}
function openPier(n){
 const p=PIERS[n-1];const ev=pierEvents(n);const dl=delays().filter(d=>(d.loc||"").includes(String(n))&&new RegExp("\\b"+n+"\\b").test(d.loc||""));
 const photos=SN().SAMPLE_PHOTOS.filter(x=>x.label.startsWith("Pier "+n));
 openSheet(`<div class="row between"><h1>Pier ${n}</h1><span class="pill ${p.stopped?"hi":pierPct(p)>=.8?"ok":""}">${p.stopped?"Stopped":Math.round(pierPct(p)*100)+"% built"}</span></div>
  <div class="card" style="margin-top:12px;padding:8px 14px">${STAGES.map((s,i)=>{const v=p.st[i];return `<div class="row between" style="padding:8px 0;${i?"border-top:1px solid var(--line)":""}"><span>${s}</span><span class="small" style="${v>0&&v<1?"color:var(--hi-ink);font-weight:600":v>=1?"":"color:var(--ink3)"}">${v>=1?"Complete":v>0?(p.stopped&&i===1?"Stopped · ":"")+Math.round(v*100)+"%":"Not started"}</span></div>`}).join("")}</div>
  ${dl.length?`<h3 style="margin:16px 0 6px">Time lost here</h3><div class="list">${dl.map(d=>`<div class="li"><div><div class="t">${esc(d.what)}</div><div class="s">${esc(D.fShort(D.wdAgo(d.wd)))} · ${r1(d.h)} h · ${gbp(d.cost)}</div></div>${d.ew?`<span class="end pill hi">${d.ew}</span>`:""}</div>`).join("")}</div>`:""}
  ${photos.length?`<h3 style="margin:16px 0 6px">Photos</h3><div class="photos">${photos.map(x=>`<div class="ph">${x.svg}<em>${esc(D.fShort(D.TODAY))}</em></div>`).join("")}</div>`:""}
  <h3 style="margin:16px 0 6px">History, from the diaries</h3>
  <ul class="tl">${ev.map(e=>`<li class="${e.hi?"hi":""}"><div>${esc(e.t)}</div><div class="small muted">${esc(D.fDay(D.wdAgo(e.wd)))}${e.ref?` · <span class="mono">${e.ref}</span>`:""}</div></li>`).join("")}</ul>
  <button class="btn line full" data-sheet-close style="margin-top:14px">Close</button>`);
}

/* in / out */
function gateRow(g){
 const on=!g.outAt;const span=(g.outAt||new Date())-g.inAt;
 const img=g.inPhoto?`<img src="${g.inPhoto}" alt="">`:ART[g.art]||ART.truck;
 return `<div class="li" style="align-items:flex-start"><button class="ph" data-gate-view="${g.id}" style="width:64px;height:64px;border-radius:10px">${img}</button>
  <button style="min-width:0;flex:1;text-align:left" data-gate-view="${g.id}"><div class="t">${esc(g.desc)}</div>
   <div class="s">In ${esc(dayLabel(g.inAt))} ${hm(g.inAt)}${g.outAt?` · Out ${esc(dayLabel(g.outAt))} ${hm(g.outAt)}`:""}</div>
   <div class="s"><span class="pill" style="height:20px">${esc(g.cat)}</span> ${on?`<b style="color:var(--ink)">On site ${dur(span)}</b>`:`On site ${dur(span)}`}</div></button>
  ${on?`<button class="btn line" data-gate-out="${g.id}" style="height:40px;padding:0 12px;font-size:13px;flex:none">Log out</button>`:""}</div>`;
}
function gateHTML(){
 const all=gate();const on=all.filter(g=>!g.outAt), off=all.filter(g=>g.outAt);
 const plantOn=on.filter(g=>g.cat==="Plant");
 return `<div class="card" style="background:var(--ink);color:#fff;border-color:var(--ink)">
  <h2 style="color:#fff">Log something in or out</h2>
  <p class="small" style="color:#B9BCC0;margin-top:4px">Take a photo at the gate. The time and place are stamped on it. Add what it is, and photograph it again when it leaves.</p>
  <button class="btn full" data-gate-in style="margin-top:14px;background:var(--ok);color:#fff"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>Photo it in</button>
 </div>
 ${plantOn.length?`<div class="finding" style="margin-top:14px"><i class="dot"></i><div><b>${plantOn.length} hired or fleet plant on site.</b> <span class="muted">Longest: ${esc(plantOn.sort((a,b)=>a.inAt-b.inAt)[0].desc)}, ${dur(new Date()-plantOn[0].inAt)}. Check it's still needed before the next hire week.</span></div></div>`:""}
 <h3 style="margin:16px 0 8px">On site now · ${on.length}</h3>
 <div class="list">${on.map(gateRow).join("")||'<div class="li muted">Nothing logged in.</div>'}</div>
 <h3 style="margin:16px 0 8px">Left site</h3>
 <div class="list">${off.slice(0,8).map(gateRow).join("")}</div>`;
}
let pending=null;
function camInput(){let i=$("#gateCam");if(!i){i=document.createElement("input");i.type="file";i.accept="image/*";i.setAttribute("capture","environment");i.id="gateCam";i.className="hide";document.body.append(i);i.addEventListener("change",onGatePhoto)}return i}
function startGate(dir,id){pending={dir,id};getGeo();const i=camInput();i.value="";i.click()}
async function onGatePhoto(e){
 const f=e.target.files&&e.target.files[0];if(!f||!pending)return;
 const when=new Date();const g=geo||await Promise.race([getGeo(),new Promise(r=>setTimeout(()=>r(null),2500))]);
 let photo;try{photo=await stampPhoto(f,pending.dir==="in"?"IN":"OUT",when,g)}catch(err){SN().toast("Couldn't read that photo");return}
 if(pending.dir==="in"){
  openSheet(`<h1>Logged in</h1><p class="sub">Stamped ${esc(when.toLocaleDateString("en-GB",{weekday:"short",day:"numeric",month:"short"}))} at ${when.toTimeString().slice(0,5)}</p>
   <div style="margin-top:12px;border-radius:12px;overflow:hidden;border:1px solid var(--line)"><img src="${photo}" alt="Photo stamped IN" style="width:100%;display:block"></div>
   <p class="gps" style="margin-top:8px">${pinSvg}${esc(gpsTxt(g))}${g?" · ±"+g.acc+" m":""}</p>
   <h3 style="margin:14px 0 6px">What is it?</h3>
   <textarea id="gDesc" class="transcript" rows="2" style="min-height:0;width:100%;font-size:16px" placeholder="e.g. 13 t excavator on low loader, hired"></textarea>
   <p class="small muted" id="gAi" style="margin-top:6px">Reading the photo…</p>
   <h3 style="margin:12px 0 6px">Type</h3>
   <div class="row" id="gCat" style="gap:6px;flex-wrap:wrap">${["Plant","Delivery","Materials","Waste","Vehicle"].map((c,i)=>`<button class="pill ${i===0?"hi":""}" data-cat="${c}" style="height:32px;padding:0 12px">${c}</button>`).join("")}</div>
   <h3 style="margin:12px 0 6px">Ticket, hire or reg number <span style="font-weight:400">(optional)</span></h3>
   <input id="gRef" class="search" style="width:100%;font-size:16px" placeholder="e.g. Hire HC-2291">
   <button class="btn dark full" id="gSave" style="margin-top:16px">Save to the log</button>`);
  let cat="Plant";
  $("#gCat").onclick=ev=>{const b=ev.target.closest("[data-cat]");if(!b)return;cat=b.dataset.cat;$$("#gCat .pill").forEach(x=>x.classList.toggle("hi",x===b))};
  aiDescribe(photo).then(d=>{const el=$("#gAi");if(!el)return;if(d){if(!$("#gDesc").value)$("#gDesc").value=d;el.textContent="Suggested from the photo. Change it if it's wrong."}else el.textContent="Type what it is."});
  $("#gSave").onclick=()=>{
   const desc=$("#gDesc").value.trim()||"Item logged in";
   const list=ls.get("shiftnote-gate",[]);
   const item={id:"m"+Date.now(),cat,desc,ref:$("#gRef").value.trim(),inAt:when.toISOString(),outAt:null,inPhoto:photo,inGps:g,who:"Sam Okafor"};
   list.unshift(item);
   if(!ls.set("shiftnote-gate",list)){list[0].inPhoto=null;ls.set("shiftnote-gate",list);SN().toast("Saved (photo too big to keep in this demo)")}
   closeSheet();tab="gate";render();SN().toast("Logged in at "+hm(when));
  };
 }else{
  const item=gate().find(x=>x.id===pending.id);if(!item)return;
  if(item.mine){const list=ls.get("shiftnote-gate",[]);const it=list.find(x=>x.id===item.id);it.outAt=when.toISOString();it.outPhoto=photo;it.outGps=g;if(!ls.set("shiftnote-gate",list)){it.outPhoto=null;ls.set("shiftnote-gate",list)}}
  else{const o=ls.get("shiftnote-gate-outs",{});o[item.id]={at:when.toISOString(),photo,gps:g};if(!ls.set("shiftnote-gate-outs",o)){o[item.id].photo=null;ls.set("shiftnote-gate-outs",o)}}
  render();viewGate(item.id);SN().toast("Logged out. On site "+dur(when-item.inAt));
 }
 pending=null;
}
const pinSvg='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>';
function viewGate(id){
 const g=gate().find(x=>x.id===id);if(!g)return;
 const pic=(src,art,lab)=>`<div style="flex:1;min-width:0"><div class="small muted" style="margin-bottom:4px">${lab}</div><div style="border-radius:10px;overflow:hidden;border:1px solid var(--line);aspect-ratio:1;background:var(--sunk)">${src?`<img src="${src}" alt="" style="width:100%;height:100%;object-fit:cover;display:block">`:art?`<div style="width:100%;height:100%">${art}</div>`:'<div style="height:100%;display:grid;place-items:center" class="small muted">Not yet</div>'}</div></div>`;
 openSheet(`<div class="row between"><span class="pill">${esc(g.cat)}</span>${g.outAt?'<span class="pill">Left site</span>':'<span class="pill ok">On site</span>'}</div>
  <h1 style="margin-top:8px;font-size:21px">${esc(g.desc)}</h1>${g.ref?`<p class="mono muted" style="margin-top:2px">${esc(g.ref)}</p>`:""}
  <div class="row" style="gap:10px;margin-top:14px;align-items:flex-start">${pic(g.inPhoto,g.inPhoto?null:ART[g.art],"In")}${pic(g.outPhoto,(!g.outPhoto&&g.outAt&&!g.mine)?ART[g.art]:null,"Out")}</div>
  <div class="card" style="margin-top:14px;padding:6px 14px">
   <div class="row between" style="padding:8px 0"><span class="muted">Arrived</span><span>${esc(D.fDay(g.inAt))} ${hm(g.inAt)}</span></div>
   <div class="row between" style="padding:8px 0;border-top:1px solid var(--line)"><span class="muted">Left</span><span>${g.outAt?esc(D.fDay(g.outAt))+" "+hm(g.outAt):"Still on site"}</span></div>
   <div class="row between" style="padding:8px 0;border-top:1px solid var(--line)"><span class="muted">Time on site</span><b>${dur((g.outAt||new Date())-g.inAt)}</b></div>
   <div class="row between" style="padding:8px 0;border-top:1px solid var(--line)"><span class="muted">Logged by</span><span>${esc(g.who||"Sam Okafor")}</span></div>
   ${g.inGps?`<div class="row between" style="padding:8px 0;border-top:1px solid var(--line)"><span class="muted">Place</span><span class="small">${esc(gpsTxt(g.inGps))}</span></div>`:""}
  </div>
  ${g.outAt?"":`<button class="btn dark full" data-gate-out="${g.id}" style="margin-top:14px">Photo it out</button>`}
  <button class="btn line full" data-sheet-close style="margin-top:10px">Close</button>`);
}

/* programme */
function progHTML(){
 const a=progressNow(), bd=behindDays();
 const W=330,H=170,L=30,Bt=150,T=12, xs=w=>L+(w/(PLAN.length-1))*(W-L-8), ys=v=>Bt-(v/80)*(Bt-T);
 const act=PLAN.slice(0,CW+1).map((p,w)=>w===CW?a:p*(0.9+0.1*(1-w/CW))*(a/PLAN[CW])/(0.9)+0);
 act[0]=0;
 // keep actual monotonic and ending at today's value
 for(let i=1;i<act.length;i++)act[i]=Math.max(act[i-1],Math.min(act[i],a));act[CW]=a;
 const path=(arr,n)=>arr.slice(0,n).map((v,w)=>(w?"L":"M")+xs(w).toFixed(1)+" "+ys(v).toFixed(1)).join("");
 let s=`<svg class="scurve" viewBox="0 0 ${W} ${H+14}" role="img" aria-label="Planned against actual progress">`;
 [0,20,40,60,80].forEach(v=>s+=`<path d="M${L} ${ys(v)}H${W-8}" stroke="var(--line)" stroke-width="1"/><text x="${L-6}" y="${ys(v)+3}" text-anchor="end">${v}%</text>`);
 s+=`<path d="${path(PLAN,CW+1)}" fill="none" stroke="var(--ink3)" stroke-width="1.6" stroke-dasharray="4 3"/><path d="M${xs(CW)} ${ys(PLAN[CW])}${PLAN.slice(CW+1).map((v,i)=>"L"+xs(CW+1+i)+" "+ys(v)).join("")}" fill="none" stroke="var(--line2)" stroke-width="1.6" stroke-dasharray="4 3"/>`;
 s+=`<path d="${path(act,CW+1)}" fill="none" stroke="var(--hi)" stroke-width="2.4"/><circle cx="${xs(CW)}" cy="${ys(a)}" r="4" fill="var(--hi)"/>`;
 s+=`<path d="M${xs(CW)} ${T}V${Bt}" stroke="var(--ink)" stroke-width="1"/><text x="${xs(CW)+4}" y="${T+8}" style="fill:var(--ink)">Today</text>`;
 [0,3,6,9,12].forEach(w=>s+=`<text x="${xs(w)}" y="${Bt+14}" text-anchor="${w===12?"end":w===0?"start":"middle"}">Wk ${w}</text>`);
 s+="</svg>";
 const next=[{t:"Pier 7 pile cap inspection",d:1,ok:1},{t:"Pier 7 pile cap pour",d:2,ok:1},{t:"Pier 9 pile cap pour",d:4,ok:0,why:"Duct must be diverted or protected first"},{t:"Pier 6 stem starts",d:5,ok:1},{t:"Piers 1–3 bearings",d:8,ok:0,why:"Supplier dates not confirmed (EW-C4-013)"}];
 return `<div class="card"><div class="row between"><h2>Planned vs built</h2><span class="pill hi">${bd} days behind</span></div>
  <div class="legend" style="margin:4px 0 6px"><span><i style="background:var(--hi);height:3px"></i>Built ${Math.round(a)}%</span><span><i style="border-top:2px dashed var(--ink3);height:0"></i>Planned ${PLAN[CW]}%</span></div>${s}
  <p class="small muted">Built % comes from each pier's stages on the site map, updated by every approved diary.</p></div>
  <h3 style="margin:16px 0 8px">Next two weeks</h3>
  <div class="list">${next.map(n=>`<div class="li"><div style="min-width:0"><div class="t">${esc(n.t)}</div><div class="s">${esc(D.fDay(D.wdAhead(n.d)))}${n.why?" · "+esc(n.why):""}</div></div><span class="end pill ${n.ok?"":"hi"}">${n.ok?"On track":"At risk"}</span></div>`).join("")}</div>
  <h3 style="margin:16px 0 8px">By pier</h3>
  <div class="card" style="padding:6px 14px">${PIERS.map((p,i)=>`<button data-pier="${p.n}" style="display:block;width:100%;text-align:left;padding:8px 0;${i?"border-top:1px solid var(--line)":""}"><div class="row between small"><b style="font-weight:600">Pier ${p.n}</b><span class="${p.stopped?"":"muted"}" style="${p.stopped?"color:var(--hi-ink);font-weight:600":""}">${p.stopped?"Stopped":STAGES[Math.min(4,p.st.findIndex(v=>v<1))]||"Done"}</span></div><div class="steps5">${p.st.map(v=>`<i class="${v>=1?"on":v>0?"now":""}"></i>`).join("")}</div></button>`).join("")}</div>`;
}

/* delays */
function delaysHTML(){
 const dl=delays().filter(d=>d.wd<=20);const by={};dl.forEach(d=>{by[d.cause]=by[d.cause]||{h:0,c:0,n:0};by[d.cause].h+=d.h;by[d.cause].c+=d.cost;by[d.cause].n++});
 const rows=Object.entries(by).sort((a,b)=>b[1].c-a[1].c);const max=Math.max(...rows.map(r=>r[1].c),1);
 const claim=dl.filter(d=>d.ew);
 return `<div class="card"><span class="small muted">Lost in the last 4 weeks</span><div class="big" style="font-size:34px">${gbp(sum(dl,d=>d.cost))}</div>
   <p class="small muted">${r1(sum(dl,d=>d.h))} hours stood, from ${dl.length} delays. Labour at £${RATE}/h plus plant hire.</p>
   <h3 style="margin:14px 0 4px">By cause</h3>${rows.map(([k,v])=>`<div class="hbar"><span>${esc(k)}</span><div class="t"><i style="width:${v.c/max*100}%"></i></div><span class="v">${gbp(v.c)}</span></div>`).join("")}</div>
  <div class="finding" style="margin-top:14px"><i class="dot"></i><div><b>${gbp(sum(claim,d=>d.cost))} of it is linked to early warnings.</b> <span class="muted">Each one has the time, gang and photos recorded on the day, ready for the commercial team.</span></div></div>
  <h3 style="margin:16px 0 8px">Delay log</h3>
  <div class="list">${dl.map(d=>`<div class="li" style="align-items:flex-start"><div style="min-width:0"><div class="t">${esc(d.what)}</div><div class="s">${esc(D.fShort(D.wdAgo(d.wd)))} · ${esc(d.loc||"Site")} · ${d.ppl} ${d.ppl===1?"person":"people"}${d.plant?" + "+esc(d.plant):""}</div>${d.ew?`<div style="margin-top:4px"><span class="pill hi">${d.ew}</span></div>`:""}</div><div class="end"><div style="font-weight:600">${r1(d.h)} h</div><div class="small muted">${gbp(d.cost)}</div></div></div>`).join("")}</div>`;
}

/* warnings */
function ewHTML(){
 const w=warnings();const cnt=EW_STAGES.map((s,i)=>w.filter(x=>x.stage===i).length);
 return `<div class="pipe">${EW_STAGES.map((s,i)=>`<div><b>${cnt[i]}</b><span>${s}</span></div>`).join("")}</div>
  ${w.some(x=>x.overdue)?`<div class="finding" style="margin-top:12px"><i class="dot"></i><div><b>${w.filter(x=>x.overdue).length} warning${w.filter(x=>x.overdue).length>1?"s have":" has"} no meeting booked yet.</b> <span class="muted">Book one so the risk is talked through while there's still time to act.</span></div></div>`:""}
  <div class="list" style="margin-top:14px">${w.map(x=>`<div class="li" style="align-items:flex-start">${av(x.who)}<div style="min-width:0;flex:1"><div class="t">${esc(x.title)}</div><div class="s"><span class="mono">${x.ref}</span> · ${x.age?x.age+" working day"+(x.age>1?"s":"")+" old":"raised today"}</div><div class="steps5">${EW_STAGES.map((s,i)=>`<i class="${i<x.stage||x.stage===4?"on":i===x.stage?"now":""}"></i>`).join("")}</div><div class="s" style="margin-top:4px;${x.overdue?"color:var(--hi-ink);font-weight:600":""}">${esc(x.stage===4?"Closed":"Next: "+x.next)}</div></div></div>`).join("")}</div>`;
}

/* actions */
function actHTML(){
 const a=actions();const open=a.filter(x=>!x.done).sort((x,y)=>x.due-y.due), done=a.filter(x=>x.done);
 const row=x=>`<div class="li"><button class="chk ${x.done?"on":""}" data-act="${x.id}" aria-label="${x.done?"Mark not done":"Mark done"}">${x.done?'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><path d="m5 12 5 5 9-10"/></svg>':""}</button><div style="min-width:0;flex:1"><div class="t ${x.done?"done-t":""}">${esc(x.t)}</div><div class="s" style="${!x.done&&x.due<0?"color:var(--hi-ink);font-weight:600":""}">${esc(x.who)} · ${x.done?"done":x.due<0?"overdue "+(-x.due)+" day"+(x.due<-1?"s":""):"due "+esc(D.fShort(D.wdAhead(x.due)))}${x.fresh?" · from today's diary":""}</div></div>${av(x.who)}</div>`;
 return `<p class="small muted" style="margin-bottom:10px">Actions come out of each diary automatically, each with an owner and a date. Tap the box when it's done.</p>
  <div class="list">${open.map(row).join("")||'<div class="li muted">All done.</div>'}</div>
  ${done.length?`<h3 style="margin:16px 0 8px">Done</h3><div class="list">${done.map(row).join("")}</div>`:""}`;
}

/* labour & plant */
function resHTML(){
 const f=SN()&&SN().filed;const today=f?sum(f.diary.labour||[],l=>l.count):null;
 const hist=[14,15,15,13,16,15,14,12,15];
 const days=hist.map((v,i)=>({d:D.wdAgo(9-i),v})).concat([{d:D.TODAY,v:today}]);
 const max=Math.max(18,...days.map(d=>d.v||0));
 const shown=days.filter(d=>d.v!=null);const avg=sum(shown,d=>d.v)/shown.length;
 const plant=[{m:"90 t crawler crane",w:42.5,s:1.5},{m:"13 t excavator (hired)",w:34,s:3+(f?3.5:0)},{m:"13 t excavator (fleet)",w:41,s:0},{m:"6 t dumper",w:38,s:0}];
 return `<div class="card"><div class="row between"><h2>Operatives on site</h2><span class="small muted">avg ${r1(avg)} a day</span></div>
  <div class="chart" style="height:110px">${days.map((d,i)=>`<div class="c"><em>${d.v==null?"–":d.v}</em><i class="${i===days.length-1?"":"zero"}" style="height:${d.v?d.v/max*100:2}%;${i===days.length-1?"":"background:var(--ink3)"}"></i></div>`).join("")}</div>
  <div class="chart-x">${days.map((d,i)=>`<span>${i===days.length-1?"Today":d.d.toLocaleDateString("en-GB",{weekday:"narrow"})}</span>`).join("")}</div>
  ${today==null?'<p class="small muted" style="margin-top:8px">Today fills in when the diary is approved.</p>':""}</div>
  <div class="card" style="margin-top:14px"><h2>Plant, last 2 weeks</h2><p class="small muted">Working vs stood hours, from the diaries.</p>
  <table style="margin-top:8px"><thead><tr><th>Machine</th><th class="n">Working</th><th class="n">Stood</th></tr></thead><tbody>${plant.map(p=>`<tr><td>${esc(p.m)}</td><td class="n">${r1(p.w)} h</td><td class="n" style="${p.s?"color:var(--hi-ink);font-weight:600":"color:var(--ink3)"}">${p.s?r1(p.s)+" h":"0"}</td></tr>`).join("")}</tbody></table></div>`;
}

/* team (manager view) */
function teamHTML(){
 const f=SN()&&SN().filed;
 const team=[
  {n:"Sam Okafor",sec:"Viaduct C4",st:f?"Filed "+f.time:"Not yet",ok:!!f,lost:f?f.lost:null,ew:f?f.ews.length:0},
  {n:"Dan Mensah",sec:"Cutting C2",st:"Filed 16:58",ok:1,lost:0,ew:0},
  {n:"Kerry Walsh",sec:"Box culvert C3",st:"Filed 17:20",ok:1,lost:1,ew:1},
  {n:"Tom Price",sec:"Viaduct C5",st:"Shift ends 18:00",ok:0,lost:null,ew:0},
  {n:"Aisha Rahman",sec:"Haul roads",st:"Filed 15:45",ok:1,lost:0,ew:0},
  {n:"Lewis Grant",sec:"Utility diversions",st:"Filed 17:05",ok:1,lost:2.5,ew:1}
 ];
 const filed=team.filter(t=>t.ok).length;
 return `<div class="finding" style="margin-top:0"><i class="dot ${filed===team.length?"ok":""}"></i><div><b>${filed} of ${team.length} diaries in for today.</b> <span class="muted">What the project manager sees across the package.</span></div></div>
  <div class="list" style="margin-top:12px">${team.map(t=>`<div class="li">${av(t.n)}<div style="min-width:0;flex:1"><div class="t">${esc(t.n)}</div><div class="s">${esc(t.sec)} · ${esc(t.st)}</div></div><div class="end small">${t.lost?`<div style="color:var(--hi-ink);font-weight:600">${r1(t.lost)} h lost</div>`:t.lost===0?'<div class="muted">No delays</div>':'<div class="muted">–</div>'}${t.ew?`<div class="muted">${t.ew} warning</div>`:""}</div></div>`).join("")}</div>
  <p class="small muted" style="margin-top:10px">Names and sections are sample data.</p>`;
}
["Dan Mensah","Kerry Walsh","Tom Price","Aisha Rahman","Lewis Grant"].forEach((n,i)=>PEOPLE[n]={i:n.split(" ").map(x=>x[0]).join(""),c:["#D6E6F5","#DDEFD9","#EEDDF0","#F3EBC8","#D9E9E7"][i]});

window.SNTrack={render,warnings};
render();
if(window.SN&&SN.renderToday){SN.renderToday();SN.renderRecords()}
})();
