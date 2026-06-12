// ══════════════════════════════════════════════════════════════
// STATE & TRANSLATIONS
// ══════════════════════════════════════════════════════════════
const APP = {
  start: null,
  pois: [],       // includes both normal POIs and waypoints (is_waypoint:true)
  legModes: {},   // { place_id: "driving"|"walking"|"transit"|"cycling" }  → mode to reach this stop
  markers: {},
  mode: 'poi',
  routeLine: null,
  routeSegments: [],
  optimizedLegModes: [],
  lastDayPlan: null,
  lastResult: null,
  authRequired: false,
  authToken: sessionStorage.getItem('tripagent_auth_token') || '',
  username: sessionStorage.getItem('tripagent_auth_user') || '',
  dragSrc: null,
  searchCache: {},
  layers: {
    food:     {active:false, group:null, color:'#ff7043'},
    parking:  {active:false, group:null, color:'#5c6bc0'},
    metro:    {active:false, group:null, color:'#e53935'},
    bus:      {active:false, group:null, color:'#43a047'},
    cycling:  {active:false, group:null, color:'#00bcd4'},
    pharmacy: {active:false, group:null, color:'#ab47bc'},
    atm:      {active:false, group:null, color:'#ffa726'},
    toilet:   {active:false, group:null, color:'#26c6da'},
    viewpoint:{active:false, group:null, color:'#8bc34a'},
  }
};

