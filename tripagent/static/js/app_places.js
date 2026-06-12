// SEARCH & AUTOCOMPLETE
// ══════════════════════════════════════════════════════════════
const qEl=document.getElementById('q');
const ddEl=document.getElementById('dd');
let debounceTimer=null, ddData=[], ddHighlight=-1;

qEl.addEventListener('input',function(){
  const val=qEl.value.trim();
  clearTimeout(debounceTimer);
  if(val.length<2){ ddEl.classList.remove('open'); return; }
  if(APP.searchCache[val]){ ddData=APP.searchCache[val]; renderDd(); return; }
  ddEl.innerHTML='<div class="dd-hint"><div class="spin"></div>'+t('searching')+'</div>';
  ddEl.classList.add('open');
  debounceTimer=setTimeout(function(){ fetchSearch(val); },200);
});

qEl.addEventListener('keydown',function(e){
  const rows=ddEl.querySelectorAll('.dd-row');
  if(!rows.length) return;
  if(e.key==='ArrowDown'){ e.preventDefault(); ddHighlight=Math.min(rows.length-1,ddHighlight+1); updateHighlight(rows); }
  else if(e.key==='ArrowUp'){ e.preventDefault(); ddHighlight=Math.max(0,ddHighlight-1); updateHighlight(rows); }
  else if(e.key==='Enter'){ e.preventDefault(); if(ddHighlight>=0&&rows[ddHighlight]) rows[ddHighlight].click(); }
  else if(e.key==='Escape'){ ddEl.classList.remove('open'); }
});

function updateHighlight(rows){
  rows.forEach(function(r,i){ r.classList.toggle('hi',i===ddHighlight); });
  if(rows[ddHighlight]) rows[ddHighlight].scrollIntoView({block:'nearest'});
}

async function fetchSearch(query){
  try{
    const full=/chile|santiago/i.test(query)?query:query+', Santiago, Chile';
    const r=await fetch('/search_places',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:full,max_results:6})});
    const d=await r.json();
    ddData=d.results||[];
    APP.searchCache[query]=ddData;
    renderDd();
  }catch(e){ ddEl.innerHTML='<div class="dd-hint">'+t('conn_error')+'</div>'; }
}

function renderDd(){
  if(!ddData.length){ ddEl.innerHTML='<div class="dd-hint">'+t('no_results')+'</div>'; ddEl.classList.add('open'); return; }
  ddEl.innerHTML=ddData.map(function(p,i){
    return '<div class="dd-row" data-i="'+i+'"><div class="dd-icon">📍</div><div class="dd-texts"><div class="dd-name">'+esc(p.name||'')+'</div><div class="dd-addr">'+esc(p.address||'')+'</div></div></div>';
  }).join('');
  ddEl.querySelectorAll('.dd-row').forEach(function(el){
    el.addEventListener('click',function(){ pickPlace(parseInt(el.dataset.i)); });
  });
  ddEl.classList.add('open');
  ddHighlight=-1;
}

function pickPlace(i){
  const p=ddData[i];
  ddEl.classList.remove('open');
  qEl.value='';
  if(APP.mode==='start'||!APP.start){ setStart(p); if(APP.mode==='start') setMode('poi'); }
  else { addPoi(p); }
}

function setStart(p){
  if(APP.start) rmMarker(APP.start.place_id);
  APP.start=Object.assign({},p);
  mkMarker(p,'S',true);
  renderList(); flyTo(p);
  toast('📍 ' + t('lbl_start') + ': ' + p.name,'ok');
}

function addPoi(p){
  if(APP.pois.find(function(x){ return x.place_id===p.place_id; })){ toast(t('toast_marker_already_in_list'),'er'); return; }
  p.duration_min=60; p.parkingEnabled=false; p.parkingData=null; p.parkingChoice=null;
  APP.pois.push(Object.assign({},p));
  mkMarker(p,APP.pois.length,false);
  renderList(); flyTo(p); updateCost();
}

function setMode(m){
  APP.mode=m;
  document.querySelectorAll('.chip').forEach(function(b){ b.classList.toggle('on',b.dataset.m===m); });
}

