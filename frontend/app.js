/* AttendAI — Frontend App */
const API = '';  // empty = same origin (served by Flask)
let token = localStorage.getItem('token') || '';
let role  = localStorage.getItem('role')  || '';
let uname = localStorage.getItem('uname') || '';
let uname_full = localStorage.getItem('uname_full') || '';
let webcamStream = null, webcamInterval = null, detectedFaces = {};
let trendChart = null, weeklyChart = null, donutChart = null;

// ── UTILS ─────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const toast = (msg, type='') => {
  const t = $('toast'); t.textContent = msg; t.className = `toast ${type}`;
  t.classList.remove('hidden');
  clearTimeout(t._to); t._to = setTimeout(()=>t.classList.add('hidden'), 3500);
};
const showMsg = (id, msg, type='success') => {
  const el = $(id); if(!el) return;
  el.textContent = msg; el.className = `msg ${type}`; el.classList.remove('hidden');
  setTimeout(()=>el.classList.add('hidden'), 5000);
};
const spin = (id, on) => { const el=$(id); if(el) el.classList.toggle('hidden',!on); };
const setDate = () => {
  const d = new Date();
  $('topbar-date').textContent = d.toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short',year:'numeric'});
};
const today = () => new Date().toISOString().split('T')[0];

async function api(path, opts={}) {
  const res = await fetch(API+path, {
    ...opts,
    headers: { ...(opts.headers||{}), ...(token ? {'Authorization':'Bearer '+token} : {}) }
  });
  if(res.status===401){ logout(); throw new Error('Session expired'); }
  const ct = res.headers.get('content-type')||'';
  if(ct.includes('application/json')){ const j=await res.json(); if(!res.ok) throw new Error(j.error||'Error'); return j; }
  if(!res.ok) throw new Error('Request failed');
  return res.blob();
}
const apiGet = path => api(path);
const apiPost = (path,body,isForm) => api(path,{ method:'POST', body: isForm ? body : JSON.stringify(body), headers: isForm ? {} : {'Content-Type':'application/json'} });

// ── AUTH ──────────────────────────────────────────────────────
async function login(e) {
  e.preventDefault();
  spin('login-spinner',true); $('login-error').textContent=''; $('login-btn').disabled=true;
  try {
    const d = await apiPost('/api/auth/login',{username:$('lf-username').value.trim(),password:$('lf-password').value});
    token=d.token; role=d.role; uname=d.username; uname_full=d.name||d.username;
    localStorage.setItem('token',token); localStorage.setItem('role',role);
    localStorage.setItem('uname',uname); localStorage.setItem('uname_full',uname_full);
    showApp();
  } catch(err){ $('login-error').textContent=err.message; }
  finally { spin('login-spinner',false); $('login-btn').disabled=false; }
}
function logout() {
  token=''; role=''; uname=''; uname_full='';
  localStorage.clear(); stopWebcam();
  $('app').classList.add('hidden'); $('login-screen').classList.remove('hidden');
  $('lf-username').value=''; $('lf-password').value='';
}
function showApp() {
  $('login-screen').classList.add('hidden'); $('app').classList.remove('hidden');
  $('sb-name').textContent=uname_full; $('sb-role').textContent=role;
  $('sb-avatar').textContent=(uname_full[0]||'U').toUpperCase();
  applyRoleVisibility(); setDate(); navigateTo('dashboard'); initData();
}
function applyRoleVisibility() {
  document.querySelectorAll('[data-roles]').forEach(el=>{
    const allowed = el.getAttribute('data-roles').split(',');
    el.style.display = allowed.includes(role) ? '' : 'none';
  });
}

// ── NAVIGATION ────────────────────────────────────────────────
function navigateTo(page) {
  document.querySelectorAll('.sb-item').forEach(i=>i.classList.remove('active'));
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  const item = document.querySelector(`.sb-item[data-page="${page}"]`);
  if(item) item.classList.add('active');
  const pg = $(`page-${page}`);
  if(pg) pg.classList.add('active');
  const titles = {dashboard:'Dashboard',register:'Register Student',import:'Batch Import',webcam:'Webcam Scan',video:'Video Upload',manual:'Manual Entry',history:'History',analytics:'Analytics',reports:'Reports',users:'User Management'};
  $('page-title').textContent = titles[page]||page;
  if(page==='dashboard') loadDashboard();
  if(page==='manual') loadStudentDropdown('man-student');
  if(page==='history') { loadStudentDropdown('hist-student'); $('hist-to').value=today(); setTimeout(searchHistory, 100); }
  if(page==='analytics') loadAnalytics();
  if(page==='reports') initReportDates();
  if(page==='users') loadUsers();
  if(page!=='webcam') stopWebcam();
  // sidebar close on mobile
  if(window.innerWidth<768) $('sidebar').classList.remove('open');
}

