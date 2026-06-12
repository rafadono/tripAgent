// ROUTE
// ══════════════════════════════════════════════════════════════
function clearRoute(){
  if(APP.routeLine){ map.removeLayer(APP.routeLine); APP.routeLine=null; }
  if(APP.routeSegments&&APP.routeSegments.length){
    APP.routeSegments.forEach(function(l){ if(l&&map.hasLayer(l)) map.removeLayer(l); });
    APP.routeSegments=[];
  }
  APP.lastDayPlan=null;
  document.getElementById('drawer').classList.remove('open');
  const legEditor=document.getElementById('leg-editor');
  const tableWrap=document.getElementById('result-table-wrap');
  if(legEditor){ legEditor.classList.remove('on'); legEditor.innerHTML=''; }
  if(tableWrap){ tableWrap.classList.remove('on'); tableWrap.innerHTML=''; }
}

function drawSegmentedRoute(day){
  if(!day||!day.stops||!APP.start) return;
  if(APP.routeSegments&&APP.routeSegments.length){
    APP.routeSegments.forEach(function(l){ if(l&&map.hasLayer(l)) map.removeLayer(l); });
    APP.routeSegments=[];
  }
  const pts=[[APP.start.lat,APP.start.lng]];
  day.stops.forEach(function(s){ if(s.lat!=null&&s.lng!=null) pts.push([s.lat,s.lng]); });
  for(let i=0;i<day.stops.length;i++){
    if(!pts[i]||!pts[i+1]) continue;
    const m=APP.optimizedLegModes[i]||inferLegMode(day.stops[i]);
    const st=SEGMENT_STYLES[m]||SEGMENT_STYLES.driving;
    APP.routeSegments.push(L.polyline([pts[i],pts[i+1]],st).addTo(map));
  }
}

function renderLegEditor(day){
  const host=document.getElementById('leg-editor');
  if(!host||!day||!day.stops) return;
  APP.optimizedLegModes=day.stops.map(function(s,i){ return APP.optimizedLegModes[i]||inferLegMode(s); });
  const rows=day.stops.map(function(s,i){
    const cur=APP.optimizedLegModes[i];
    return '<div class="leg-seg-row">'+
      '<label>' + t('lbl_leg') + ' ' + (i+1)+' · '+esc(s.name||('Stop '+(i+1)))+'</label>'+
      '<select onchange="setOptimizedLegMode('+i+',this.value)">'+
      '<option value="driving"'+(cur==='driving'?' selected':'')+'>'+t('lbl_driving')+'</option>'+
      '<option value="walking"'+(cur==='walking'?' selected':'')+'>'+t('lbl_walking')+'</option>'+
      '<option value="transit_metro"'+(cur==='transit_metro'?' selected':'')+'>'+t('lbl_metro')+'</option>'+
      '<option value="transit_bus"'+(cur==='transit_bus'?' selected':'')+'>'+t('lbl_bus')+'</option>'+
      '<option value="cycling"'+(cur==='cycling'?' selected':'')+'>'+t('lbl_cycling')+'</option>'+
      '</select>'+
    '</div>';
  }).join('');
  host.innerHTML='<div class="leg-editor-head"><h4>'+t('post_opt_modes')+'</h4>'+
    '<div class="leg-legend">'+
      '<span class="leg-lg-item"><span class="leg-lg-line"></span>'+t('lbl_driving')+'</span>'+
      '<span class="leg-lg-item"><span class="leg-lg-line walk"></span>'+t('lbl_walking')+'</span>'+
      '<span class="leg-lg-item"><span class="leg-lg-line metro"></span>'+t('lbl_metro')+'</span>'+
      '<span class="leg-lg-item"><span class="leg-lg-line bus"></span>'+t('lbl_bus')+'</span>'+
    '</div></div>'+
    '<div class="leg-seg-list">'+rows+'</div>';
  host.classList.add('on');
}