// ══════════════════════════════════════════════════════════════
// MARKERS
// ══════════════════════════════════════════════════════════════
function mkMarker(p,label,isStart){
  if(p.lat==null||p.lng==null) return;
  if(APP.markers[p.place_id]){ map.removeLayer(APP.markers[p.place_id]); delete APP.markers[p.place_id]; }
  const bg=isStart?'#4da3ff':'#00d4a0', fg=isStart?'#fff':'#0c1420';
  const icon=L.divIcon({
    className:'',
    html:'<div class="ta-marker" style="background:'+bg+';color:'+fg+'">'+label+'</div>',
    iconSize:[28,28], iconAnchor:[14,14], popupAnchor:[0,-14]
  });
  const m=L.marker([p.lat,p.lng],{icon:icon,title:p.name||''}).addTo(map);
  APP.markers[p.place_id]=m;
}

function rmMarker(id){ if(APP.markers[id]){ map.removeLayer(APP.markers[id]); delete APP.markers[id]; } }

function refreshPOIMarkers(){ APP.pois.forEach(function(p,i){ rmMarker(p.place_id); mkMarker(p,i+1,false); }); }

function flyTo(p){ if(p.lat&&p.lng) map.flyTo([p.lat,p.lng],15,{duration:1.1}); }

// ══════════════════════════════════════════════════════════════
// RENDER LIST
// ══════════════════════════════════════════════════════════════
function renderList(){
  const any=APP.start||APP.pois.length;
  document.getElementById('empty').style.display=any?'none':'block';
  document.getElementById('list').style.display=any?'block':'none';
  const sl=document.getElementById('sl'), sr=document.getElementById('sr');
  const pl=document.getElementById('pl'), pr=document.getElementById('pr');

  if(APP.start){
    sl.style.display='flex';
    sr.innerHTML='<div class="place start" id="place-start">'+
      '<div class="p-num s">S</div>'+
      '<div class="p-info"><div class="p-name">'+esc(APP.start.name)+'</div><div class="p-addr">'+esc(APP.start.address||'')+'</div></div>'+
      '<button class="p-btn edit" id="start-edit-btn" title="' + t('ctx_edit') + '">✏️</button>'+
    '</div>'+
    '<div class="start-edit-panel" id="start-edit-panel"></div>';
    document.getElementById('start-edit-btn').addEventListener('click',function(){ startEditStart(); });
  } else { sl.style.display='none'; sr.innerHTML=''; }

  if(APP.pois.length){
    pl.style.display='flex';
    document.getElementById('poi-count').textContent=APP.pois.length;

    const modeOpts=[
      {v:'driving', label:'🚗 ' + t('lbl_driving')},
      {v:'walking', label:'🚶 ' + t('lbl_walking')},
      {v:'transit_metro', label:'🚇 ' + t('lbl_metro')},
      {v:'transit_bus', label:'🚌 ' + t('lbl_bus')},
      {v:'cycling', label:'🚲 ' + t('lbl_cycling')},
    ];
    let html='';
    APP.pois.forEach(function(p,i){
      const canUp=i>0, canDown=i<APP.pois.length-1;
      const isWp=p.is_waypoint;
      const curMode=APP.legModes[p.place_id]||document.getElementById('sm').value;
      const typeIcon=p.waypoint_type==='metro'?'🚇':'🅿️';
      const typeName=p.waypoint_type==='metro'?'Metro':'Parking';
      html+='<div class="leg-mode-row">'+
        '<span class="leg-mode-label">' + t('from_label') + ':</span>'+
        '<div class="leg-mode-chips">'+
        modeOpts.map(function(m){
          return '<button class="leg-chip'+(curMode===m.v?' on':'')+
            '" onclick="setLegMode(\'' +p.place_id+ '\',\'' +m.v+ '\')">' +m.label+ '</button>';
        }).join('')+
        '</div></div>';
      if(isWp){
        html+='<div class="place waypoint" id="place-'+p.place_id+'" draggable="true">'+
          '<span class="drag-handle">⠿</span>'+
          '<div class="p-num wp">'+typeIcon+'</div>'+
          '<div class="p-info"><div class="p-name">'+esc(p.name)+'</div><div class="wp-badge">'+typeName+' · ' + t('lbl_technical_stop') + '</div></div>'+
          '<div class="p-arrows">'+
            '<button class="arr" data-id="'+p.place_id+'" data-dir="-1"'+(canUp?'':' disabled')+'>▲</button>'+
            '<button class="arr" data-id="'+p.place_id+'" data-dir="1"'+(canDown?'':' disabled')+'>▼</button>'+
          '</div>'+
          '<button class="p-btn del" data-id="'+p.place_id+'" title="' + t('ctx_remove') + '">✕</button>'+
        '</div>';
      } else {
        html+='<div class="place" id="place-'+p.place_id+'" draggable="true">'+
          '<span class="drag-handle">⠿</span>'+
          '<div class="p-num p">'+(i+1)+'</div>'+
          '<div class="p-info"><div class="p-name">'+esc(p.name)+'</div><div class="p-addr">'+esc(p.address||'')+'</div></div>'+
          '<div class="p-arrows">'+
            '<button class="arr" data-id="'+p.place_id+'" data-dir="-1"'+(canUp?'':' disabled')+'>▲</button>'+
            '<button class="arr" data-id="'+p.place_id+'" data-dir="1"'+(canDown?'':' disabled')+'>▼</button>'+
          '</div>'+
          '<div class="p-dur"><input class="dur" type="number" min="5" max="480" value="'+p.duration_min+'" data-id="'+p.place_id+'"/><span class="dur-u">min</span></div>'+
          '<button class="p-btn park'+(p.parkingEnabled?' on':'')+'" data-id="'+p.place_id+'" title="' + t('ctx_parking') + '">🅿️</button>'+
          '<button class="p-btn edit" data-id="'+p.place_id+'" title="' + t('ctx_edit') + '">✏️</button>'+
          '<button class="p-btn del" data-id="'+p.place_id+'" title="' + t('ctx_remove') + '">✕</button>'+
        '</div>'+
        '<div class="edit-panel" id="edit-'+p.place_id+'"></div>'+
        '<div class="park-panel'+(p.parkingEnabled?' open':'')+'" id="park-'+p.place_id+'">'+renderParkPanel(p)+'</div>';
      }
    });
    pr.innerHTML=html;

    pr.querySelectorAll('.arr').forEach(function(el){ el.addEventListener('click',function(){ movePoi(el.dataset.id,parseInt(el.dataset.dir)); }); });
    pr.querySelectorAll('.dur').forEach(function(el){ el.addEventListener('input',function(){ const poi=APP.pois.find(function(p){ return p.place_id===el.dataset.id; }); if(poi) poi.duration_min=Math.max(5,parseInt(el.value)||60); }); });
    pr.querySelectorAll('.p-btn.park').forEach(function(el){ el.addEventListener('click',function(){ toggleParking(el.dataset.id); }); });
    pr.querySelectorAll('.p-btn.edit').forEach(function(el){ el.addEventListener('click',function(){ startEdit(el.dataset.id); }); });
    pr.querySelectorAll('.p-btn.del').forEach(function(el){ el.addEventListener('click',function(){ rmPoi(el.dataset.id); }); });

    pr.querySelectorAll('.place').forEach(function(el){
      const pid=el.id.replace('place-','');
      el.addEventListener('contextmenu',function(e){ showCtxMenu(e,pid); });
      el.addEventListener('dragstart',function(e){ APP.dragSrc=el.id.replace('place-',''); el.classList.add('dragging'); e.dataTransfer.effectAllowed='move'; });
      el.addEventListener('dragend',function(){ el.classList.remove('dragging'); pr.querySelectorAll('.place').forEach(function(p){ p.classList.remove('drag-over'); }); });
      el.addEventListener('dragover',function(e){ e.preventDefault(); if(APP.dragSrc&&el.id!=='place-'+APP.dragSrc){ pr.querySelectorAll('.place').forEach(function(p){ p.classList.remove('drag-over'); }); el.classList.add('drag-over'); } });
      el.addEventListener('drop',function(e){
        e.preventDefault();
        const targetId=el.id.replace('place-','');
        if(!APP.dragSrc||targetId===APP.dragSrc) return;
        const from=APP.pois.findIndex(function(p){ return p.place_id===APP.dragSrc; });
        const to=APP.pois.findIndex(function(p){ return p.place_id===targetId; });
        if(from===-1||to===-1) return;
        const item=APP.pois.splice(from,1)[0];
        APP.pois.splice(to,0,item);
        refreshPOIMarkers(); renderList(); clearRoute();
      });
    });
  } else { pl.style.display='none'; pr.innerHTML=''; }
}