// ── INIT ──────────────────────────────────────────────────────
async function initData() {
  await loadStats();
  await loadDashboard();
  $('man-date').value = today();
}

// ── DASHBOARD ─────────────────────────────────────────────────
async function loadStats() {
  try {
    const d = await apiGet('/api/stats');
    $('s-present').textContent=d.today.Present||0;
    $('s-absent').textContent=d.today.Absent||0;
    $('s-late').textContent=d.today.Late||0;
    $('s-total').textContent=d.total_students||0;
    const total=d.total_students||0, present=d.today.Present||0, absent=d.today.Absent||0, late=d.today.Late||0;
    const rate = total>0 ? Math.round(present/total*100) : 0;
    $('rate-badge').textContent=`${rate}% Attendance Rate`;
    renderDonut(present,absent,late);
  } catch(e){ console.error(e); }
}
async function loadDashboard() {
  await loadStats();
  try {
    const records = await apiGet('/api/attendance?date='+today());
    renderAttendList('dash-list', records);
  } catch(e){ console.error(e); }
}
function renderAttendList(containerId, records) {
  const el = $(containerId); if(!el) return;
  if(!records.length){ el.innerHTML='<div class="empty-state"><i class="fas fa-inbox"></i><p>No records</p></div>'; return; }
  el.innerHTML = records.map(r=>{
    const ini=(r.name||'?').split(' ').map(n=>n[0]).join('').toUpperCase().slice(0,2);
    const cls=r.status==='Present'?'present':r.status==='Absent'?'absent':'late';
    return `<div class="att-item"><div class="att-info"><div class="att-av">${ini}</div><div><div class="att-name">${r.name}</div><div class="att-id">${r.student_id}</div></div></div><span class="badge ${cls}">${r.status}</span></div>`;
  }).join('');
}
function renderDonut(present, absent, late) {
  const ctx = $('donut-chart'); if(!ctx) return;
  if(donutChart) donutChart.destroy();
  donutChart = new Chart(ctx, {
    type:'doughnut',
    data:{ labels:['Present','Absent','Late'], datasets:[{data:[present,absent,late], backgroundColor:['#10B981','#EF4444','#F59E0B'], borderWidth:0, hoverOffset:8}] },
    options:{ cutout:'72%', plugins:{ legend:{ position:'bottom', labels:{padding:16,font:{size:12}} } }, animation:{animateRotate:true} }
  });
}

// ── REGISTER STUDENT ──────────────────────────────────────────
$('reg-image').addEventListener('change', function(){
  const file = this.files[0]; if(!file) return;
  const reader = new FileReader();
  reader.onload = e => { const img=$('reg-preview'); img.src=e.target.result; img.classList.remove('hidden'); $('reg-upload-placeholder').classList.add('hidden'); };
  reader.readAsDataURL(file);
});
$('reg-form').addEventListener('submit', async function(e){
  e.preventDefault(); spin('reg-spin',true);
  try {
    const fd = new FormData();
    fd.append('name',$('reg-name').value.trim());
    fd.append('student_id',$('reg-sid').value.trim());
    fd.append('email',$('reg-email').value.trim());
    fd.append('department',$('reg-dept').value.trim());
    fd.append('year',$('reg-year').value);
    if($('reg-image').files[0]) fd.append('image',$('reg-image').files[0]);
    const d = await apiPost('/api/add_student',fd,true);
    toast(d.message,'success'); showMsg('reg-msg',d.message,'success');
    this.reset(); $('reg-preview').classList.add('hidden'); $('reg-upload-placeholder').classList.remove('hidden');
  } catch(err){ showMsg('reg-msg',err.message,'error'); }
  finally { spin('reg-spin',false); }
});
$('train-btn').addEventListener('click', async function(){
  spin('train-spin',true);
  try { const d=await apiPost('/api/train_model',{}); toast(d.message,'success'); showMsg('train-msg',d.message,'success'); }
  catch(err){ showMsg('train-msg',err.message,'error'); }
  finally { spin('train-spin',false); }
});