const TRANSLATIONS = {
  es: {
    // index.html static UI
    title: "TripAgent - Optimizador de Rutas",
    saved_routes_btn: "Rutas guardadas",
    change_theme_btn: "Cambiar tema",
    close_panel_btn: "Cerrar panel",
    auth_user_placeholder: "Usuario",
    auth_pass_placeholder: "Clave",
    auth_login_btn: "Login",
    auth_state_no_session: "Sin sesión",
    auth_state_session: "Sesión: ",
    search_placeholder: "Escribe una dirección o lugar…",
    chip_poi: "+ Lugar",
    chip_start: "📍 Inicio",
    empty_message: "Escribe una dirección arriba<br>para comenzar tu itinerario.",
    start_label: "Inicio",
    rm_start_btn: "Quitar",
    places_label: "Lugares",
    clear_places_btn: "Limpiar",
    est_cost_label: "💰 Costo estimado:",
    date_label: "Fecha",
    transport_label: "Transporte",
    opt_driving: "🚗 Auto",
    opt_walking: "🚶 Caminar",
    opt_transit: "🚌 Transporte público",
    opt_cycling: "🚲 Bicicleta",
    from_label: "Desde",
    to_label: "Hasta",
    objective_label: "Objetivo",
    opt_time: "⚡ Tiempo mínimo",
    opt_money: "💰 Costo mínimo",
    opt_comfort: "😌 Comodidad",
    btn_optimize: "Optimizar ruta →",
    layer_food: "🍽️ Comida",
    layer_parking: "🅿️ Estacionamiento",
    layer_metro: "🚇 Metro",
    layer_bus: "🚌 Paraderos",
    layer_cycling_lanes: "🚲 Ciclovías",
    layer_pharmacy: "💊 Farmacias",
    layer_atm: "🏧 ATMs",
    layer_toilet: "🚻 Baños",
    layer_viewpoint: "🔭 Miradores",
    drawer_title: "Itinerario optimizado",
    btn_copy: "Copiar",
    btn_save_route: "Guardar ruta",
    btn_save_run: "Guardar corrida",
    btn_compare: "Comparar",
    btn_alternatives: "Ranking alternativas",
    btn_replan: "Replanificar ahora",
    modal_saved_title: "💾 Rutas Guardadas",
    modal_compare_title: "Comparar corridas",

    // Dynamic Javascript Labels & Messages
    msg_fill_auth: "Completa usuario y clave",
    msg_login_failed: "Error login: ",
    msg_session_started: "Sesión iniciada",
    searching: "Buscando...",
    conn_error: "Error al conectar",
    no_results: "Sin resultados",
    searching_options: "Buscando opciones...",
    post_opt_modes: "Modos por tramo (post-optimización)",
    optimizing: "Optimizando...",
    no_alternatives: "Sin alternativas disponibles.",
    login_required: "Login requerido",
    opt_unavailable: "Optimización no disponible",
    copied_clipboard: "Copiado al portapapeles",
    route_saved: "Ruta guardada",
    run_saved: "Corrida de optimización guardada",
    no_saved_routes: "No hay rutas guardadas",
    no_saved_runs: "No hay corridas guardadas",
    request_queued: "Solicitud en cola",
    server_error: "Error en el servidor",
    start_updated: "Inicio actualizado: ",
    stop_added_suggested: "Parada agregada en posición sugerida: ",
    already_in_list: "Ya está en la lista",
    replan_success: "Ruta replanificada en tiempo real",
    replan_failed: "No se pudo replanificar",
    replan_error: "Error replanificando: ",
    alternative_ranking_failed: "No se pudo obtener ranking",
    alternative_ranking_error: "Error en ranking: ",
    found: "encontrados",
    error_loading_layer: "Error cargando capa",
    park_loading: "Buscando...",
    toast_start_marker: "Inicio → ",
    toast_marker_already_in_list: "Ya está en la lista",
    toast_stop_added: "Parada agregada en posicion sugerida: ",
    search_error: "Error",
    place_updated: "Actualizado: ",
    parking_error: "Error buscando estacionamientos",
    parking_title: "Estacionar y caminar",
    metro_title: "Metro cercano",
    parking_use_start: "📍 Usar como inicio",
    parking_added_wp: "✓ Agregado como parada",
    parking_add_wp: "+ Agregar como parada",
    micro_fare: "micro",
    metro_fare: "metro",

    msg_no_start: "Agrega un punto de inicio",
    msg_no_places: "Agrega al menos un lugar de interés",
    route_optimized_success: "Ruta optimizada",
    msg_generate_base_first: "Primero genera una ruta base",
    replan_prompt_delay: "Retraso en minutos para replanificar (ej: 15):",

    lbl_driving: "Auto",
    lbl_walking: "Caminar",
    lbl_metro: "Metro",
    lbl_bus: "Micro",
    lbl_cycling: "Bici",
    lbl_transit: "Transporte público",
    lbl_start: "Inicio",
    lbl_end: "Fin",
    lbl_travel: "traslado",
    lbl_wait: "espera",
    lbl_visit: "en lugares",
    lbl_duration: "Estadía",
    lbl_window: "Ventana",
    lbl_replan_reason: "Motivo replanificación",
    lbl_applied_delay: "Retraso aplicado",
    lbl_removed_places: "Lugares removidos",
    lbl_score: "Puntaje",
    lbl_action: "Acción",
    lbl_copy_desc: "Descripción copiada",
    lbl_compare_runs: "Comparar corridas",
    lbl_metrics: "Métricas",
    lbl_cashflow: "Flujo de caja",
    lbl_reconcile: "Reconciliar",
    lbl_technical_stop: "parada técnica",
    lbl_opt_table: "Tabla de resultados",
    lbl_arrival: "Llegada",
    lbl_departure: "Salida",
    lbl_day_summary: "Resumen del día",
    lbl_visited_places: "Lugares visitados",
    lbl_cumul_from_start: "desde salida",
    lbl_total_time: "Tiempo total",
    lbl_departure_from_start: "Salida desde inicio",
    lbl_end_route: "Fin del recorrido",
    lbl_effective: "efectivos",
    lbl_place: "Lugar",
    lbl_leg: "Tramo",

    lbl_route_name: "Nombre de la ruta:",
    msg_max_routes_limit: "Máximo 5 rutas guardadas",
    msg_route_loaded: "Ruta cargada",
    msg_confirm_delete_route: "¿Eliminar esta ruta?",
    msg_route_deleted: "Ruta eliminada",
    lbl_apply: "Aplicar",
    lbl_mix: "Mezclar",
    msg_run_applied: "Corrida aplicada",
    msg_run_mixed: "Corrida mezclada con la actual",
    lbl_itinerary: "ITINERARIO",
    lbl_travel_from_prev: "Traslado desde anterior: ",
    msg_copy_failed: "Error al copiar",
    lbl_stops: "paradas",

    // Context Menu
    ctx_edit: "✏️ Editar lugar",
    ctx_set_start: "📍 Usar como inicio",
    ctx_parking: "🅿️ Buscar estacionamiento",
    ctx_remove: "✕ Eliminar"
  },
  en: {
    // index.html static UI
    title: "TripAgent - Route Optimizer",
    saved_routes_btn: "Saved Routes",
    change_theme_btn: "Toggle Theme",
    close_panel_btn: "Close panel",
    auth_user_placeholder: "Username",
    auth_pass_placeholder: "Password",
    auth_login_btn: "Login",
    auth_state_no_session: "No session",
    auth_state_session: "Session: ",
    search_placeholder: "Type an address or place...",
    chip_poi: "+ Place",
    chip_start: "📍 Start",
    empty_message: "Type an address above<br>to start your itinerary.",
    start_label: "Start",
    rm_start_btn: "Remove",
    places_label: "Places",
    clear_places_btn: "Clear",
    est_cost_label: "💰 Estimated Cost:",
    date_label: "Date",
    transport_label: "Transport",
    opt_driving: "🚗 Driving",
    opt_walking: "🚶 Walking",
    opt_transit: "🚌 Public Transit",
    opt_cycling: "🚲 Cycling",
    from_label: "From",
    to_label: "To",
    objective_label: "Objective",
    opt_time: "⚡ Min Time",
    opt_money: "💰 Min Cost",
    opt_comfort: "😌 Comfort",
    btn_optimize: "Optimize Route →",
    layer_food: "🍽️ Food",
    layer_parking: "🅿️ Parking",
    layer_metro: "🚇 Metro",
    layer_bus: "🚌 Bus Stops",
    layer_cycling_lanes: "🚲 Cycling Lanes",
    layer_pharmacy: "💊 Pharmacies",
    layer_atm: "🏧 ATMs",
    layer_toilet: "🚻 Toilets",
    layer_viewpoint: "🔭 Viewpoints",
    drawer_title: "Optimized Itinerary",
    btn_copy: "Copy",
    btn_save_route: "Save Route",
    btn_save_run: "Save Run",
    btn_compare: "Compare",
    btn_alternatives: "Alternatives Ranking",
    btn_replan: "Replan Now",
    modal_saved_title: "💾 Saved Routes",
    modal_compare_title: "Compare Runs",

    // Dynamic Javascript Labels & Messages
    msg_fill_auth: "Please enter username and password",
    msg_login_failed: "Login error: ",
    msg_session_started: "Logged in",
    searching: "Searching...",
    conn_error: "Connection error",
    no_results: "No results",
    searching_options: "Searching options...",
    post_opt_modes: "Leg modes (post-optimization)",
    optimizing: "Optimizing...",
    no_alternatives: "No alternatives available.",
    login_required: "Login required",
    opt_unavailable: "Optimization unavailable",
    copied_clipboard: "Copied to clipboard",
    route_saved: "Route saved",
    run_saved: "Optimization run saved",
    no_saved_routes: "No saved routes",
    no_saved_runs: "No saved runs",
    request_queued: "Request queued",
    server_error: "Server error",
    start_updated: "Start updated: ",
    stop_added_suggested: "Stop added in suggested position: ",
    already_in_list: "Already in list",
    replan_success: "Route replanned in real-time",
    replan_failed: "Could not replan",
    replan_error: "Error replanning: ",
    alternative_ranking_failed: "Could not fetch alternatives",
    alternative_ranking_error: "Error in ranking: ",
    found: "found",
    error_loading_layer: "Error loading layer",
    park_loading: "Searching...",
    toast_start_marker: "Start → ",
    toast_marker_already_in_list: "Already in list",
    toast_stop_added: "Stop added in suggested position: ",
    search_error: "Error",
    place_updated: "Updated: ",
    parking_error: "Error searching parking spaces",
    parking_title: "Park and walk",
    metro_title: "Nearby metro",
    parking_use_start: "📍 Use as start",
    parking_added_wp: "✓ Added as stop",
    parking_add_wp: "+ Add as stop",
    micro_fare: "bus",
    metro_fare: "metro",

    msg_no_start: "Please add a start point",
    msg_no_places: "Please add at least one place of interest",
    route_optimized_success: "Route optimized",
    msg_generate_base_first: "Please generate a base route first",
    replan_prompt_delay: "Delay in minutes to replan (e.g. 15):",

    lbl_driving: "Driving",
    lbl_walking: "Walking",
    lbl_metro: "Metro",
    lbl_bus: "Bus",
    lbl_cycling: "Cycling",
    lbl_transit: "Public Transit",
    lbl_start: "Start",
    lbl_end: "End",
    lbl_travel: "travel",
    lbl_wait: "wait",
    lbl_visit: "at places",
    lbl_duration: "Stay",
    lbl_window: "Window",
    lbl_replan_reason: "Replan reason",
    lbl_applied_delay: "Applied delay",
    lbl_removed_places: "Removed places",
    lbl_score: "Score",
    lbl_action: "Action",
    lbl_copy_desc: "Description copied",
    lbl_compare_runs: "Compare runs",
    lbl_metrics: "Metrics",
    lbl_cashflow: "Cash Flow",
    lbl_reconcile: "Reconcile",
    lbl_technical_stop: "technical stop",
    lbl_opt_table: "Result table",
    lbl_arrival: "Arrival",
    lbl_departure: "Departure",
    lbl_day_summary: "Day summary",
    lbl_visited_places: "Visited places",
    lbl_cumul_from_start: "from start",
    lbl_total_time: "Total time",
    lbl_departure_from_start: "Departure from start",
    lbl_end_route: "End of route",
    lbl_effective: "effective",
    lbl_place: "Place",
    lbl_leg: "Leg",

    lbl_route_name: "Route name:",
    msg_max_routes_limit: "Maximum of 5 saved routes reached",
    msg_route_loaded: "Route loaded",
    msg_confirm_delete_route: "Delete this route?",
    msg_route_deleted: "Route deleted",
    lbl_apply: "Apply",
    lbl_mix: "Mix",
    msg_run_applied: "Run applied",
    msg_run_mixed: "Run mixed with the current one",
    lbl_itinerary: "ITINERARY",
    lbl_travel_from_prev: "Travel from previous: ",
    msg_copy_failed: "Copy failed",
    lbl_stops: "stops",

    // Context Menu
    ctx_edit: "✏️ Edit place",
    ctx_set_start: "📍 Use as start",
    ctx_parking: "🅿️ Search parking",
    ctx_remove: "✕ Remove"
  }
};