function setOptimizedLegMode(index, mode){
  if(!APP.lastDayPlan||!APP.lastDayPlan.stops||!APP.lastDayPlan.stops[index]) return;
  APP.optimizedLegModes[index]=mode;
  const pid=APP.lastDayPlan.stops[index].place_id;
  APP.legModes[pid]=mode;
  drawSegmentedRoute(APP.lastDayPlan);
  renderResultTable(APP.lastDayPlan);
}

function renderResultTable(day){
  const host=document.getElementById('result-table-wrap');
  if(!host||!day) return;
  let html='<h4>'+t('lbl_opt_table')+'</h4><div class="result-table-scroll"><table class="result-table"><thead><tr>'+
    '<th>#</th><th>'+t('lbl_place')+'</th><th>'+t('lbl_arrival')+'</th><th>'+t('lbl_departure')+'</th><th>'+t('lbl_travel')+'</th><th>'+t('lbl_wait')+'</th><th>'+t('lbl_duration')+'</th><th>'+t('objective_label')+'</th></tr></thead><tbody>';
  day.stops.forEach(function(s,i){
    const mode=APP.optimizedLegModes[i]||inferLegMode(s);
    html+='<tr>'+
      '<td>'+(i+1)+'</td>'+
      '<td>'+esc(s.name||s.place_id)+'</td>'+
      '<td>'+fmtTime(s.arrival)+'</td>'+
      '<td>'+fmtTime(s.depart)+'</td>'+
      '<td>'+fmtDur(s.travel_min_from_prev||0)+'</td>'+
      '<td>'+fmtDur(s.wait_min||0)+'</td>'+
      '<td>'+fmtDur(s.visit_min||0)+'</td>'+
      '<td>'+routeModeLabel(mode)+'</td>'+
      '</tr>';
  });
  html+='</tbody></table></div>';
  host.innerHTML=html;
  host.classList.add('on');
}

async function runPlan(){
  if(APP.authRequired && !APP.authToken){ toast(t('login_required'),'er'); return; }
  if(!APP.start){ toast(t('msg_no_start'),'er'); return; }
  if(!APP.pois.length){ toast(t('msg_no_places'),'er'); return; }
  const btn=document.getElementById('btn');
  btn.disabled=true;
  btn.innerHTML='<div class="spin"></div><span>'+t('optimizing')+'</span>';
  try{
    const r=await fetch('/plan',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},authHeaders()),body:JSON.stringify(buildPlanPayload())});
    const data=await r.json();
    if(r.status===202){
      const q=(data&&data.detail)||{};
      const qid=q.queue_id?(' #'+q.queue_id):'';
      toast(t('request_queued')+qid,'ok');
      return;
    }
    if(!r.ok) throw new Error(data.detail||t('server_error'));
    APP.lastResult=data;
    showResult(data);
    toast(t('route_optimized_success'),'ok');
  }catch(e){ toast('Error: '+e.message,'er'); }
  finally{ btn.disabled=false; btn.innerHTML='<span>'+t('btn_optimize')+'</span>'; }
}

// ══════════════════════════════════════════════════════════════
// SHOW RESULT & TIMELINE
// ═══════════════════════════════════════════════════════════
function buildPlanPayload(){
  return {
    days:[{
      date:document.getElementById('sd').value,
      day_start_time:document.getElementById('st').value,
      day_end_time:document.getElementById('se').value,
      start_location:{place_id:APP.start.place_id},
      start_is_optimizable:false,
      pois:APP.pois.map(function(p){
        return {
          place_id:p.place_id,
          duration_min:p.is_waypoint?0:p.duration_min,
          arrival_mode:canonicalArrivalMode(APP.legModes[p.place_id])||null,
          is_waypoint:p.is_waypoint||false,
          waypoint_type:p.waypoint_type||null
        };
      })
    }],
    mode:document.getElementById('sm').value,
    objective:document.getElementById('so').value
  };
}