// ── BATCH IMPORT ──────────────────────────────────────────────
$('import-file').addEventListener('change', function(){
  $('import-filename').textContent = this.files[0]?.name || 'Click or drag CSV / Excel file';
  $('import-icon').className = this.files[0]?.name?.endsWith('.csv') ? 'fas fa-file-csv' : 'fas fa-file-excel';
});
$('import-btn').addEventListener('click', async function(){
  const file = $('import-file').files[0];
  if(!file){ toast('Please select a file','error'); return; }
  spin('import-spin',true);
  try {
    const fd = new FormData(); fd.append('file',file);
    const d = await apiPost('/api/import_students',fd,true);
    const res = $('import-result');
    res.className=`import-result ${d.errors?.length?'error':'success'}`; res.classList.remove('hidden');
    res.innerHTML=`<b>✓ Imported: ${d.imported}/${d.total}</b>${d.errors?.length?`<br><small>Errors:<br>${d.errors.slice(0,5).join('<br>')}</small>`:''}`;
    toast(`Imported ${d.imported} students`,'success');
  } catch(err){ toast(err.message,'error'); }
  finally { spin('import-spin',false); }
});
$('dl-template').addEventListener('click', ()=>{
  const csv='student_id,name,email,department,year\nCS001,Aarav Kumar,aarav@college.edu,CSE,2\nCS002,Priya Sharma,priya@college.edu,ECE,3';
  const a=document.createElement('a'); a.href='data:text/csv;charset=utf-8,'+encodeURIComponent(csv);
  a.download='student_template.csv'; a.click();
});

// ── VIDEO RECOGNITION ─────────────────────────────────────────
$('vid-file').addEventListener('change', function(){ $('vid-fname').textContent=this.files[0]?.name||'Choose video'; });
$('vid-form').addEventListener('submit', async function(e){
  e.preventDefault(); spin('vid-spin',true);
  const fd=new FormData(); fd.append('video',$('vid-file').files[0]);
  try {
    const d=await apiPost('/api/recognize',fd,true);
    const msg=`✓ ${d.present_count} Present, ✗ ${d.absent_count} Absent`;
    toast(msg,'success'); showMsg('vid-msg',msg,'success');
    this.reset(); $('vid-fname').textContent='Choose video';
  } catch(err){ showMsg('vid-msg',err.message,'error'); }
  finally { spin('vid-spin',false); }
});

// ── WEBCAM ────────────────────────────────────────────────────
$('webcam-start').addEventListener('click', startWebcam);
$('webcam-stop').addEventListener('click', stopWebcam);
$('webcam-mark').addEventListener('click', markWebcamAttendance);

async function startWebcam() {
  try {
    webcamStream = await navigator.mediaDevices.getUserMedia({video:{width:640,height:480},audio:false});
    const vid=$('webcam-video'); vid.srcObject=webcamStream;
    $('webcam-overlay').style.display='none';
    $('webcam-start').classList.add('hidden'); $('webcam-stop').classList.remove('hidden'); $('webcam-mark').classList.remove('hidden');
    detectedFaces={};
    webcamInterval = setInterval(captureFrame, 2000);
  } catch(err){ toast('Camera error: '+err.message,'error'); }
}
function stopWebcam() {
  if(webcamStream){ webcamStream.getTracks().forEach(t=>t.stop()); webcamStream=null; }
  if(webcamInterval){ clearInterval(webcamInterval); webcamInterval=null; }
  const vid=$('webcam-video'); if(vid) vid.srcObject=null;
  if($('webcam-overlay')) $('webcam-overlay').style.display='';
  if($('webcam-start')){ $('webcam-start').classList.remove('hidden'); $('webcam-stop').classList.add('hidden'); $('webcam-mark').classList.add('hidden'); }
}
async function captureFrame() {
  if(!webcamStream) return;
  const vid=$('webcam-video'), canvas=$('webcam-canvas');
  canvas.width=vid.videoWidth; canvas.height=vid.videoHeight;
  const ctx=canvas.getContext('2d'); ctx.drawImage(vid,0,0);
  const b64=canvas.toDataURL('image/jpeg',0.6);
  try {
    const d=await apiPost('/api/recognize_frame',{image:b64});
    if(d.faces?.length){ d.faces.filter(f=>f.student_id).forEach(f=>{ detectedFaces[f.student_id]=f.name; }); }
    renderDetected();
    // Draw boxes
    ctx.strokeStyle='#10B981'; ctx.lineWidth=2; ctx.font='14px Inter';
    d.faces?.forEach(f=>{
      const [t,r,b,l]=f.location||[];
      if(t!==undefined){ ctx.strokeRect(l*2,t*2,(r-l)*2,(b-t)*2); ctx.fillStyle='#10B981'; ctx.fillText(f.name,l*2,(t*2)-4); }
    });
  } catch(e){}
}
function renderDetected() {
  const el=$('webcam-detected'); if(!el) return;
  const names=Object.values(detectedFaces);
  el.innerHTML = names.length ? names.map(n=>`<div class="detected-chip"><i class="fas fa-check-circle"></i>${n}</div>`).join('') : '';
}
async function markWebcamAttendance() {
  const ids=Object.keys(detectedFaces);
  if(!ids.length){ toast('No faces detected yet','error'); return; }
  try {
    for(const sid of ids){ await apiPost('/api/update_attendance',{student_id:sid,status:'Present',date:today()}); }
    toast(`Marked ${ids.length} students Present`,'success'); showMsg('webcam-msg',`Marked Present: ${Object.values(detectedFaces).join(', ')}`,'success');
  } catch(e){ toast(e.message,'error'); }
}