let currentLanguage = localStorage.getItem('tripagent_lang') || 'es';

function t(key) {
  return (TRANSLATIONS[currentLanguage] && TRANSLATIONS[currentLanguage][key]) || key;
}

function applyTranslations() {
  // Translate static text elements using data-i18n
  document.querySelectorAll('[data-i18n]').forEach(function(el) {
    const key = el.getAttribute('data-i18n');
    el.innerHTML = t(key);
  });

  // Translate placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el) {
    const key = el.getAttribute('data-i18n-placeholder');
    el.setAttribute('placeholder', t(key));
  });

  // Translate titles
  document.querySelectorAll('[data-i18n-title]').forEach(function(el) {
    const key = el.getAttribute('data-i18n-title');
    el.setAttribute('title', t(key));
  });

  // Update toggle button text to show the OTHER language option
  const langBtn = document.getElementById('lang-btn');
  if (langBtn) {
    langBtn.textContent = currentLanguage === 'es' ? '🌐 EN' : '🌐 ES';
  }

  // Update document title
  document.title = t('title');

  // Refresh auth state UI
  refreshAuthState();

  // If a plan output exists, re-render it dynamically
  if (APP.lastDayPlan) {
    if (typeof renderLegEditor === 'function') renderLegEditor(APP.lastDayPlan);
    if (typeof renderResultTable === 'function') renderResultTable(APP.lastDayPlan);
    if (typeof showResult === 'function' && APP.lastResult) showResult(APP.lastResult);
  }
  
  // Re-render place list if available
  if (typeof renderList === 'function') {
    renderList();
  }
  
  // Re-render cost badge if relevant
  if (typeof updateCost === 'function') {
    updateCost();
  }
}

