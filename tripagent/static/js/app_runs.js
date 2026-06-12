// SAVE / LOAD ROUTES
// ══════════════════════════════════════════════════════════════
function saveRoute(){
  if(!APP.lastResult){ toast(t('msg_generate_base_first'),'er'); return; }
  const name=prompt(t('lbl_route_name'));
  if(!name) return;
  const saved=JSON.parse(localStorage.getItem('tripagent_routes')||'[]');
  if(saved.length>=5){ toast(t('msg_max_routes_limit'),'er'); return; }
  saved.push({name:name,date:new Date().toISOString(),start:APP.start,pois:APP.pois,legModes:APP.legModes,settings:{mode:document.getElementById('sm').value,objective:document.getElementById('so').value,date:document.getElementById('sd').value,startTime:document.getElementById('st').value,endTime:document.getElementById('se').value}});
  localStorage.setItem('tripagent_routes',JSON.stringify(saved));
  toast(t('route_saved'),'ok');
}

function openSavedRoutes(){
  const saved=JSON.parse(localStorage.getItem('tripagent_routes')||'[]');
  const list=document.getElementById('saved-list');
  if(!saved.length){ list.innerHTML='<p style="text-align:center;padding:20px;color:var(--muted)">'+t('no_saved_routes')+'</p>'; }
  else {
    list.innerHTML=saved.map(function(r,i){
      const d=new Date(r.date);
      return '<div class="saved-route" onclick="loadRoute('+i+')"><div class="saved-route-info"><div class="saved-route-name">'+esc(r.name)+'</div><div class="saved-route-meta">'+r.pois.length+' ' + t('lbl_stops') + ' · '+d.toLocaleDateString('es-CL')+'</div></div><button class="saved-route-del" onclick="event.stopPropagation();deleteRoute('+i+')">🗑️</button></div>';
    }).join('');
  }
  document.getElementById('saved-modal').classList.add('on');
}

function loadRoute(i){
  const saved=JSON.parse(localStorage.getItem('tripagent_routes')||'[]');
  const r=saved[i]; if(!r) return;
  if(APP.start) rmMarker(APP.start.place_id);
  APP.pois.forEach(function(p){ rmMarker(p.place_id); });
  APP.start=r.start; APP.pois=r.pois; APP.legModes=r.legModes||{};
  mkMarker(APP.start,'S',true);
  APP.pois.forEach(function(p,idx){ mkMarker(p,idx+1,false); });
  document.getElementById('sm').value=r.settings.mode;
  document.getElementById('so').value=r.settings.objective;
  document.getElementById('sd').value=r.settings.date;
  document.getElementById('st').value=r.settings.startTime;
  document.getElementById('se').value=r.settings.endTime;
  renderList(); closeModal(); toast(t('msg_route_loaded'),'ok');
  const pts=[[APP.start.lat,APP.start.lng]];
  APP.pois.forEach(function(p){ pts.push([p.lat,p.lng]); });
  if(pts.length>1) map.fitBounds(L.latLngBounds(pts),{padding:[50,50]});
}

function deleteRoute(i){
  if(!confirm(t('msg_confirm_delete_route'))) return;
  const saved=JSON.parse(localStorage.getItem('tripagent_routes')||'[]');
  saved.splice(i,1); localStorage.setItem('tripagent_routes',JSON.stringify(saved));
  openSavedRoutes(); toast(t('msg_route_deleted'),'ok');
}

function closeModal(){ document.getElementById('saved-modal').classList.remove('on'); }

function saveOptimizationRun(){
  if(!APP.lastResult||!APP.lastDayPlan){ toast(t('msg_generate_base_first'),'er'); return; }
  const runs=JSON.parse(localStorage.getItem('tripagent_runs')||'[]');
  const day=APP.lastDayPlan;
  runs.unshift({
    id: Date.now(),
    created_at: new Date().toISOString(),
    mode: APP.lastResult.mode,
    objective: APP.lastResult.objective,
    date: day.date,
    totals: {travel:day.total_travel_min, wait:day.total_wait_min, visit:day.total_visit_min},
    stops: day.stops.map(function(s,idx){
      return {
        place_id:s.place_id, name:s.name, arrival:s.arrival, depart:s.depart,
        travel_min_from_prev:s.travel_min_from_prev, wait_min:s.wait_min, visit_min:s.visit_min,
        leg_mode:APP.optimizedLegModes[idx]||inferLegMode(s), is_waypoint:!!s.is_waypoint, waypoint_type:s.waypoint_type||null
      };
    })
  });
  localStorage.setItem('tripagent_runs',JSON.stringify(runs.slice(0,12)));
  toast(t('run_saved'),'ok');
}