async function replanNow(){
  if(APP.authRequired && !APP.authToken){ toast(t('login_required'),'er'); return; }
  if(!APP.start || !APP.pois.length){ toast(t('msg_generate_base_first'),'er'); return; }
  const delayRaw=prompt(t('replan_prompt_delay'),'15');
  if(delayRaw===null) return;
  const delayMin=Math.max(0,parseInt(delayRaw,10)||0);
  try{
    const r=await fetch('/plan/replan',{
      method:'POST',
      headers:Object.assign({'Content-Type':'application/json'},authHeaders()),
      body:JSON.stringify({base_request:buildPlanPayload(),delay_min:delayMin,reason:'user_replan'})
    });
    const data=await r.json();
    if(!r.ok) throw new Error(data.detail||t('replan_failed'));
    APP.lastResult={mode:data.mode, objective:data.objective, days:data.days};
    showResult(APP.lastResult);
    toast(t('replan_success'),'ok');
  }catch(e){
    toast(t('replan_error')+e.message,'er');
  }
}

async function fetchAlternatives(){
  if(APP.authRequired && !APP.authToken){ toast(t('login_required'),'er'); return; }
  if(!APP.start || !APP.pois.length){ toast(t('msg_generate_base_first'),'er'); return; }
  try{
    const r=await fetch('/plan/alternatives',{
      method:'POST',
      headers:Object.assign({'Content-Type':'application/json'},authHeaders()),
      body:JSON.stringify(buildPlanPayload())
    });
    const data=await r.json();
    if(!r.ok) throw new Error(data.detail||t('alternative_ranking_failed'));
    renderAlternativesModal((data&&data.ranking)||[]);
  }catch(e){
    toast(t('alternative_ranking_error')+e.message,'er');
  }
}

function renderAlternativesModal(rows){
  const modal=document.getElementById('compare-modal');
  const host=document.getElementById('compare-list');
  if(!modal||!host) return;
  if(!rows.length){
    host.innerHTML='<p>'+t('no_alternatives')+'</p>';
    modal.classList.add('on');
    return;
  }
  let html='<table class="result-table"><thead><tr><th>#</th><th>'+t('objective_label')+'</th><th>'+t('lbl_score')+'</th><th>'+t('lbl_travel')+'</th><th>'+t('lbl_wait')+'</th><th>'+t('lbl_visit')+'</th><th>'+t('lbl_replan_reason')+'</th></tr></thead><tbody>';
  rows.forEach(function(r,i){
    html+='<tr><td>'+(i+1)+'</td><td>'+esc(r.objective)+'</td><td>'+esc(r.score)+'</td><td>'+fmtDur(r.total_travel_min||0)+'</td><td>'+fmtDur(r.total_wait_min||0)+'</td><td>'+fmtDur(r.total_visit_min||0)+'</td><td>'+esc(r.rationale||'')+'</td></tr>';
  });
  html+='</tbody></table>';
  host.innerHTML=html;
  modal.classList.add('on');
}