function movePoi(id,dir){
  const i=APP.pois.findIndex(function(p){ return p.place_id===id; });
  if(i===-1) return;
  const ni=i+dir;
  if(ni<0||ni>=APP.pois.length) return;
  const tmp=APP.pois[i]; APP.pois[i]=APP.pois[ni]; APP.pois[ni]=tmp;
  refreshPOIMarkers(); renderList(); clearRoute();
}

function setLegMode(placeId, mode){
  APP.legModes[placeId]=mode;
  renderList();
}

function rmStart(){ if(APP.start) rmMarker(APP.start.place_id); APP.start=null; renderList(); }
function rmPoi(id){ rmMarker(id); delete APP.legModes[id]; APP.pois=APP.pois.filter(function(p){ return p.place_id!==id; }); refreshPOIMarkers(); renderList(); clearRoute(); updateCost(); }
function rmAllPois(){ APP.pois.forEach(function(p){ rmMarker(p.place_id); delete APP.legModes[p.place_id]; }); APP.pois=[]; renderList(); clearRoute(); updateCost(); }

// ══════════════════════════════════════════════════════════════
// EDIT START
// ══════════════════════════════════════════════════════════════
function startEditStart(){
  const panel=document.getElementById('start-edit-panel');
  if(!panel) return;
  const isOpen=panel.classList.contains('open');
  if(isOpen){ panel.classList.remove('open'); panel.innerHTML=''; return; }
  panel.classList.add('open');
  panel.innerHTML='<input class="edit-input" id="start-edit-input" placeholder="' + t('search_placeholder') + '" autocomplete="off"/><div class="edit-dd" id="start-edit-dd"></div>';
  const inp=document.getElementById('start-edit-input');
  inp.focus();
  let startEditTimer=null, startEditResults=[];
  inp.addEventListener('input',function(){
    const val=inp.value.trim();
    clearTimeout(startEditTimer);
    if(val.length<2){ document.getElementById('start-edit-dd').classList.remove('open'); return; }
    document.getElementById('start-edit-dd').innerHTML='<div class="dd-hint"><div class="spin"></div>'+t('searching')+'</div>';
    document.getElementById('start-edit-dd').classList.add('open');
    startEditTimer=setTimeout(async function(){
      try{
        const full=/chile|santiago/i.test(val)?val:val+', Santiago, Chile';
        const r=await fetch('/search_places',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:full,max_results:5})});
        const d=await r.json();
        startEditResults=d.results||[];
        const dd=document.getElementById('start-edit-dd');
        if(!startEditResults.length){ dd.innerHTML='<div class="dd-hint">'+t('no_results')+'</div>'; return; }
        dd.innerHTML=startEditResults.map(function(p,i){ return '<div class="dd-row" data-i="'+i+'"><div class="dd-icon">📍</div><div class="dd-texts"><div class="dd-name">'+esc(p.name)+'</div><div class="dd-addr">'+esc(p.address||'')+'</div></div></div>'; }).join('');
        dd.querySelectorAll('.dd-row').forEach(function(el){
          el.addEventListener('click',function(){
            const np=startEditResults[parseInt(el.dataset.i)];
            if(APP.start) rmMarker(APP.start.place_id);
            APP.start=Object.assign({},np);
            mkMarker(APP.start,'S',true);
            panel.classList.remove('open'); panel.innerHTML='';
            renderList(); flyTo(APP.start);
            toast(t('start_updated')+np.name,'ok');
          });
        });
      }catch(e){ document.getElementById('start-edit-dd').innerHTML='<div class="dd-hint">'+t('search_error')+'</div>'; }
    },200);
  });
  inp.addEventListener('keydown',function(e){ if(e.key==='Escape'){ panel.classList.remove('open'); panel.innerHTML=''; } });
}

