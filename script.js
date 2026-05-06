/* ================================================================
   SİBER GÜVENLİK PROJESİ — Frontend Veritabanı Simülasyonu
   SQL şemasındaki tüm mantık localStorage ile çalıştırılır.
   ================================================================ */

/* ---------- YARDIMCI FONKSİYONLAR ---------- */

function getUsers() {
  return JSON.parse(localStorage.getItem('users') || '[]');
}
function saveUsers(arr) {
  localStorage.setItem('users', JSON.stringify(arr));
}
function getLogs() {
  return JSON.parse(localStorage.getItem('login_logs') || '[]');
}
function saveLogs(arr) {
  localStorage.setItem('login_logs', JSON.stringify(arr));
}
function nextId(arr) {
  return arr.length === 0 ? 1 : Math.max(...arr.map(r => r.id)) + 1;
}
function now() {
  return new Date().toISOString().slice(0, 19).replace('T', ' ');
}

async function hashPassword(plain) {
  const enc = new TextEncoder().encode(plain);
  const buf = await crypto.subtle.digest('SHA-256', enc);
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

function showMsg(id, text, type) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'msg ' + (type || '');
  el.style.display = 'block';
  if (type === 'success') {
    setTimeout(() => { el.style.display = 'none'; }, 3000);
  }
}

/* ---------- VERİTABANI BAŞLATMA ---------- */

async function seedTestData() {
  if (localStorage.getItem('db_seeded_v2')) return;

  localStorage.removeItem('db_seeded');
  localStorage.removeItem('users');
  localStorage.removeItem('login_logs');

  const users = [{
    id: 1,
    username: 'admin',
    email: 'admin@test.com',
    password_hash: await hashPassword('admin123'),
    created_at: now(),
    is_locked: false,
    failed_attempts: 0,
    lock_until: null,
    role: 'admin'
  }];
  saveUsers(users);
  saveLogs([]);
  localStorage.setItem('db_seeded_v2', 'true');
}

/* ---------- SAYFA GEÇİŞİ ---------- */

function show(id) {
  document.querySelectorAll('.card').forEach(c => c.classList.add('hidden'));
  const target = document.getElementById(id);
  if (target) {
    target.classList.remove('hidden');
    target.style.animation = 'fadeSlideIn 0.4s ease';
  }
  document.querySelectorAll('.msg').forEach(m => { m.style.display = 'none'; });
}

/* ---------- KAYIT OL ---------- */

async function register() {
  const username = document.getElementById('regUser').value.trim();
  const email    = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPass').value;

  if (!username || !email || !password) {
    return showMsg('regMsg', 'Tüm alanları doldurun!', 'error');
  }
  if (password.length < 6) {
    return showMsg('regMsg', 'Şifre en az 6 karakter olmalı!', 'error');
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return showMsg('regMsg', 'Geçerli bir e-posta girin!', 'error');
  }

  const users = getUsers();

  if (users.find(u => u.username === username)) {
    return showMsg('regMsg', 'Bu kullanıcı adı zaten alınmış!', 'error');
  }
  if (users.find(u => u.email === email)) {
    return showMsg('regMsg', 'Bu e-posta zaten kayıtlı!', 'error');
  }

  users.push({
    id: nextId(users),
    username,
    email,
    password_hash: await hashPassword(password),
    created_at: now(),
    is_locked: false,
    failed_attempts: 0,
    lock_until: null,
    role: 'user'
  });
  saveUsers(users);

  showMsg('regMsg', 'Kayıt başarılı! Giriş yapabilirsiniz.', 'success');
  setTimeout(() => show('login'), 1500);
}

/* ---------- GİRİŞ YAP ---------- */

function getClientIP() {
  return '192.168.1.' + Math.floor(Math.random() * 254 + 1);
}

function addLog(userId, ip, status, reason) {
  const logs = getLogs();
  logs.push({
    id: nextId(logs),
    user_id: userId,
    ip_address: ip,
    attempt_time: now(),
    status,
    reason: reason || null
  });
  saveLogs(logs);
}

function checkAndUnlockExpired() {
  const users = getUsers();
  const current = new Date();
  let changed = false;
  users.forEach(u => {
    if (u.is_locked && u.lock_until) {
      const lockEnd = new Date(u.lock_until.replace(' ', 'T'));
      if (current >= lockEnd) {
        u.is_locked = false;
        u.lock_until = null;
        u.failed_attempts = 0;
        changed = true;
      }
    }
  });
  if (changed) saveUsers(users);
  return users;
}