function toggleLanguage() {
  currentLanguage = currentLanguage === 'es' ? 'en' : 'es';
  localStorage.setItem('tripagent_lang', currentLanguage);
  applyTranslations();
  toast(currentLanguage === 'es' ? 'Idioma cambiado a Español' : 'Language changed to English', 'ok');
}

// Bind load event to apply translations when page opens
window.addEventListener('DOMContentLoaded', function() {
  applyTranslations();
});

const BUS_FARE_CLP = 770;
const METRO_FARE_CLP = { low: 710, valley: 790, peak: 870 };
const SEGMENT_STYLES = {
  driving:       {color:'#4285F4', weight:5, opacity:.85},
  walking:       {color:'#34A853', weight:4, opacity:.9, dashArray:'10 8'},
  transit_metro: {color:'#9C27B0', weight:6, opacity:.9},
  transit_bus:   {color:'#00ACC1', weight:5, opacity:.9, dashArray:'12 8'},
  cycling:       {color:'#FB8C00', weight:4, opacity:.9, dashArray:'7 5'}
};

// init layer groups
Object.keys(APP.layers).forEach(function(k){ APP.layers[k].group = L.layerGroup(); });

// ══════════════════════════════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════════════════════════════
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function fmtTime(iso){
  if(!iso) return '--:--';
  try{ return new Date(iso).toLocaleTimeString('es-CL',{hour:'2-digit',minute:'2-digit'}); }
  catch(e){ return iso; }
}