// ══════════════════════════════════════════════════════════════
// EDIT INLINE
// ══════════════════════════════════════════════════════════════
const editState={};
function startEdit(id){
  const panel=document.getElementById('edit-'+id);
  if(!panel) return;
  const isOpen=panel.classList.contains('open');
  document.querySelectorAll('.edit-panel').forEach(function(p){ p.classList.remove('open'); p.innerHTML=''; });
  if(isOpen) return;
  panel.classList.add('open');
  panel.innerHTML='<input class="edit-input" id="edit-input-'+id+'" placeholder="' + t('search_placeholder') + '" autocomplete="off"/><div class="edit-dd" id="edit-dd-'+id+'"></div>';
  const inp=document.getElementById('edit-input-'+id);
  inp.focus();
  editState[id]={timer:null,results:[],highlight:-1};
  inp.addEventListener('input',function(){
    const val=inp.value.trim();
    clearTimeout(editState[id].timer);
    if(val.length<2){ document.getElementById('edit-dd-'+id).classList.remove('open'); return; }
    document.getElementById('edit-dd-'+id).innerHTML='<div class="dd-hint"><div class="spin"></div>'+t('searching')+'</div>';
    document.getElementById('edit-dd-'+id).classList.add('open');
    editState[id].timer=setTimeout(function(){ fetchEditSearch(id,val); },200);
  });
  inp.addEventListener('keydown',function(e){ if(e.key==='Escape'){ panel.classList.remove('open'); panel.innerHTML=''; delete editState[id]; } });
}