async function login() {
  const username = document.getElementById('loginUser').value.trim();
  const password = document.getElementById('loginPass').value;
  const ip = getClientIP();

  if (!username || !password) {
    return showMsg('msg', 'Kullanıcı adı ve şifre girin!', 'error');
  }

  let users = checkAndUnlockExpired();
  const user = users.find(u => u.username === username);

  if (!user) {
    addLog(0, ip, 'failed', 'User not found');
    return showMsg('msg', 'Kullanıcı bulunamadı!', 'error');
  }

  if (user.is_locked) {
    const lockEnd = new Date(user.lock_until.replace(' ', 'T'));
    const remaining = Math.ceil((lockEnd - new Date()) / 60000);
    addLog(user.id, ip, 'failed', 'Account locked');
    return showMsg('msg', `Hesap kilitli! ${remaining} dakika sonra tekrar deneyin.`, 'error');
  }

  const inputHash = await hashPassword(password);

  if (inputHash !== user.password_hash) {
    user.failed_attempts += 1;
    addLog(user.id, ip, 'failed', 'Wrong password');

    if (user.failed_attempts >= 5) {
      user.is_locked = true;
      const lockTime = new Date();
      lockTime.setMinutes(lockTime.getMinutes() + 10);
      user.lock_until = lockTime.toISOString().slice(0, 19).replace('T', ' ');
      saveUsers(users);
      return showMsg('msg', 'Hesap kilitlendi! 5 yanlış giriş. 10 dakika bekleyin.', 'error');
    }

    saveUsers(users);
    return showMsg('msg', `Şifre yanlış! (${user.failed_attempts}/5 deneme)`, 'error');
  }

  user.failed_attempts = 0;
  user.is_locked = false;
  user.lock_until = null;
  saveUsers(users);
  addLog(user.id, ip, 'success', null);

  sessionStorage.setItem('currentUser', JSON.stringify({
    id: user.id,
    username: user.username,
    email: user.email,
    loginTime: now(),
    ip: ip
  }));

  showMsg('msg', 'Giriş başarılı! Yönlendiriliyorsunuz...', 'success');
  setTimeout(() => {
    if (user.username === 'admin') {
      window.location.href = 'dashboard.html';
    } else {
      window.location.href = 'user.html';
    }
  }, 1000);
}

/* ---------- ŞİFREMİ UNUTTUM ---------- */

let resetCodes = {};

function sendCode() {
  const email = document.getElementById('email').value.trim();
  if (!email) return showMsg('forgotMsg', 'E-posta adresinizi girin!', 'error');

  const users = getUsers();
  const user = users.find(u => u.email === email);
  if (!user) return showMsg('forgotMsg', 'Bu e-posta kayıtlı değil!', 'error');

  const code = Math.floor(100000 + Math.random() * 900000).toString();
  resetCodes[email] = { code, expires: Date.now() + 300000 };

  showMsg('forgotMsg', `Doğrulama kodu: ${code} (5 dk geçerli)`, 'success');
}

async function resetPass() {
  const email   = document.getElementById('email').value.trim();
  const code    = document.getElementById('code').value.trim();
  const newPass = document.getElementById('newPass').value;

  if (!email || !code || !newPass) {
    return showMsg('forgotMsg', 'Tüm alanları doldurun!', 'error');
  }
  if (newPass.length < 6) {
    return showMsg('forgotMsg', 'Yeni şifre en az 6 karakter olmalı!', 'error');
  }

  const entry = resetCodes[email];
  if (!entry) return showMsg('forgotMsg', 'Önce doğrulama kodu gönderin!', 'error');
  if (Date.now() > entry.expires) return showMsg('forgotMsg', 'Kodun süresi dolmuş! Tekrar gönderin.', 'error');
  if (entry.code !== code) return showMsg('forgotMsg', 'Kod yanlış!', 'error');

  const users = getUsers();
  const user = users.find(u => u.email === email);
  if (!user) return showMsg('forgotMsg', 'Kullanıcı bulunamadı!', 'error');

  user.password_hash = await hashPassword(newPass);
  user.failed_attempts = 0;
  user.is_locked = false;
  user.lock_until = null;
  saveUsers(users);

  delete resetCodes[email];
  showMsg('forgotMsg', 'Şifre değiştirildi! Giriş yapabilirsiniz.', 'success');
  setTimeout(() => show('login'), 1500);
}