function showResult(data){
  const day=data.days[0], stops=day.stops;

  if(APP.routeLine){ map.removeLayer(APP.routeLine); APP.routeLine=null; }
  if(APP.routeSegments&&APP.routeSegments.length){
    APP.routeSegments.forEach(function(l){ if(l&&map.hasLayer(l)) map.removeLayer(l); });
    APP.routeSegments=[];
  }

  if(day.encoded_polyline){
    const pts=decodePolyline(day.encoded_polyline);
    if(pts.length) APP.routeLine=L.polyline(pts,{color:'#6b7280',weight:3,opacity:.35,lineJoin:'round',dashArray:'6 8'}).addTo(map);
  }

  APP.pois.forEach(function(p){ rmMarker(p.place_id); });
  const newOrder=stops.map(function(s){ return APP.pois.find(function(p){ return p.place_id===s.place_id; }); }).filter(Boolean);
  APP.pois=newOrder;
  stops.forEach(function(s,i){ const p=APP.pois.find(function(q){ return q.place_id===s.place_id; }); if(p) mkMarker(p,i+1,false); });
  renderList();
  APP.lastDayPlan=day;
  APP.optimizedLegModes=stops.map(function(s){ return inferLegMode(s); });
  drawSegmentedRoute(day);
  renderLegEditor(day);
  renderResultTable(day);

  const pts=[[APP.start.lat,APP.start.lng]];
  stops.forEach(function(s){ if(s.lat!=null&&s.lng!=null) pts.push([s.lat,s.lng]); });
  if(pts.length>1) map.fitBounds(L.latLngBounds(pts),{padding:[60,60]});

  // Calculate actual trip departure time
  const firstStop=stops[0];
  let tripStart=null;
  if(firstStop&&firstStop.arrival){
    const d=new Date(firstStop.arrival);
    d.setMinutes(d.getMinutes()-(firstStop.travel_min_from_prev||0));
    tripStart=d.toISOString();
  }
  const lastStop=stops[stops.length-1];
  const tripEnd=lastStop?lastStop.depart:null;
  const totalMin=day.total_travel_min+day.total_visit_min+day.total_wait_min;

  // ── Stats bar ──
  let statsHtml='';
  statsHtml+='<div class="ds">🕒 <b>'+fmtTime(tripStart)+'</b> → <b>'+fmtTime(tripEnd)+'</b></div>';
  statsHtml+='<span class="ds-sep">|</span>';
  statsHtml+='<div class="ds">🚗 <b>'+fmtDur(day.total_travel_min)+'</b> '+t('lbl_travel')+'</div>';
  statsHtml+='<div class="ds">⏳ <b>'+fmtDur(day.total_visit_min)+'</b> '+t('lbl_visit')+'</div>';
  if(day.total_wait_min) statsHtml+='<div class="ds">⏳ <b>'+fmtDur(day.total_wait_min)+'</b> '+t('lbl_wait')+'</div>';
  statsHtml+='<span class="ds-sep">|</span>';
  statsHtml+='<div class="ds">'+t('lbl_total_time')+': <b>'+fmtDur(totalMin)+'</b></div>';
  document.getElementById('dstats').innerHTML=statsHtml;

  // ── Day progress bar ──
  if(totalMin>0){
    const travelPct=Math.round(day.total_travel_min/totalMin*100);
    const visitPct=Math.round(day.total_visit_min/totalMin*100);
    const waitPct=100-travelPct-visitPct;
    let dpHtml='<div class="dp-label"><span>'+fmtTime(tripStart)+'</span><span>'+fmtTime(tripEnd)+'</span></div>';
    dpHtml+='<div class="dp-track">';
    dpHtml+='<div class="dp-seg dp-travel" style="left:0;width:'+travelPct+'%"></div>';
    dpHtml+='<div class="dp-seg dp-visit" style="left:'+travelPct+'%;width:'+visitPct+'%"></div>';
    if(waitPct>0) dpHtml+='<div class="dp-seg dp-wait" style="left:'+(travelPct+visitPct)+'%;width:'+waitPct+'%"></div>';
    dpHtml+='</div>';
    dpHtml+='<div class="dp-legend"><div class="dp-leg-item"><div class="dp-leg-dot" style="background:#4da3ff"></div>'+t('lbl_travel')+' '+travelPct+'%</div><div class="dp-leg-item"><div class="dp-leg-dot" style="background:#00d4a0"></div>'+t('lbl_visit')+' '+visitPct+'%</div>'+(waitPct>0?'<div class="dp-leg-item"><div class="dp-leg-dot" style="background:#ffc542"></div>'+t('lbl_wait')+' '+waitPct+'%</div>':'')+'</div>';
    document.getElementById('day-progress').innerHTML=dpHtml;
  }

  // ── Timeline ──
  let tlHtml='<div class="tl-summary"><h4>'+t('lbl_day_summary')+'</h4><div class="sum-grid">';
  tlHtml+='<div class="sum-item"><span class="sum-label">'+t('lbl_departure_from_start')+'</span><span class="sum-val">'+fmtTime(tripStart)+'</span></div>';
  tlHtml+='<div class="sum-item"><span class="sum-label">'+t('lbl_end_route')+'</span><span class="sum-val">'+fmtTime(tripEnd)+'</span></div>';
  tlHtml+='<div class="sum-item"><span class="sum-label">'+t('lbl_total_time')+'</span><span class="sum-val big">'+fmtDur(totalMin)+'</span></div>';
  tlHtml+='<div class="sum-item"><span class="sum-label">'+t('lbl_visited_places')+'</span><span class="sum-val">'+stops.length+'</span></div>';
  tlHtml+='<div class="sum-item"><span class="sum-label">'+t('lbl_travel')+'</span><span class="sum-val">'+fmtDur(day.total_travel_min)+'</span></div>';
  tlHtml+='<div class="sum-item"><span class="sum-label">'+t('lbl_visit')+'</span><span class="sum-val">'+fmtDur(day.total_visit_min)+'</span></div>';
  if(day.total_wait_min) tlHtml+='<div class="sum-item"><span class="sum-label">'+t('lbl_wait')+'</span><span class="sum-val">'+fmtDur(day.total_wait_min)+'</span></div>';
  tlHtml+='</div></div>';

  // Start point
  tlHtml+='<div class="tl-stop">'+
    '<div class="tl-stop-dot"><div class="tl-dot s">S</div></div>'+
    '<div class="tl-stop-body">'+
      '<div class="tl-name">'+esc(APP.start.name||t('start_label'))+'</div>'+
      '<div class="tl-times"><span class="tl-arr">'+t('lbl_departure')+' '+fmtTime(tripStart)+'</span></div>'+
    '</div>'+
  '</div>';

  let cumulMin=0;
  stops.forEach(function(s,i){
    const travel=s.travel_min_from_prev||0;
    const visit=s.visit_min||0;
    const wait=s.wait_min||0;
    const stopTotal=travel+wait+visit;
    cumulMin+=stopTotal;

    const barTotal=Math.max(stopTotal,1);
    const tPct=Math.round(travel/barTotal*100), wPct=Math.round(wait/barTotal*100), vPct=100-tPct-wPct;

    // Travel time connector with mode icon
    if(travel>0){
      const modeKey=APP.optimizedLegModes[i]||inferLegMode(s);
      const modeIcon={'driving':'🚗','walking':'🚶','transit':'🚌','transit_metro':'🚇','transit_bus':'🚌','cycling':'🚲'}[modeKey||'driving'];
      tlHtml+='<div class="tl-connector"><div class="tl-conn-line"></div><div class="tl-conn-label">'+modeIcon+' '+fmtDur(travel)+'</div></div>';
    }

    const isWpStop=s.is_waypoint;
    const wpIcon=s.waypoint_type==='metro'?'🚇':'🅿️';
    tlHtml+='<div class="tl-stop">'+
      '<div class="tl-stop-dot"><div class="tl-dot'+(isWpStop?' wp':' p')+'">'+(isWpStop?wpIcon:(i+1))+'</div></div>'+
      '<div class="tl-stop-body">'+
        '<div class="tl-name">'+esc(s.name)+(isWpStop?'<span class="tl-waypoint-badge">'+(s.waypoint_type==='metro'?'Metro':'Parking')+'</span>':'')+'</div>'+
        '<div class="tl-times">'+
          '<span class="tl-arr">'+fmtTime(s.arrival)+'</span>'+
          ' → <span class="tl-dep">'+fmtTime(s.depart)+'</span>'+
          ' &nbsp;<span class="tl-dur-eff">'+fmtDur(visit)+' '+t('lbl_effective')+'</span>'+
        '</div>'+
        '<div class="tl-bars">'+
          (travel>0?'<div class="tl-bar travel" style="flex:'+travel+'"></div>':'')+
          (wait>0?'<div class="tl-bar wait" style="flex:'+wait+'"></div>':'')+
          '<div class="tl-bar visit" style="flex:'+visit+'"></div>'+
        '</div>'+
        '<div class="tl-tags">'+
          (travel>0?'<span class="tl-tag travel">'+({'driving':'🚗','walking':'🚶','transit':'🚌','transit_metro':'🚇','transit_bus':'🚌','cycling':'🚲'}[(APP.optimizedLegModes[i]||inferLegMode(s))||'driving'])+' '+fmtDur(travel)+'</span>':'')+
          '<span class="tl-tag visit">🕒 '+fmtDur(visit)+' '+t('lbl_visit')+'</span>'+
          (wait>0?'<span class="tl-tag wait">⏳ '+fmtDur(wait)+' '+t('lbl_wait')+'</span>':'')+
          '<span class="tl-tag cumul">+'+fmtDur(cumulMin)+' '+t('lbl_cumul_from_start')+'</span>'+
        '</div>'+
      '</div>'+
    '</div>';
  });

  document.getElementById('tl').innerHTML=tlHtml;
  document.getElementById('drawer').classList.add('open');
}