async function fetchEditSearch(id,query){
  try{
    const full=/chile|santiago/i.test(query)?query:query+', Santiago, Chile';
    const r=await fetch('/search_places',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:full,max_results:5})});
    const d=await r.json();
    editState[id].results=d.results||[];
    renderEditDd(id);
  }catch(e){ document.getElementById('edit-dd-'+id).innerHTML='<div class="dd-hint">'+t('search_error')+'</div>'; }
}

function renderEditDd(id){
  const dd=document.getElementById('edit-dd-'+id);
  if(!dd) return;
  const results=editState[id].results;
  if(!results.length){ dd.innerHTML='<div class="dd-hint">'+t('no_results')+'</div>'; dd.classList.add('open'); return; }
  dd.innerHTML=results.map(function(p,i){ return '<div class="dd-row" data-i="'+i+'"><div class="dd-icon">📍</div><div class="dd-texts"><div class="dd-name">'+esc(p.name)+'</div><div class="dd-addr">'+esc(p.address||'')+'</div></div></div>'; }).join('');
  dd.querySelectorAll('.dd-row').forEach(function(el){ el.addEventListener('click',function(){ replacePlace(id,parseInt(el.dataset.i)); }); });
  dd.classList.add('open');
}

function replacePlace(oldId,newIdx){
  const newPlace=editState[oldId].results[newIdx];
  const i=APP.pois.findIndex(function(p){ return p.place_id===oldId; });
  if(i===-1) return;
  const oldDur=APP.pois[i].duration_min;
  rmMarker(oldId);
  APP.pois[i]=Object.assign({},newPlace,{duration_min:oldDur,parkingEnabled:false,parkingData:null,parkingChoice:null});
  mkMarker(APP.pois[i],i+1,false);
  renderList(); flyTo(APP.pois[i]);
  toast(t('place_updated')+newPlace.name,'ok');
  delete editState[oldId];
}

// ══════════════════════════════════════════════════════════════
// PARKING
// ══════════════════════════════════════════════════════════════
async function toggleParking(id){
  const poi=APP.pois.find(function(p){ return p.place_id===id; });
  if(!poi) return;
  poi.parkingEnabled=!poi.parkingEnabled;
  if(!poi.parkingEnabled){ poi.parkingData=null; poi.parkingChoice=null; }
  renderList(); updateCost();
  if(poi.parkingEnabled&&!poi.parkingData) await fetchParking(id);
}

async function fetchParking(id){
  const poi=APP.pois.find(function(p){ return p.place_id===id; });
  if(!poi||poi.lat==null||poi.lng==null) return;
  const panel=document.getElementById('park-'+id);
  if(panel) panel.innerHTML='<div class="park-loading"><div class="spin"></div>'+t('searching_options')+'</div>';
  try{
    const r=await fetch('/nearest_parking',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:poi.lat,lng:poi.lng,radius_m:600})});
    poi.parkingData=await r.json();
  }catch(e){ poi.parkingData={parking:[],metro:[]}; toast(t('parking_error'),'er'); }
  renderList();
}