/* ---------- DASHBOARD ---------- */

function loadUserPanel() {
  const raw = sessionStorage.getItem('currentUser');
  if (!raw) {
    window.location.href = 'index.html';
    return;
  }
  const cur = JSON.parse(raw);
  const el = document.getElementById('userPanelName');
  if (el) el.textContent = cur.username;
  const emailEl = document.getElementById('userPanelEmail');
  if (emailEl) emailEl.textContent = cur.email;
  const timeEl = document.getElementById('userPanelTime');
  if (timeEl) timeEl.textContent = cur.loginTime;
}

function loadDashboard() {
  const el = document.getElementById('userInfo');
  if (!el) return;

  const raw = sessionStorage.getItem('currentUser');
  if (!raw) {
    window.location.href = 'index.html';
    return;
  }

  const cur = JSON.parse(raw);

  if (cur.username !== 'admin') {
    window.location.href = 'user.html';
    return;
  }
  const users = getUsers();
  const logs = getLogs();
  const allUsers = users.length;
  const lockedCount = users.filter(u => u.is_locked).length;

  const userLogs = logs.filter(l => l.user_id === cur.id);
  const totalLogins = logs.length;
  const failedLogins = logs.filter(l => l.status === 'failed').length;
  const successLogins = logs.filter(l => l.status === 'success').length;
  const failRate = totalLogins > 0 ? ((failedLogins / totalLogins) * 100).toFixed(1) : 0;

  const ipStats = {};
  logs.forEach(l => {
    if (!ipStats[l.ip_address]) ipStats[l.ip_address] = { total: 0, failed: 0 };
    ipStats[l.ip_address].total++;
    if (l.status === 'failed') ipStats[l.ip_address].failed++;
  });
  const topIPs = Object.entries(ipStats)
    .sort((a, b) => b[1].total - a[1].total)
    .slice(0, 5);

  const welcomeEl = document.getElementById('welcomeUser');
  if (welcomeEl) welcomeEl.textContent = cur.username;

  const loginTimeEl = document.getElementById('loginTime');
  if (loginTimeEl) loginTimeEl.textContent = cur.loginTime;

  const loginIpEl = document.getElementById('loginIp');
  if (loginIpEl) loginIpEl.textContent = cur.ip;

  const statCards = document.getElementById('statCards');
  if (statCards) {
    statCards.innerHTML = `
      <div class="stat-card">
        <div class="stat-number">${allUsers}</div>
        <div class="stat-label">Toplam Kullanıcı</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">${totalLogins}</div>
        <div class="stat-label">Toplam Giriş Denemesi</div>
      </div>
      <div class="stat-card stat-success">
        <div class="stat-number">${successLogins}</div>
        <div class="stat-label">Başarılı Giriş</div>
      </div>
      <div class="stat-card stat-danger">
        <div class="stat-number">${failedLogins}</div>
        <div class="stat-label">Başarısız Giriş</div>
      </div>
      <div class="stat-card stat-warning">
        <div class="stat-number">%${failRate}</div>
        <div class="stat-label">Başarısızlık Oranı</div>
      </div>
      <div class="stat-card stat-danger">
        <div class="stat-number">${lockedCount}</div>
        <div class="stat-label">Kilitli Hesap</div>
      </div>
    `;
  }

  const topIPsEl = document.getElementById('topIPs');
  if (topIPsEl) {
    topIPsEl.innerHTML = topIPs.map(([ip, data]) => `
      <tr>
        <td>${ip}</td>
        <td>${data.total}</td>
        <td class="text-danger">${data.failed}</td>
      </tr>
    `).join('');
  }

  const logTable = document.getElementById('logTable');
  if (logTable) {
    const recent = userLogs.slice(-10).reverse();
    logTable.innerHTML = recent.map(l => `
      <tr>
        <td>${l.attempt_time}</td>
        <td>${l.ip_address}</td>
        <td><span class="badge ${l.status === 'success' ? 'badge-success' : 'badge-fail'}">${l.status === 'success' ? 'Başarılı' : 'Başarısız'}</span></td>
        <td>${l.reason || '-'}</td>
      </tr>
    `).join('');
  }

  const allLogTable = document.getElementById('allLogTable');
  if (allLogTable) {
    const recent = logs.slice(-20).reverse();
    allLogTable.innerHTML = recent.map(l => {
      const u = users.find(x => x.id === l.user_id);
      return `
        <tr>
          <td>${u ? u.username : '—'}</td>
          <td>${l.attempt_time}</td>
          <td>${l.ip_address}</td>
          <td><span class="badge ${l.status === 'success' ? 'badge-success' : 'badge-fail'}">${l.status === 'success' ? 'Başarılı' : 'Başarısız'}</span></td>
          <td>${l.reason || '-'}</td>
        </tr>
      `;
    }).join('');
  }
}