function openCompareRuns(){
  const runs=JSON.parse(localStorage.getItem('tripagent_runs')||'[]');
  const list=document.getElementById('compare-list');
  if(!runs.length){
    list.innerHTML='<p style="text-align:center;padding:20px;color:var(--muted)">'+t('no_saved_runs')+'</p>';
  } else {
    list.innerHTML=runs.map(function(r,i){
      const total=(r.totals.travel||0)+(r.totals.wait||0)+(r.totals.visit||0);
      return '<div class="saved-route" style="cursor:default">'+
        '<div class="saved-route-info"><div class="saved-route-name">'+esc(r.mode)+' · '+esc(r.objective)+' · '+esc(r.date)+'</div>'+
        '<div class="saved-route-meta">'+r.stops.length+' ' + t('lbl_stops') + ' · ' + t('lbl_total_time') + ' ' + fmtDur(total)+' · ' + t('lbl_travel') + ' ' + fmtDur(r.totals.travel||0)+'</div></div>'+
        '<button class="saved-route-del" onclick="applyRun('+i+')">'+t('lbl_apply')+'</button>'+
        '<button class="saved-route-del" onclick="mixRun('+i+')">'+t('lbl_mix')+'</button>'+
        '<button class="saved-route-del" onclick="deleteRun('+i+')">🗑️</button>'+
      '</div>';
    }).join('');
  }
  document.getElementById('compare-modal').classList.add('on');
}

function closeCompareModal(){ document.getElementById('compare-modal').classList.remove('on'); }

function applyRun(i){
  const runs=JSON.parse(localStorage.getItem('tripagent_runs')||'[]');
  const run=runs[i]; if(!run) return;
  const byId={}; APP.pois.forEach(function(p){ byId[p.place_id]=p; });
  const used={}; const ordered=[];
  run.stops.forEach(function(s){
    if(byId[s.place_id]&&!used[s.place_id]){
      ordered.push(byId[s.place_id]);
      used[s.place_id]=true;
      APP.legModes[s.place_id]=s.leg_mode;
    }
  });
  APP.pois.forEach(function(p){ if(!used[p.place_id]) ordered.push(p); });
  APP.pois=ordered;
  renderList(); closeCompareModal(); toast(t('msg_run_applied'),'ok');
}

function mixRun(i){
  const runs=JSON.parse(localStorage.getItem('tripagent_runs')||'[]');
  const run=runs[i]; if(!run) return;
  const ids=APP.pois.map(function(p){ return p.place_id; });
  run.stops.forEach(function(s,idx){
    if(idx===0) return;
    const prev=run.stops[idx-1].place_id, cur=s.place_id;
    const pIdx=ids.indexOf(prev), cIdx=ids.indexOf(cur);
    if(pIdx===-1||cIdx===-1||cIdx===pIdx+1) return;
    ids.splice(cIdx,1);
    ids.splice(pIdx+1,0,cur);
    APP.legModes[cur]=s.leg_mode;
  });
  const byId={}; APP.pois.forEach(function(p){ byId[p.place_id]=p; });
  APP.pois=ids.map(function(id){ return byId[id]; }).filter(Boolean);
  renderList(); closeCompareModal(); toast(t('msg_run_mixed'),'ok');
}

function deleteRun(i){
  const runs=JSON.parse(localStorage.getItem('tripagent_runs')||'[]');
  runs.splice(i,1);
  localStorage.setItem('tripagent_runs',JSON.stringify(runs));
  openCompareRuns();
}

// EXPORT
// ══════════════════════════════════════════════════════════════
function exportToClipboard(){
  if(!APP.lastResult) return;
  const day=APP.lastResult.days[0], stops=day.stops;
  let text=t('lbl_itinerary') + ' - '+document.getElementById('sd').value+'\n\n';
  text+=t('start_label') + ': '+(APP.start?APP.start.name:'-')+'\n';
  text+=t('transport_label') + ': '+document.getElementById('sm').value+'\n';
  text+=t('lbl_total_time') + ': '+fmtDur(day.total_travel_min+day.total_visit_min+day.total_wait_min)+'\n\n';
  stops.forEach(function(s,i){
    text+=(i+1)+'. '+s.name+'\n';
    text+='   '+fmtTime(s.arrival)+' - '+fmtTime(s.depart)+' ('+fmtDur(s.visit_min)+' ' + t('lbl_visit') + ')\n';
    if(s.travel_min_from_prev) text+='   ' + t('lbl_travel_from_prev') + fmtDur(s.travel_min_from_prev)+'\n';
    if(s.wait_min) text+='   ' + t('lbl_wait') + ': '+fmtDur(s.wait_min)+'\n';
    text+='\n';
  });
  navigator.clipboard.writeText(text).then(function(){ toast(t('copied_clipboard'),'ok'); }).catch(function(){ toast(t('msg_copy_failed'),'er'); });
}

// THEME
// ══════════════════════════════════════════════════════════════
function toggleTheme(){
  const current=document.body.dataset.theme||'dark';
  const next=current==='dark'?'light':'dark';
  document.body.dataset.theme=next;
  localStorage.setItem('tripagent_theme',next);
  document.getElementById('theme-btn').textContent=next==='dark'?'🌙':'☀️';
}
const savedTheme=localStorage.getItem('tripagent_theme');
if(savedTheme){ document.body.dataset.theme=savedTheme; document.getElementById('theme-btn').textContent=savedTheme==='dark'?'🌙':'☀️'; }