function renderParkPanel(p){
  if(!p.parkingEnabled) return '';
  if(!p.parkingData) return '<div class="park-loading"><div class="spin"></div>'+t('park_loading')+'</div>';
  const d=p.parkingData;
  let html='<h5>' + t('parking_title') + '</h5>';

  function renderParkOpt(opt, icon, type){
    const sel=p.parkingChoice&&p.parkingChoice.place_id===opt.place_id;
    const isWp=APP.pois.some(function(x){ return x.place_id===opt.place_id&&x.is_waypoint; });
    const optJson=JSON.stringify({place_id:opt.place_id,name:opt.name,address:opt.address||'',lat:opt.lat,lng:opt.lng,cost_clp_hr:opt.cost_clp_hr,cost_clp_trip:opt.cost_clp_trip,cost_clp_trip_low:opt.cost_clp_trip_low,cost_clp_trip_high:opt.cost_clp_trip_high,walk_min:opt.walk_min,distance_m:opt.distance_m}).replace(/"/g,'&quot;');
    return '<div class="park-opt'+(sel?' sel':'')+'" onclick="selectParking(\''+p.place_id+'\',\''+opt.place_id+'\')">'+
      '<div class="park-opt-icon">'+icon+'</div>'+
      '<div class="park-opt-info">'+
        '<div class="park-opt-name">'+esc(opt.name)+'</div>'+
        '<div class="park-opt-meta"><span>📍 '+opt.distance_m+'m</span><span>🚶 '+opt.walk_min+'min</span><span>💰 '+parkingPriceLabel(opt)+'</span></div>'+
        '<div style="display:flex;gap:5px;margin-top:4px">'+
          '<button class="park-set-start" onclick="event.stopPropagation();setPlaceAsStart(\''+opt.place_id+'\',\''+esc(opt.name)+'\','+opt.lat+','+opt.lng+',\''+esc(opt.address||'')+'\')">'+t('parking_use_start')+'</button>'+
          '<button class="park-add-wp'+(isWp?' added':'')+'" onclick="event.stopPropagation();addWaypoint('+optJson+',\''+type+'\',\''+p.place_id+'\')">'+
            (isWp?t('parking_added_wp'):t('parking_add_wp'))+
          '</button>'+
        '</div>'+
      '</div>'+
    '</div>';
  }

  (d.parking||[]).forEach(function(opt){ html+=renderParkOpt(opt,'🅿️','parking'); });
  if(d.metro&&d.metro.length){
    html+='<h5 style="margin-top:10px">' + t('metro_title') + '</h5>';
    (d.metro||[]).forEach(function(opt){ html+=renderParkOpt(opt,'🚇','metro'); });
  }
  return html;
}

function selectParking(poiId,parkId){
  const poi=APP.pois.find(function(p){ return p.place_id===poiId; });
  if(!poi||!poi.parkingData) return;
  const all=(poi.parkingData.parking||[]).concat(poi.parkingData.metro||[]);
  const opt=all.find(function(o){ return o.place_id===parkId; });
  if(!opt) return;
  poi.parkingChoice=(poi.parkingChoice&&poi.parkingChoice.place_id===parkId)?null:opt;
  renderList(); updateCost();
}

// ══════════════════════════════════════════════════════════════
// COST CALCULATOR
// ══════════════════════════════════════════════════════════════
function updateCost(){
  let total=0;
  const mode=document.getElementById('sm').value;
  if(mode==='transit'){
    const segments=Math.max(1,APP.pois.length);
    total=segments*BUS_FARE_CLP;
  }
  else if(mode==='driving') APP.pois.forEach(function(p){ if(p.parkingChoice){ if(p.parkingChoice.cost_clp_hr!=null) total+=p.parkingChoice.cost_clp_hr; else if(p.parkingChoice.cost_clp_trip!=null) total+=p.parkingChoice.cost_clp_trip; }});
  const badge=document.getElementById('cost-badge'), val=document.getElementById('cost-val');
  if(total>0){
    badge.classList.add('on');
    if(mode==='transit'){
      val.textContent=fmtCurrency(total)+' ('+t('micro_fare')+' '+fmtCurrency(BUS_FARE_CLP)+' / '+t('metro_fare')+' '+fmtCurrency(METRO_FARE_CLP.low)+'-'+fmtCurrency(METRO_FARE_CLP.peak)+')';
    } else {
      val.textContent=fmtCurrency(total);
    }
  }
  else badge.classList.remove('on');
}

// ══════════════════════════════════════════════════════════════
// MAP LAYERS (Overpass API)
// ══════════════════════════════════════════════════════════════
const OVERPASS_QUERIES={
  food:     function(b){ return 'node["amenity"~"restaurant|cafe|fast_food"]["name"]('+b+');'; },
  parking:  function(b){ return 'node["amenity"="parking"]('+b+');way["amenity"="parking"]('+b+');'; },
  metro:    function(b){ return 'node["station"="subway"]('+b+');node["railway"="station"]["subway"="yes"]('+b+');'; },
  bus:      function(b){ return 'node["highway"="bus_stop"]('+b+');'; },
  cycling:  function(b){ return 'way["highway"="cycleway"]('+b+');way["cycleway"~"lane|track"]('+b+');'; },
  pharmacy: function(b){ return 'node["amenity"="pharmacy"]('+b+');'; },
  atm:      function(b){ return 'node["amenity"="atm"]('+b+');node["amenity"="bank"]('+b+');'; },
  toilet:   function(b){ return 'node["amenity"="toilets"]('+b+');'; },
  viewpoint:function(b){ return 'node["tourism"="viewpoint"]('+b+');node["tourism"="attraction"]('+b+');'; },
};

function toggleLayer(key){
  const layer=APP.layers[key];
  if(!layer) return;
  layer.active=!layer.active;
  const btn=document.querySelector('.map-btn[data-layer="'+key+'"]');
  if(btn) btn.classList.toggle('on',layer.active);
  if(layer.active){ layer.group.addTo(map); loadLayer(key); }
  else map.removeLayer(layer.group);
}

async function loadLayer(key){
  const layer=APP.layers[key];
  const bounds=map.getBounds();
  const bbox=bounds.getSouth()+','+bounds.getWest()+','+bounds.getNorth()+','+bounds.getEast();
  const query='[out:json][timeout:25];('+OVERPASS_QUERIES[key](bbox)+');out center 100;>;out skel qt;';
  try{
    const r=await fetch('https://overpass-api.de/api/interpreter',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'data='+encodeURIComponent(query)});
    const data=await r.json();
    layer.group.clearLayers();
    const nodeIndex={};
    (data.elements||[]).forEach(function(el){ if(el.type==='node') nodeIndex[el.id]=el; });
    (data.elements||[]).forEach(function(el){
      if(el.type==='way'&&el.nodes){
        const pts=el.nodes.map(function(nid){ const n=nodeIndex[nid]; return n?[n.lat,n.lon]:null; }).filter(Boolean);
        if(pts.length>1) L.polyline(pts,{color:layer.color,weight:3,opacity:.7}).bindPopup(esc((el.tags&&el.tags.name)||'Ciclovía')).addTo(layer.group);
      } else {
        const lat=el.lat||(el.center&&el.center.lat), lng=el.lon||(el.center&&el.center.lon);
        if(!lat||!lng) return;
        const icon=L.divIcon({className:'',html:'<div class="ta-layer-dot" style="background:'+layer.color+'"></div>',iconSize:[20,20],iconAnchor:[10,10]});
        L.marker([lat,lng],{icon:icon}).bindPopup(esc((el.tags&&el.tags.name)||key)).addTo(layer.group);
      }
    });
    toast(layer.group.getLayers().length+' '+t('found'),'ok');
  }catch(e){ toast(t('error_loading_layer'),'er'); }
}

let layerMoveTimer=null;
map.on('moveend',function(){
  clearTimeout(layerMoveTimer);
  layerMoveTimer=setTimeout(function(){ Object.keys(APP.layers).forEach(function(key){ if(APP.layers[key].active) loadLayer(key); }); },800);
});