function closeDrawer(){ document.getElementById('drawer').classList.remove('open'); }

// ══════════════════════════════════════════════════════════════
// POLYLINE DECODER
// ══════════════════════════════════════════════════════════════
function decodePolyline(encoded){
  const points=[]; let index=0, lat=0, lng=0;
  while(index<encoded.length){
    let b, shift=0, result=0;
    do{ b=encoded.charCodeAt(index++)-63; result|=(b&0x1f)<<shift; shift+=5; }while(b>=0x20);
    lat+=(result&1)?~(result>>1):(result>>1);
    shift=0; result=0;
    do{ b=encoded.charCodeAt(index++)-63; result|=(b&0x1f)<<shift; shift+=5; }while(b>=0x20);
    lng+=(result&1)?~(result>>1):(result>>1);
    points.push([lat/1e5,lng/1e5]);
  }
  return points;
}

// ══════════════════════════════════════════════════════════════
// SET PLACE AS START (desde parking/metro)
// ══════════════════════════════════════════════════════════════
function setPlaceAsStart(placeId, name, lat, lng, address){
  const p={place_id:placeId, name:name, address:address||'', lat:lat, lng:lng};
  if(APP.start) rmMarker(APP.start.place_id);
  APP.start=p;
  mkMarker(p,'S',true);
  renderList(); flyTo(p);
  toast(t('toast_start_marker')+name,'ok');
}