function fmtDur(min){
  if(!min || min<=0) return '0 min';
  if(min<60) return min+' min';
  const h=Math.floor(min/60), m=min%60;
  return m ? h+'h '+m+'min' : h+'h';
}

function fmtCurrency(n){ return '$'+Math.round(n).toLocaleString('es-CL'); }
function parkingPriceLabel(opt){
  if(opt.cost_clp_trip!=null){
    const lo = opt.cost_clp_trip_low!=null ? opt.cost_clp_trip_low : opt.cost_clp_trip;
    const hi = opt.cost_clp_trip_high!=null ? opt.cost_clp_trip_high : opt.cost_clp_trip;
    return fmtCurrency(lo)+'-'+fmtCurrency(hi)+'/viaje';
  }
  return fmtCurrency(opt.cost_clp_hr||0)+'/hr';
}

// Make sure global scope can see functions
window.t = t;
window.applyTranslations = applyTranslations;
window.toggleLanguage = toggleLanguage;

function canonicalArrivalMode(mode){
  if(!mode) return null;
  if(mode==='transit_metro'||mode==='transit_bus') return 'transit';
  return mode;
}

function routeModeLabel(mode){
  return {
    driving: t('lbl_driving'),
    walking: t('lbl_walking'),
    transit_metro: t('lbl_metro'),
    transit_bus: t('lbl_bus'),
    cycling: t('lbl_cycling'),
    transit: t('lbl_transit')
  }[mode] || t('lbl_driving');
}

function inferLegMode(stop){
  if(stop&&stop.leg_mode) return stop.leg_mode;
  if(stop&&stop.is_waypoint&&stop.waypoint_type==='metro') return 'transit_metro';
  if(stop&&stop.is_waypoint&&stop.waypoint_type==='bus') return 'transit_bus';
  return 'driving';
}

let toastTimer=null;
function toast(msg,type){
  const el=document.getElementById('toast');
  if(!el) return;
  el.textContent=msg;
  el.className='on '+(type||'');
  clearTimeout(toastTimer);
  toastTimer=setTimeout(function(){ el.classList.remove('on'); },3000);
}

function authHeaders(){
  if(!APP.authToken) return {};
  return { Authorization:'Bearer '+APP.authToken };
}

async function login(){
  const userEl=document.getElementById('auth-user');
  const passEl=document.getElementById('auth-pass');
  const stateEl=document.getElementById('auth-state');
  if(!userEl||!passEl||!stateEl) return;
  const username=(userEl.value||'').trim();
  const password=passEl.value||'';
  if(!username||!password){ toast(t('msg_fill_auth'),'er'); return; }
  try{
    const r=await fetch('/auth/login',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({username:username,password:password})
    });
    const data=await r.json();
    if(!r.ok) throw new Error(data.detail||t('msg_login_failed'));
    APP.authToken=data.access_token||'';
    APP.username=data.username||username;
    sessionStorage.setItem('tripagent_auth_token',APP.authToken);
    sessionStorage.setItem('tripagent_auth_user',APP.username);
    stateEl.textContent=t('auth_state_session')+APP.username;
    passEl.value='';
    toast(t('msg_session_started'),'ok');
    if(typeof applyBackendAvailability==='function'){ applyBackendAvailability(); }
  }catch(e){
    stateEl.textContent=t('auth_state_no_session');
    toast(t('msg_login_failed')+e.message,'er');
  }
}

function refreshAuthState(){
  const stateEl=document.getElementById('auth-state');
  if(!stateEl) return;
  stateEl.textContent=APP.username ? (t('auth_state_session')+APP.username) : t('auth_state_no_session');
}

// Initial state application
applyTranslations();

// ══════════════════════════════════════════════════════════════
// MAP
// ══════════════════════════════════════════════════════════════
const map=L.map('map',{zoomControl:true}).setView([-33.45,-70.65],13);
L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',{
  attribution:'&copy; OSM &copy; CARTO', maxZoom:19
}).addTo(map);

// ══════════════════════════════════════════════════════════════

function toggleMobilePanel() {
  const panel = document.getElementById('panel');
  if (panel) {
    panel.classList.toggle('open');
  }
}