// ── MANUAL ENTRY ──────────────────────────────────────────────
async function loadStudentDropdown(elId) {
  try {
    const students=await apiGet('/api/students');
    const sel=$(elId); sel.innerHTML='<option value="">Select student...</option>';
    students.forEach(s=>{ const o=document.createElement('option'); o.value=s.student_id; o.textContent=`${s.name} (${s.student_id})`; sel.appendChild(o); });
  } catch(e){ console.error(e); }
}
$('man-form').addEventListener('submit', async function(e){
  e.preventDefault(); spin('man-spin',true);
  const sid=$('man-student').value, date=$('man-date').value, status=document.querySelector('input[name="man-status"]:checked')?.value;
  if(!sid||!status){ showMsg('man-msg','Please select student and status','error'); spin('man-spin',false); return; }
  try {
    const d=await apiPost('/api/update_attendance',{student_id:sid,status,date});
    toast(d.message,'success'); showMsg('man-msg',d.message,'success');
  } catch(err){ showMsg('man-msg',err.message,'error'); }
  finally { spin('man-spin',false); }
});

// ── HISTORY ───────────────────────────────────────────────────
$('hist-search').addEventListener('click', searchHistory);
$('hist-export-csv').addEventListener('click', ()=>{ const f=$('hist-from').value,t=$('hist-to').value; window.location.href=`/api/export_csv?from=${f}&to=${t}&token=${token}`; });

async function searchHistory() {
  const from=$('hist-from').value, to=$('hist-to').value||today(), sid=$('hist-student').value;
  try {
    let url='/api/attendance/history?';
    if(sid) url+=`student_id=${sid}&`;
    if(from) url+=`from=${from}&to=${to}`;
    const records=await apiGet(url);
    const tb=$('hist-body');
    tb.innerHTML=records.length ? records.map((r,i)=>{
      const cls=r.status==='Present'?'present':r.status==='Absent'?'absent':'late';
      return `<tr><td>${i+1}</td><td>${r.student_id}</td><td>${r.name}</td><td>${r.date}</td><td><span class="badge ${cls}">${r.status}</span></td></tr>`;
    }).join('') : '<tr><td colspan="5" class="tc">No records found</td></tr>';
  } catch(e){ toast(e.message,'error'); }
}