function addWaypoint(opt, type, anchorPlaceId){
  if(APP.pois.some(function(x){ return x.place_id===opt.place_id; })){
    toast(t('toast_marker_already_in_list'),'er'); return;
  }
  const wp={
    place_id: opt.place_id,
    name: opt.name,
    address: opt.address||'',
    lat: opt.lat,
    lng: opt.lng,
    duration_min: 0,
    is_waypoint: true,
    waypoint_type: type,
    parkingEnabled: false,
    parkingData: null,
    parkingChoice: null,
    cost_clp_hr: opt.cost_clp_hr||0,
    cost_clp_trip: opt.cost_clp_trip||0,
    cost_clp_trip_low: opt.cost_clp_trip_low||0,
    cost_clp_trip_high: opt.cost_clp_trip_high||0,
    walk_min: opt.walk_min||0,
    distance_m: opt.distance_m||0,
  };
  const anchorIdx=APP.pois.findIndex(function(p){ return p.place_id===anchorPlaceId; });
  if(anchorIdx>=0) APP.pois.splice(anchorIdx,0,wp);
  else APP.pois.push(wp);
  mkMarker(wp, type==='metro'?'M':'P', false);
  APP.legModes[wp.place_id]= type==='metro'?'transit_metro':'driving';
  if(anchorPlaceId) APP.legModes[anchorPlaceId]='walking';
  renderList(); flyTo(wp);
  toast(t('toast_stop_added')+opt.name,'ok');
  updateCost();
}