/* ---------- TAB SİSTEMİ ---------- */

function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  const btn = document.querySelector(`.tab-btn[onclick="switchTab('${tabName}')"]`);
  if (btn) btn.classList.add('active');

  const content = document.getElementById('tab-' + tabName);
  if (content) {
    content.classList.add('active');
    content.style.animation = 'fadeSlideIn 0.4s ease';
  }

  if (tabName === 'report') loadReports();
  if (tabName === 'filter') {
    // İlk açılışta tüm logları göster
    const results = document.getElementById('filterResults');
    if (results && results.innerHTML === '') applyFilter();
  }
}

/* ---------- LOG FİLTRELEME ---------- */

function applyFilter() {
  const username  = (document.getElementById('filterUser')?.value || '').trim().toLowerCase();
  const ip        = (document.getElementById('filterIP')?.value || '').trim();
  const dateStart = document.getElementById('filterDateStart')?.value || '';
  const dateEnd   = document.getElementById('filterDateEnd')?.value || '';
  const status    = document.getElementById('filterStatus')?.value || '';

  const users = getUsers();
  const logs  = getLogs();

  let filtered = logs.map(l => {
    const u = users.find(x => x.id === l.user_id);
    return { ...l, username: u ? u.username : '—', email: u ? u.email : '' };
  });

  // Kullanıcı adı filtresi
  if (username) {
    filtered = filtered.filter(l => l.username.toLowerCase().includes(username));
  }

  // IP filtresi
  if (ip) {
    filtered = filtered.filter(l => l.ip_address.includes(ip));
  }

  // Tarih aralığı filtresi
  if (dateStart) {
    const start = new Date(dateStart);
    filtered = filtered.filter(l => {
      const logDate = new Date(l.attempt_time.replace(' ', 'T'));
      return logDate >= start;
    });
  }
  if (dateEnd) {
    const end = new Date(dateEnd);
    filtered = filtered.filter(l => {
      const logDate = new Date(l.attempt_time.replace(' ', 'T'));
      return logDate <= end;
    });
  }

  // Durum filtresi
  if (status) {
    filtered = filtered.filter(l => l.status === status);
  }

  // Sonuçları en yeniden eskiye sırala
  filtered.sort((a, b) => {
    const da = new Date(a.attempt_time.replace(' ', 'T'));
    const db = new Date(b.attempt_time.replace(' ', 'T'));
    return db - da;
  });

  // Sonuç sayısını güncelle
  const countEl = document.getElementById('filterCount');
  if (countEl) countEl.textContent = `${filtered.length} kayıt bulundu`;

  // Tabloyu doldur
  const tbody = document.getElementById('filterResults');
  if (tbody) {
    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; opacity:0.5; padding:24px;">Filtreye uygun kayıt bulunamadı.</td></tr>`;
    } else {
      tbody.innerHTML = filtered.map((l, i) => `
        <tr>
          <td>${i + 1}</td>
          <td>${l.username}</td>
          <td>${l.attempt_time}</td>
          <td>${l.ip_address}</td>
          <td><span class="badge ${l.status === 'success' ? 'badge-success' : 'badge-fail'}">${l.status === 'success' ? 'Başarılı' : 'Başarısız'}</span></td>
          <td>${l.reason || '-'}</td>
        </tr>
      `).join('');
    }
  }
}

function clearFilter() {
  const ids = ['filterUser', 'filterIP', 'filterDateStart', 'filterDateEnd', 'filterStatus'];
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  applyFilter();
}

/* ---------- RAPORLAMA ---------- */