// ── ANALYTICS ─────────────────────────────────────────────────
async function loadAnalytics() {
  try {
    const d=await apiGet('/api/analytics');
    renderTrendChart(d.daily_trend);
    renderWeeklyChart(d.weekly);
    renderStudentAnalytics(d.student_stats);
    renderTopAttendees(d.student_stats);
  } catch(e){ toast(e.message,'error'); }
}
function renderTrendChart(trend) {
  const ctx=$('trend-chart'); if(!ctx) return;
  if(trendChart) trendChart.destroy();
  const dates=Object.keys(trend).sort().slice(-30);
  const present=dates.map(d=>trend[d]?.Present||0);
  const absent=dates.map(d=>trend[d]?.Absent||0);
  trendChart=new Chart(ctx,{
    type:'line',
    data:{ labels:dates.map(d=>d.slice(5)), datasets:[
      {label:'Present',data:present,borderColor:'#10B981',backgroundColor:'rgba(16,185,129,.1)',tension:.4,fill:true},
      {label:'Absent',data:absent,borderColor:'#EF4444',backgroundColor:'rgba(239,68,68,.05)',tension:.4,fill:true}
    ]},
    options:{ responsive:true, plugins:{legend:{position:'top'}}, scales:{y:{beginAtZero:true,ticks:{stepSize:1}}} }
  });
}
function renderWeeklyChart(weekly) {
  const ctx=$('weekly-chart'); if(!ctx) return;
  if(weeklyChart) weeklyChart.destroy();
  const days=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const data=new Array(7).fill(0); weekly.forEach(r=>{ data[parseInt(r.dow)]=Math.round(r.rate||0); });
  weeklyChart=new Chart(ctx,{
    type:'bar',
    data:{ labels:days, datasets:[{label:'Attendance %',data,backgroundColor:'rgba(255,140,66,.8)',borderRadius:8}] },
    options:{ responsive:true, scales:{y:{min:0,max:100,ticks:{callback:v=>v+'%'}}}, plugins:{legend:{display:false}} }
  });
}
function renderStudentAnalytics(stats) {
  const tb=$('analytics-body'); if(!tb) return;
  tb.innerHTML=stats.map(s=>{
    const rate=s.total>0?Math.round(s.present/s.total*100):0;
    const cls=rate>=75?'present':rate>=50?'late':'absent';
    return `<tr><td>${s.student_id}</td><td>${s.name}</td><td>${s.present||0}</td><td>${s.absent||0}</td><td>${s.late||0}</td><td>${s.total||0}</td><td><span class="badge ${cls}">${rate}%</span></td></tr>`;
  }).join('');
}
function renderTopAttendees(stats) {
  const el=$('top-list'); if(!el) return;
  const sorted=[...stats].filter(s=>s.total>0).sort((a,b)=>(b.present/b.total)-(a.present/a.total)).slice(0,5);
  el.innerHTML=sorted.map(s=>{
    const rate=Math.round(s.present/s.total*100);
    return `<div class="att-item"><div class="att-info"><div class="att-av">${s.name[0]}</div><div><div class="att-name">${s.name}</div><div class="att-id">${s.student_id}</div><div class="progress-bar"><div class="progress-fill" style="width:${rate}%"></div></div></div></div><span class="badge present">${rate}%</span></div>`;
  }).join('') || '<div class="empty-state"><p>No data</p></div>';
}

// ── REPORTS ───────────────────────────────────────────────────
function initReportDates() {
  const t=today(), fm=t.slice(0,8)+'01';
  $('rpt-date').value=t; $('rpt-from').value=fm; $('rpt-to').value=t;
  $('csv-from').value=fm; $('csv-to').value=t;
}
$('rpt-daily-btn').addEventListener('click',()=>{ const d=$('rpt-date').value||today(); downloadFile(`/api/export_pdf?date=${d}`); });
$('rpt-summary-btn').addEventListener('click',()=>{ const f=$('rpt-from').value,t=$('rpt-to').value||today(); downloadFile(`/api/export_pdf_summary?from=${f}&to=${t}`); });
$('rpt-csv-btn').addEventListener('click',()=>{ const f=$('csv-from').value,t=$('csv-to').value||today(); downloadFile(`/api/export_csv?from=${f}&to=${t}`); });
function downloadFile(url) {
  fetch(API+url,{headers:{Authorization:'Bearer '+token}}).then(r=>r.blob()).then(blob=>{
    const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=url.split('/').pop().split('?')[0]; a.click();
  }).catch(e=>toast(e.message,'error'));
}

// ── USER MANAGEMENT ───────────────────────────────────────────
async function loadUsers() {
  try {
    const users=await apiGet('/api/auth/users');
    const tb=$('users-body');
    tb.innerHTML=users.map(u=>`
      <tr>
        <td><b>${u.username}</b></td><td>${u.full_name||'—'}</td>
        <td><span class="badge ${u.role==='admin'?'absent':u.role==='teacher'?'late':'present'}">${u.role}</span></td>
        <td><span class="badge ${u.is_active?'present':'absent'}">${u.is_active?'Active':'Inactive'}</span></td>
        <td>${u.last_login?u.last_login.slice(0,16):'Never'}</td>
        <td><button class="btn-sm" onclick="openUserModal(${u.id},'${u.username}','${u.full_name||''}','${u.email||''}','${u.role}',${u.is_active})">Edit</button></td>
      </tr>`).join('');
  } catch(e){ toast(e.message,'error'); }
}
$('add-user-btn').addEventListener('click',()=>openUserModal());
function openUserModal(id='',username='',name='',email='',urole='student',active=1) {
  $('user-modal-title').textContent=id?'Edit User':'Add User';
  $('um-id').value=id; $('um-username').value=username; $('um-name').value=name;
  $('um-email').value=email; $('um-role').value=urole; $('um-active').value=active;
  $('um-password').value=''; $('um-username').readOnly=!!id;
  $('user-modal').classList.remove('hidden');
}
function closeUserModal(){ $('user-modal').classList.add('hidden'); }
$('user-modal-close').addEventListener('click',closeUserModal);
$('user-modal-cancel').addEventListener('click',closeUserModal);
$('user-form').addEventListener('submit', async function(e){
  e.preventDefault(); const id=$('um-id').value;
  const payload={full_name:$('um-name').value,email:$('um-email').value,role:$('um-role').value,is_active:parseInt($('um-active').value)};
  if($('um-password').value) payload.password=$('um-password').value;
  if(!id) payload.username=$('um-username').value;
  try {
    if(id){ await api(`/api/auth/users/${id}`,{method:'PUT',body:JSON.stringify(payload),headers:{'Content-Type':'application/json'}}); }
    else { await apiPost('/api/auth/register',payload); }
    toast('User saved','success'); closeUserModal(); loadUsers();
  } catch(err){ toast(err.message,'error'); }
});