// ══════════════════════════════════════════════════════════════
// CONTEXT MENU
// ══════════════════════════════════════════════════════════════
const ctxMenu=document.createElement('div');
ctxMenu.id='ctx-menu';
document.body.appendChild(ctxMenu);

let ctxTarget=null;

function showCtxMenu(e,poiId){
  e.preventDefault();
  e.stopPropagation();
  ctxTarget=poiId;
  const poi=APP.pois.find(function(p){ return p.place_id===poiId; });
  if(!poi) return;
  ctxMenu.innerHTML=
    '<div class="ctx-item" onclick="ctxEdit()">'+t('ctx_edit')+'</div>'+
    '<div class="ctx-item" onclick="ctxSetStart()">'+t('ctx_set_start')+'</div>'+
    '<div class="ctx-sep"></div>'+
    '<div class="ctx-item" onclick="ctxParking()">'+t('ctx_parking')+'</div>'+
    '<div class="ctx-sep"></div>'+
    '<div class="ctx-item danger" onclick="ctxRemove()">'+t('ctx_remove')+'</div>';
  const x=Math.min(e.clientX, window.innerWidth-200);
  const y=Math.min(e.clientY, window.innerHeight-160);
  ctxMenu.style.left=x+'px';
  ctxMenu.style.top=y+'px';
  ctxMenu.classList.add('on');
}

function hideCtxMenu(){ ctxMenu.classList.remove('on'); ctxTarget=null; }

function ctxEdit(){ hideCtxMenu(); if(ctxTarget) startEdit(ctxTarget); }

function ctxSetStart(){
  hideCtxMenu();
  const poi=APP.pois.find(function(p){ return p.place_id===ctxTarget; });
  if(!poi) return;
  if(APP.start) rmMarker(APP.start.place_id);
  const old=ctxTarget;
  APP.start={place_id:poi.place_id,name:poi.name,address:poi.address||'',lat:poi.lat,lng:poi.lng};
  rmPoi(old);
  mkMarker(APP.start,'S',true);
  renderList();
  toast(t('toast_start_marker')+APP.start.name,'ok');
}

function ctxParking(){
  hideCtxMenu();
  if(!ctxTarget) return;
  const poi=APP.pois.find(function(p){ return p.place_id===ctxTarget; });
  if(!poi) return;
  poi.parkingEnabled=true;
  renderList();
  fetchParking(ctxTarget);
}

function ctxRemove(){ hideCtxMenu(); if(ctxTarget) rmPoi(ctxTarget); }

document.addEventListener('click',function(e){
  if(!ctxMenu.contains(e.target)) hideCtxMenu();
  if(!document.getElementById('search-area').contains(e.target)) ddEl.classList.remove('open');
});
document.addEventListener('keydown',function(e){ if(e.key==='Escape') hideCtxMenu(); });

// ══════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════
document.getElementById('sd').valueAsDate=new Date();

async function applyBackendAvailability(){
  try{
    const resp=await fetch('/ui-check');
    if(!resp.ok) return;
    const data=await resp.json();
    const btn=document.getElementById('btn');
    if(!btn) return;
    APP.authRequired=!!(data&&data.auth_enabled);
    if(APP.authRequired && !APP.authToken){
      btn.disabled=true;
      btn.innerHTML='<span>'+t('login_required')+'</span>';
      return;
    }
    if(data && data.plan_enabled===false){
      btn.disabled=true;
      btn.innerHTML='<span>'+t('opt_unavailable')+'</span>';
      if(data.fallback_message){ toast(data.fallback_message,'er'); }
    }else{
      btn.disabled=false;
      btn.innerHTML='<span>'+t('btn_optimize')+'</span>';
    }
  }catch(e){
    // no-op: keep UI operable for static fallback
  }
}

applyBackendAvailability();