function loadReports() {
  const users = getUsers();
  const logs  = getLogs();

  const totalLogins   = logs.length;
  const failedLogins  = logs.filter(l => l.status === 'failed').length;
  const successLogins = logs.filter(l => l.status === 'success').length;
  const failRate      = totalLogins > 0 ? ((failedLogins / totalLogins) * 100).toFixed(1) : 0;
  const lockedCount   = users.filter(u => u.is_locked).length;

  // --- Genel İstatistik Kartları ---
  const reportStats = document.getElementById('reportStats');
  if (reportStats) {
    reportStats.innerHTML = `
      <div class="report-stat-card">
        <div class="report-stat-icon">📊</div>
        <div class="report-stat-value">${totalLogins}</div>
        <div class="report-stat-label">Toplam Giriş Denemesi</div>
      </div>
      <div class="report-stat-card rsc-success">
        <div class="report-stat-icon">✅</div>
        <div class="report-stat-value">${successLogins}</div>
        <div class="report-stat-label">Başarılı Giriş</div>
      </div>
      <div class="report-stat-card rsc-danger">
        <div class="report-stat-icon">❌</div>
        <div class="report-stat-value">${failedLogins}</div>
        <div class="report-stat-label">Başarısız Giriş</div>
      </div>
      <div class="report-stat-card rsc-warning">
        <div class="report-stat-icon">📉</div>
        <div class="report-stat-value">%${failRate}</div>
        <div class="report-stat-label">Başarısızlık Oranı</div>
      </div>
      <div class="report-stat-card rsc-danger">
        <div class="report-stat-icon">🔒</div>
        <div class="report-stat-value">${lockedCount}</div>
        <div class="report-stat-label">Kilitli Hesap</div>
      </div>
      <div class="report-stat-card rsc-info">
        <div class="report-stat-icon">👥</div>
        <div class="report-stat-value">${users.length}</div>
        <div class="report-stat-label">Toplam Kullanıcı</div>
      </div>
    `;
  }

  // --- Son 7 Günlük Dağılım (Bar Chart) ---
  const dailyChart = document.getElementById('dailyChart');
  if (dailyChart) {
    const dayMap = {};
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      dayMap[key] = { success: 0, failed: 0 };
    }

    logs.forEach(l => {
      const day = l.attempt_time.slice(0, 10);
      if (dayMap[day]) {
        if (l.status === 'success') dayMap[day].success++;
        else dayMap[day].failed++;
      }
    });

    const maxVal = Math.max(1, ...Object.values(dayMap).map(d => d.success + d.failed));

    dailyChart.innerHTML = `
      <div class="bar-chart">
        ${Object.entries(dayMap).map(([date, data]) => {
          const total = data.success + data.failed;
          const successPct = (data.success / maxVal) * 100;
          const failedPct = (data.failed / maxVal) * 100;
          const dayLabel = date.slice(5); // MM-DD
          return `
            <div class="bar-column">
              <div class="bar-value">${total}</div>
              <div class="bar-stack" style="height: 160px;">
                <div class="bar-segment bar-failed" style="height: ${failedPct}%;" title="Başarısız: ${data.failed}"></div>
                <div class="bar-segment bar-success" style="height: ${successPct}%;" title="Başarılı: ${data.success}"></div>
              </div>
              <div class="bar-label">${dayLabel}</div>
            </div>
          `;
        }).join('')}
      </div>
      <div class="chart-legend">
        <span class="legend-item"><span class="legend-dot legend-success"></span> Başarılı</span>
        <span class="legend-item"><span class="legend-dot legend-failed"></span> Başarısız</span>
      </div>
    `;
  }

  // --- Saatlik Dağılım ---
  const hourlyChart = document.getElementById('hourlyChart');
  if (hourlyChart) {
    const hourMap = {};
    for (let h = 0; h < 24; h++) hourMap[h] = 0;

    const today = new Date().toISOString().slice(0, 10);
    logs.forEach(l => {
      if (l.attempt_time.slice(0, 10) === today && l.status === 'failed') {
        const hour = parseInt(l.attempt_time.slice(11, 13));
        hourMap[hour]++;
      }
    });

    const maxHour = Math.max(1, ...Object.values(hourMap));

    hourlyChart.innerHTML = `
      <div class="hour-chart">
        ${Object.entries(hourMap).map(([hour, count]) => {
          const pct = (count / maxHour) * 100;
          return `
            <div class="hour-bar-col">
              <div class="hour-bar-val">${count > 0 ? count : ''}</div>
              <div class="hour-bar" style="height: ${Math.max(pct, 2)}%; opacity: ${count > 0 ? 1 : 0.2};"></div>
              <div class="hour-label">${String(hour).padStart(2, '0')}</div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // --- En Riskli Kullanıcılar ---
  const riskyUsers = document.getElementById('riskyUsers');
  if (riskyUsers) {
    const userFailMap = {};
    logs.forEach(l => {
      if (l.status === 'failed') {
        if (!userFailMap[l.user_id]) userFailMap[l.user_id] = 0;
        userFailMap[l.user_id]++;
      }
    });

    const sorted = Object.entries(userFailMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);

    if (sorted.length === 0) {
      riskyUsers.innerHTML = `<tr><td colspan="5" style="text-align:center; opacity:0.5; padding:24px;">Başarısız giriş kaydı yok.</td></tr>`;
    } else {
      riskyUsers.innerHTML = sorted.map(([uid, count], i) => {
        const u = users.find(x => x.id === parseInt(uid));
        return `
          <tr>
            <td>${i + 1}</td>
            <td>${u ? u.username : '—'}</td>
            <td>${u ? u.email : '—'}</td>
            <td class="text-danger">${count}</td>
            <td>${u && u.is_locked
              ? '<span class="badge badge-fail">🔒 Kilitli</span>'
              : '<span class="badge badge-success">✅ Aktif</span>'
            }</td>
          </tr>
        `;
      }).join('');
    }
  }

  // --- IP Bar Grafikleri ---
  const ipBars = document.getElementById('ipBars');
  if (ipBars) {
    const ipMap = {};
    logs.forEach(l => {
      if (!ipMap[l.ip_address]) ipMap[l.ip_address] = { total: 0, failed: 0 };
      ipMap[l.ip_address].total++;
      if (l.status === 'failed') ipMap[l.ip_address].failed++;
    });

    const sortedIPs = Object.entries(ipMap)
      .sort((a, b) => b[1].total - a[1].total)
      .slice(0, 5);
    const maxIP = sortedIPs.length > 0 ? sortedIPs[0][1].total : 1;

    ipBars.innerHTML = sortedIPs.map(([ip, data]) => {
      const totalPct = (data.total / maxIP) * 100;
      const failPct  = (data.failed / maxIP) * 100;
      return `
        <div class="ip-bar-row">
          <div class="ip-bar-label">${ip}</div>
          <div class="ip-bar-track">
            <div class="ip-bar-fill ip-bar-total" style="width: ${totalPct}%;">
              <span>${data.total} deneme</span>
            </div>
            <div class="ip-bar-fill ip-bar-failed" style="width: ${failPct}%;">
              <span>${data.failed} başarısız</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  // --- Kilitli Hesaplar ---
  const lockedAccounts = document.getElementById('lockedAccounts');
  const noLockedMsg    = document.getElementById('noLockedMsg');
  if (lockedAccounts) {
    const locked = users.filter(u => u.is_locked);
    if (locked.length === 0) {
      lockedAccounts.innerHTML = '';
      if (noLockedMsg) noLockedMsg.style.display = 'block';
    } else {
      if (noLockedMsg) noLockedMsg.style.display = 'none';
      lockedAccounts.innerHTML = locked.map(u => `
        <tr>
          <td>${u.username}</td>
          <td>${u.email}</td>
          <td class="text-danger">${u.failed_attempts}</td>
          <td>${u.lock_until || '—'}</td>
        </tr>
      `).join('');
    }
  }
}

function clearAllLogs() {
  if (!confirm('Tüm loglar silinecek! Emin misiniz?')) return;
  saveLogs([]);
  // Kullanıcıların failed_attempts sıfırla
  const users = getUsers();
  users.forEach(u => {
    u.failed_attempts = 0;
    u.is_locked = false;
    u.lock_until = null;
  });
  saveUsers(users);
  loadDashboard();
  loadReports();
  // Filtre sonuçlarını da temizle
  const filterResults = document.getElementById('filterResults');
  if (filterResults) filterResults.innerHTML = '';
  const filterCount = document.getElementById('filterCount');
  if (filterCount) filterCount.textContent = '0 kayıt bulundu';
  alert('Tüm loglar temizlendi!');
}

function logout() {
  sessionStorage.removeItem('currentUser');
  window.location.href = 'index.html';
}

/* ---------- SAYFA YÜKLENME ---------- */

document.addEventListener('DOMContentLoaded', async () => {
  await seedTestData();

  if (document.getElementById('userInfo')) {
    loadDashboard();
    loadReports();
  }

  if (document.getElementById('userPanelName')) {
    loadUserPanel();
  }
});