// ── EVENT WIRING ──────────────────────────────────────────────
$('login-form').addEventListener('submit',login);
$('logout-btn').addEventListener('click',logout);
$('hamburger').addEventListener('click',()=>{ $('sidebar').classList.toggle('open'); });
$('lf-eye').addEventListener('click',()=>{
  const inp=$('lf-password'); inp.type=inp.type==='password'?'text':'password';
  $('lf-eye').innerHTML=inp.type==='password'?'<i class="fas fa-eye"></i>':'<i class="fas fa-eye-slash"></i>';
});
$('refresh-btn').addEventListener('click',()=>{ loadStats(); toast('Refreshed',''); });
$('dash-refresh').addEventListener('click', loadDashboard);
$('dash-export-pdf').addEventListener('click',()=>downloadFile(`/api/export_pdf?date=${today()}`));
document.querySelectorAll('.sb-item').forEach(item=>{
  item.addEventListener('click',e=>{ e.preventDefault(); navigateTo(item.getAttribute('data-page')); });
});

// ── STARTUP ───────────────────────────────────────────────────
if(token){
  // Validate token by checking health
  fetch(API+'/api/health',{headers:{'Authorization':'Bearer '+token}})
    .then(r=>{ if(r.status===401) logout(); else showApp(); })
    .catch(()=>showApp());
} else {
  $('login-screen').classList.remove('hidden');
}


// ── ML ANALYTICS ──────────────────────────────────────────────
let mlPredictionChart = null;

async function loadMLAnalytics() {
  try {
    // Show loading states
    $('ml-linear-loading').classList.remove('hidden');
    $('ml-logistic-loading').classList.remove('hidden');
    $('ml-insights-loading').classList.remove('hidden');
    $('ml-linear-content').classList.add('hidden');
    $('ml-logistic-content').classList.add('hidden');
    $('ml-insights-content').classList.add('hidden');

    // Fetch full ML analysis
    const data = await apiGet('/api/ml/full_analysis');

    if (!data.success) {
      // Show error message
      const errorMsg = data.error || 'ML analysis failed';
      $('ml-linear-loading').innerHTML = `
        <i class="fas fa-exclamation-circle fa-2x" style="color: var(--orange);"></i>
        <p>${errorMsg}</p>
        <p style="margin-top: 12px; font-size: 0.9rem;">
          <strong>To use ML Analytics:</strong><br>
          • Add at least 10 days of attendance records<br>
          • Register at least 5 students<br>
          • Mark attendance for multiple days
        </p>
      `;
      $('ml-logistic-loading').classList.add('hidden');
      $('ml-insights-loading').classList.add('hidden');
      
      // Update stats to show zeros
      $('ml-trend').textContent = '—';
      $('ml-trend-sub').textContent = 'Insufficient data';
      $('ml-risk-count').textContent = '—';
      $('ml-risk-sub').textContent = 'Insufficient data';
      $('ml-avg').textContent = '—';
      $('ml-accuracy').textContent = '—';
      $('ml-accuracy-sub').textContent = 'Insufficient data';
      
      toast('Insufficient data for ML analysis', 'error');
      return;
    }

    // Update Linear Regression
    if (data.linear_regression && data.linear_regression.success) {
      displayLinearRegression(data.linear_regression);
    } else {
      $('ml-linear-loading').innerHTML = `
        <i class="fas fa-info-circle fa-2x" style="color: var(--blue);"></i>
        <p>${data.linear_regression?.error || 'Insufficient data for predictions'}</p>
        <p style="margin-top: 8px; font-size: 0.9rem;">Need at least 10 days of attendance records</p>
      `;
    }

    // Update Logistic Regression
    if (data.logistic_regression && data.logistic_regression.success) {
      displayLogisticRegression(data.logistic_regression);
    } else {
      $('ml-logistic-loading').innerHTML = `
        <i class="fas fa-info-circle fa-2x" style="color: var(--blue);"></i>
        <p>${data.logistic_regression?.error || 'Insufficient data for classification'}</p>
        <p style="margin-top: 8px; font-size: 0.9rem;">Need at least 5 students with 5+ attendance records each</p>
      `;
    }

    // Update Overall Insights
    if (data.overall_insights && data.overall_insights.length > 0) {
      displayOverallInsights(data.overall_insights);
    } else {
      $('ml-insights-loading').innerHTML = `
        <i class="fas fa-info-circle fa-2x" style="color: var(--blue);"></i>
        <p>Add more attendance data to see insights</p>
      `;
    }

    // Update top stats
    updateMLStats(data);

    if (data.success) {
      toast('ML analysis completed successfully', 'success');
    }
  } catch (err) {
    console.error('ML Analytics error:', err);
    toast(err.message || 'Failed to load ML analytics', 'error');
    
    // Show friendly error message
    $('ml-linear-loading').innerHTML = `
      <i class="fas fa-exclamation-triangle fa-2x" style="color: var(--red);"></i>
      <p>Error loading ML analytics</p>
      <p style="margin-top: 8px; font-size: 0.9rem;">${err.message}</p>
    `;
    $('ml-logistic-loading').classList.add('hidden');
    $('ml-insights-loading').classList.add('hidden');
  }
}

function displayLinearRegression(data) {
  $('ml-linear-loading').classList.add('hidden');
  $('ml-linear-content').classList.remove('hidden');

  // Update info cards
  $('ml-direction').innerHTML = `
    <i class="fas fa-arrow-${data.trend.direction === 'improving' ? 'up' : 'down'}" 
       style="color: ${data.trend.direction === 'improving' ? 'var(--green)' : 'var(--red)'}"></i>
    ${data.trend.direction.charAt(0).toUpperCase() + data.trend.direction.slice(1)}
  `;
  $('ml-rate').textContent = `${data.trend.rate_per_day > 0 ? '+' : ''}${data.trend.rate_per_day}% per day`;
  $('ml-strength').textContent = data.trend.strength.charAt(0).toUpperCase() + data.trend.strength.slice(1);
  $('ml-r2').textContent = data.metrics.r2_score.toFixed(3);

  // Update recommendation
  $('ml-rec-text').textContent = data.recommendation;

  // Create prediction chart
  const labels = data.predictions.map(p => `Day ${p.day}`);
  const values = data.predictions.map(p => p.predicted_rate);

  const ctx = $('ml-prediction-chart').getContext('2d');
  
  if (mlPredictionChart) {
    mlPredictionChart.destroy();
  }

  mlPredictionChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Predicted Attendance Rate (%)',
        data: values,
        borderColor: data.trend.direction === 'improving' ? '#10B981' : '#EF4444',
        backgroundColor: data.trend.direction === 'improving' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointBackgroundColor: '#fff',
        pointBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top'
        },
        tooltip: {
          callbacks: {
            label: (context) => `${context.parsed.y.toFixed(2)}%`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          min: Math.max(0, Math.min(...values) - 5),
          max: Math.min(100, Math.max(...values) + 5),
          ticks: {
            callback: (value) => value + '%'
          }
        }
      }
    }
  });
}

function displayLogisticRegression(data) {
  $('ml-logistic-loading').classList.add('hidden');
  $('ml-logistic-content').classList.remove('hidden');

  // Update risk summary
  $('ml-total-students').textContent = data.summary.total_students;
  
  // Count by severity
  const critical = data.at_risk_students.filter(s => s.severity === 'Critical').length;
  const high = data.at_risk_students.filter(s => s.severity === 'High').length;
  const medium = data.at_risk_students.filter(s => s.severity === 'Medium').length;
  
  $('ml-critical-count').textContent = critical;
  $('ml-high-count').textContent = high;
  $('ml-medium-count').textContent = medium;
  $('ml-good-count').textContent = data.summary.good_standing_count;

  // Populate at-risk table
  const riskBody = $('ml-risk-body');
  riskBody.innerHTML = '';
  
  if (data.at_risk_students.length === 0) {
    riskBody.innerHTML = '<tr><td colspan="7" class="tc">No at-risk students found! 🎉</td></tr>';
  } else {
    data.at_risk_students.forEach(student => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${student.student_id}</td>
        <td>${student.name}</td>
        <td><strong>${student.attendance_rate.toFixed(1)}%</strong></td>
        <td>${student.recent_trend.toFixed(1)}%</td>
        <td><strong>${student.risk_probability.toFixed(1)}%</strong></td>
        <td><span class="severity-badge ${student.severity.toLowerCase()}">${student.severity}</span></td>
        <td>${student.max_consecutive_absent}</td>
      `;
      riskBody.appendChild(row);
    });
  }

  // Populate good standing table
  const goodBody = $('ml-good-body');
  goodBody.innerHTML = '';
  
  if (data.good_standing_students.length === 0) {
    goodBody.innerHTML = '<tr><td colspan="6" class="tc">No students in good standing</td></tr>';
  } else {
    data.good_standing_students.forEach(student => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${student.student_id}</td>
        <td>${student.name}</td>
        <td><strong>${student.attendance_rate.toFixed(1)}%</strong></td>
        <td>${student.recent_trend.toFixed(1)}%</td>
        <td><strong>${student.good_probability.toFixed(1)}%</strong></td>
        <td><span class="badge green">Good Standing</span></td>
      `;
      goodBody.appendChild(row);
    });
  }

  // Display recommendations
  const recList = $('ml-rec-list');
  recList.innerHTML = '';
  data.recommendations.forEach(rec => {
    const li = document.createElement('li');
    li.textContent = rec;
    recList.appendChild(li);
  });
}

function displayOverallInsights(insights) {
  $('ml-insights-loading').classList.add('hidden');
  $('ml-insights-content').classList.remove('hidden');

  const grid = $('ml-insights-grid');
  grid.innerHTML = '';

  insights.forEach(insight => {
    const card = document.createElement('div');
    
    // Determine card type based on emoji/icon
    let cardType = 'info';
    let icon = 'fa-info-circle';
    
    if (insight.includes('🔴') || insight.includes('Critical')) {
      cardType = 'critical';
      icon = 'fa-exclamation-circle';
    } else if (insight.includes('🟡') || insight.includes('🟠') || insight.includes('Warning')) {
      cardType = 'warning';
      icon = 'fa-exclamation-triangle';
    } else if (insight.includes('🟢') || insight.includes('Positive')) {
      cardType = 'positive';
      icon = 'fa-check-circle';
    }

    card.className = `ml-insight-card ${cardType}`;
    card.innerHTML = `
      <i class="fas ${icon}"></i>
      <p>${insight}</p>
    `;
    grid.appendChild(card);
  });
}

function updateMLStats(data) {
  // Update trend stat
  if (data.linear_regression && data.linear_regression.success) {
    const lr = data.linear_regression;
    $('ml-trend').innerHTML = `
      <i class="fas fa-arrow-${lr.trend.direction === 'improving' ? 'up' : 'down'}"></i>
      ${lr.trend.direction.charAt(0).toUpperCase() + lr.trend.direction.slice(1)}
    `;
    $('ml-trend-sub').textContent = `${lr.trend.rate_per_day > 0 ? '+' : ''}${lr.trend.rate_per_day}% per day`;
    $('ml-avg').textContent = `${lr.current_average.toFixed(1)}%`;
  }

  // Update risk stat
  if (data.logistic_regression && data.logistic_regression.success) {
    const log = data.logistic_regression;
    $('ml-risk-count').textContent = log.summary.at_risk_count;
    $('ml-risk-sub').textContent = `${log.summary.at_risk_percentage.toFixed(1)}% of students`;
    $('ml-accuracy').textContent = `${log.model_performance.accuracy.toFixed(1)}%`;
    $('ml-accuracy-sub').textContent = log.model_performance.quality.charAt(0).toUpperCase() + log.model_performance.quality.slice(1);
  }
}

// ML Tab switching
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('ml-tab')) {
    // Remove active from all tabs
    document.querySelectorAll('.ml-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.ml-tab-content').forEach(content => content.classList.remove('active'));
    
    // Add active to clicked tab
    e.target.classList.add('active');
    const tabName = e.target.dataset.tab;
    $(`ml-tab-${tabName}`).classList.add('active');
  }
});

// ML Refresh button
if ($('ml-refresh')) {
  $('ml-refresh').addEventListener('click', loadMLAnalytics);
}

// Load ML analytics when page is shown
document.addEventListener('DOMContentLoaded', () => {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.target.id === 'page-ml-analytics' && mutation.target.classList.contains('active')) {
        loadMLAnalytics();
      }
    });
  });

  const mlPage = $('page-ml-analytics');
  if (mlPage) {
    observer.observe(mlPage, { attributes: true, attributeFilter: ['class'] });
  }
});
