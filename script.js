
const API = 'http://127.0.0.1:5000/api';

/* ---------- YARDIMCI FONKSİYONLAR ---------- */

async function apiFetch(url, options = {}) {
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    });
    return await res.json();
  } catch (err) {
    console.error('API Hatası:', err);
    return { status: 'error', message: 'Sunucuya bağlanılamadı! Flask çalışıyor mu?' };
  }
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

/* ---------- GERİ SAYIM ZAMANLAYICI ---------- */

let countdownInterval = null;

function startCountdown(msgId, seconds, baseMessage) {
  // Önceki zamanlayıcıyı temizle
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }

  let remaining = seconds;
  const el = document.getElementById(msgId);
  if (!el) return;

  // Login butonunu devre dışı bırak
  const loginBtn = document.querySelector('#login .btn');
  if (loginBtn) {
    loginBtn.disabled = true;
    loginBtn.style.opacity = '0.5';
    loginBtn.style.cursor = 'not-allowed';
  }

  // İlk gösterim
  el.innerHTML = `${baseMessage}<br><span class="countdown-timer">⏳ Kalan süre: <strong>${remaining}</strong> saniye</span>`;
  el.className = 'msg error';
  el.style.display = 'block';

  countdownInterval = setInterval(() => {
    remaining--;
    if (remaining <= 0) {
      clearInterval(countdownInterval);
      countdownInterval = null;
      el.innerHTML = `✅ Kilit süresi doldu! Tekrar deneyebilirsiniz.`;
      el.className = 'msg success';
      // Login butonunu tekrar aktif et
      if (loginBtn) {
        loginBtn.disabled = false;
        loginBtn.style.opacity = '1';
        loginBtn.style.cursor = 'pointer';
      }
      setTimeout(() => { el.style.display = 'none'; }, 3000);
    } else {
      el.innerHTML = `${baseMessage}<br><span class="countdown-timer">⏳ Kalan süre: <strong>${remaining}</strong> saniye</span>`;
    }
  }, 1000);
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
  const email = document.getElementById('regEmail').value.trim();
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

  const data = await apiFetch(`${API}/register`, {
    method: 'POST',
    body: JSON.stringify({ username, email, password })
  });

  if (data.status === 'success') {
    showMsg('regMsg', data.message, 'success');
    setTimeout(() => show('login'), 1500);
  } else {
    showMsg('regMsg', data.message, 'error');
  }
}

/* ---------- GİRİŞ YAP ---------- */

async function login() {
  const username = document.getElementById('loginUser').value.trim();
  const password = document.getElementById('loginPass').value;

  if (!username || !password) {
    return showMsg('msg', 'Kullanıcı adı ve şifre girin!', 'error');
  }

  const data = await apiFetch(`${API}/login`, {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });

  if (data.status === 'success') {
    sessionStorage.setItem('currentUser', JSON.stringify(data.user));
    showMsg('msg', data.message, 'success');
    setTimeout(() => {
      if (data.user.role === 'admin') {
        window.location.href = 'dashboard.html';
      } else {
        window.location.href = 'user.html';
      }
    }, 1000);
  } else if (data.status === 'requires_reset') {
    showMsg('msg', data.message, 'error');
    setTimeout(() => show('forgot'), 2000);
  } else if (data.locked && data.remaining_seconds > 0) {
    // Kilitli hesap — geri sayım başlat
    startCountdown('msg', data.remaining_seconds, data.message);
  } else {
    showMsg('msg', data.message, 'error');
  }
}

/* ---------- ŞİFREMİ UNUTTUM ---------- */

async function sendCode() {
  const email = document.getElementById('email').value.trim();
  if (!email) return showMsg('forgotMsg', 'E-posta adresinizi girin!', 'error');

  const data = await apiFetch(`${API}/send-code`, {
    method: 'POST',
    body: JSON.stringify({ email })
  });

  showMsg('forgotMsg', data.message, data.status === 'success' ? 'success' : 'error');
}

async function resetPass() {
  const email = document.getElementById('email').value.trim();
  const code = document.getElementById('code').value.trim();
  const newPass = document.getElementById('newPass').value;

  if (!email || !code || !newPass) {
    return showMsg('forgotMsg', 'Tüm alanları doldurun!', 'error');
  }
  if (newPass.length < 6) {
    return showMsg('forgotMsg', 'Yeni şifre en az 6 karakter olmalı!', 'error');
  }

  const data = await apiFetch(`${API}/reset-password`, {
    method: 'POST',
    body: JSON.stringify({ email, code, newPassword: newPass })
  });

  if (data.status === 'success') {
    showMsg('forgotMsg', data.message, 'success');
    setTimeout(() => show('login'), 1500);
  } else {
    showMsg('forgotMsg', data.message, 'error');
  }
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

async function loadDashboard() {
  const el = document.getElementById('userInfo');
  if (!el) return;

  const raw = sessionStorage.getItem('currentUser');
  if (!raw) {
    window.location.href = 'index.html';
    return;
  }

  const cur = JSON.parse(raw);

  if (cur.role !== 'admin') {
    window.location.href = 'user.html';
    return;
  }

  // Backend'den istatistikleri çek
  const stats = await apiFetch(`${API}/dashboard/stats`);
  const userLogs = await apiFetch(`${API}/dashboard/user-logs/${cur.username}`);
  const allLogs = await apiFetch(`${API}/dashboard/all-logs`);

  // Header bilgileri
  const welcomeEl = document.getElementById('welcomeUser');
  if (welcomeEl) welcomeEl.textContent = cur.username;
  const loginTimeEl = document.getElementById('loginTime');
  if (loginTimeEl) loginTimeEl.textContent = cur.loginTime;
  const loginIpEl = document.getElementById('loginIp');
  if (loginIpEl) loginIpEl.textContent = cur.ip;

  // İstatistik kartları
  const statCards = document.getElementById('statCards');
  if (statCards) {
    statCards.innerHTML = `
      <div class="stat-card">
        <div class="stat-number">${stats.allUsers}</div>
        <div class="stat-label">Toplam Kullanıcı</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">${stats.totalLogins}</div>
        <div class="stat-label">Toplam Giriş Denemesi</div>
      </div>
      <div class="stat-card stat-success">
        <div class="stat-number">${stats.successLogins}</div>
        <div class="stat-label">Başarılı Giriş</div>
      </div>
      <div class="stat-card stat-danger">
        <div class="stat-number">${stats.failedLogins}</div>
        <div class="stat-label">Başarısız Giriş</div>
      </div>
      <div class="stat-card stat-warning">
        <div class="stat-number">%${stats.failRate}</div>
        <div class="stat-label">Başarısızlık Oranı</div>
      </div>
      <div class="stat-card stat-danger">
        <div class="stat-number">${stats.lockedCount}</div>
        <div class="stat-label">Kilitli Hesap</div>
      </div>
    `;
  }

  // Top IP tablosu
  const topIPsEl = document.getElementById('topIPs');
  if (topIPsEl) {
    topIPsEl.innerHTML = stats.topIPs.map(r => `
      <tr>
        <td>${r.ip}</td>
        <td>${r.total}</td>
        <td class="text-danger">${r.failed}</td>
      </tr>
    `).join('');
  }

  // Kullanıcının kendi logları
  const logTable = document.getElementById('logTable');
  if (logTable) {
    logTable.innerHTML = userLogs.map(l => `
      <tr>
        <td>${l.time}</td>
        <td>${l.ip}</td>
        <td><span class="badge ${l.status === 'success' ? 'badge-success' : 'badge-fail'}">${l.status === 'success' ? 'Başarılı' : 'Başarısız'}</span></td>
        <td>${l.reason || '-'}</td>
      </tr>
    `).join('');
  }

  // Tüm sistem logları
  const allLogTable = document.getElementById('allLogTable');
  if (allLogTable) {
    allLogTable.innerHTML = allLogs.map(l => `
      <tr>
        <td>${l.username}</td>
        <td>${l.time}</td>
        <td>${l.ip}</td>
        <td><span class="badge ${l.status === 'success' ? 'badge-success' : 'badge-fail'}">${l.status === 'success' ? 'Başarılı' : 'Başarısız'}</span></td>
        <td>${l.reason || '-'}</td>
      </tr>
    `).join('');
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
    const results = document.getElementById('filterResults');
    if (results && results.innerHTML === '') applyFilter();
  }
}

/* ---------- LOG FİLTRELEME ---------- */

async function applyFilter() {
  const username = (document.getElementById('filterUser')?.value || '').trim();
  const ip = (document.getElementById('filterIP')?.value || '').trim();
  const dateStart = document.getElementById('filterDateStart')?.value || '';
  const dateEnd = document.getElementById('filterDateEnd')?.value || '';
  const status = document.getElementById('filterStatus')?.value || '';

  const params = new URLSearchParams();
  if (username) params.set('username', username);
  if (ip) params.set('ip', ip);
  if (dateStart) params.set('dateStart', dateStart);
  if (dateEnd) params.set('dateEnd', dateEnd);
  if (status) params.set('status', status);

  const filtered = await apiFetch(`${API}/dashboard/filter-logs?${params.toString()}`);

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
          <td>${l.time}</td>
          <td>${l.ip}</td>
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

async function loadReports() {
  const data = await apiFetch(`${API}/dashboard/reports`);
  const stats = await apiFetch(`${API}/dashboard/stats`);

  // --- Genel İstatistik Kartları ---
  const reportStats = document.getElementById('reportStats');
  if (reportStats) {
    reportStats.innerHTML = `
      <div class="report-stat-card">
        <div class="report-stat-icon">📊</div>
        <div class="report-stat-value">${stats.totalLogins}</div>
        <div class="report-stat-label">Toplam Giriş Denemesi</div>
      </div>
      <div class="report-stat-card rsc-success">
        <div class="report-stat-icon">✅</div>
        <div class="report-stat-value">${stats.successLogins}</div>
        <div class="report-stat-label">Başarılı Giriş</div>
      </div>
      <div class="report-stat-card rsc-danger">
        <div class="report-stat-icon">❌</div>
        <div class="report-stat-value">${stats.failedLogins}</div>
        <div class="report-stat-label">Başarısız Giriş</div>
      </div>
      <div class="report-stat-card rsc-warning">
        <div class="report-stat-icon">📉</div>
        <div class="report-stat-value">%${stats.failRate}</div>
        <div class="report-stat-label">Başarısızlık Oranı</div>
      </div>
      <div class="report-stat-card rsc-danger">
        <div class="report-stat-icon">🔒</div>
        <div class="report-stat-value">${stats.lockedCount}</div>
        <div class="report-stat-label">Kilitli Hesap</div>
      </div>
      <div class="report-stat-card rsc-info">
        <div class="report-stat-icon">👥</div>
        <div class="report-stat-value">${stats.allUsers}</div>
        <div class="report-stat-label">Toplam Kullanıcı</div>
      </div>
    `;
  }

  // --- Son 7 Günlük Dağılım (Bar Chart) ---
  const dailyChart = document.getElementById('dailyChart');
  if (dailyChart) {
    // Son 7 gün map
    const dayMap = {};
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      dayMap[key] = { success: 0, failed: 0 };
    }

    data.daily.forEach(d => {
      if (dayMap[d.date]) {
        dayMap[d.date].success = d.success || 0;
        dayMap[d.date].failed = d.failed || 0;
      }
    });

    const maxVal = Math.max(1, ...Object.values(dayMap).map(d => d.success + d.failed));

    dailyChart.innerHTML = `
      <div class="bar-chart">
        ${Object.entries(dayMap).map(([date, dd]) => {
      const total = dd.success + dd.failed;
      const successPct = (dd.success / maxVal) * 100;
      const failedPct = (dd.failed / maxVal) * 100;
      const dayLabel = date.slice(5);
      return `
            <div class="bar-column">
              <div class="bar-value">${total}</div>
              <div class="bar-stack" style="height: 160px;">
                <div class="bar-segment bar-failed" style="height: ${failedPct}%;" title="Başarısız: ${dd.failed}"></div>
                <div class="bar-segment bar-success" style="height: ${successPct}%;" title="Başarılı: ${dd.success}"></div>
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
    data.hourly.forEach(h => { hourMap[h.hour] = h.count; });

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
    if (data.riskyUsers.length === 0) {
      riskyUsers.innerHTML = `<tr><td colspan="5" style="text-align:center; opacity:0.5; padding:24px;">Başarısız giriş kaydı yok.</td></tr>`;
    } else {
      riskyUsers.innerHTML = data.riskyUsers.map((u, i) => `
        <tr>
          <td>${i + 1}</td>
          <td>${u.username}</td>
          <td>${u.email}</td>
          <td class="text-danger">${u.failCount}</td>
          <td>${u.isLocked
          ? '<span class="badge badge-fail">🔒 Kilitli</span>'
          : '<span class="badge badge-success">✅ Aktif</span>'
        }</td>
        </tr>
      `).join('');
    }
  }

  // --- IP Bar Grafikleri ---
  const ipBars = document.getElementById('ipBars');
  if (ipBars) {
    const maxIP = data.topIPs.length > 0 ? data.topIPs[0].total : 1;
    ipBars.innerHTML = data.topIPs.map(r => {
      const totalPct = (r.total / maxIP) * 100;
      const failPct = (r.failed / maxIP) * 100;
      return `
        <div class="ip-bar-row">
          <div class="ip-bar-label">${r.ip}</div>
          <div class="ip-bar-track">
            <div class="ip-bar-fill ip-bar-total" style="width: ${totalPct}%;">
              <span>${r.total} deneme</span>
            </div>
            <div class="ip-bar-fill ip-bar-failed" style="width: ${failPct}%;">
              <span>${r.failed} başarısız</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  // --- Kilitli Hesaplar ---
  const lockedAccounts = document.getElementById('lockedAccounts');
  const noLockedMsg = document.getElementById('noLockedMsg');
  if (lockedAccounts) {
    if (data.lockedAccounts.length === 0) {
      lockedAccounts.innerHTML = '';
      if (noLockedMsg) noLockedMsg.style.display = 'block';
    } else {
      if (noLockedMsg) noLockedMsg.style.display = 'none';
      lockedAccounts.innerHTML = data.lockedAccounts.map(u => `
        <tr>
          <td>${u.username}</td>
          <td>${u.email}</td>
          <td class="text-danger">${u.failedAttempts}</td>
          <td>${u.lockUntil || '—'}</td>
        </tr>
      `).join('');
    }
  }
}

async function clearAllLogs() {
  if (!confirm('Tüm loglar silinecek! Emin misiniz?')) return;

  const data = await apiFetch(`${API}/dashboard/clear-logs`, { method: 'POST' });
  alert(data.message);

  loadDashboard();
  loadReports();
  const filterResults = document.getElementById('filterResults');
  if (filterResults) filterResults.innerHTML = '';
  const filterCount = document.getElementById('filterCount');
  if (filterCount) filterCount.textContent = '0 kayıt bulundu';
}

function logout() {
  sessionStorage.removeItem('currentUser');
  window.location.href = 'index.html';
}

/* ---------- SAYFA YÜKLENME ---------- */

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('userInfo')) {
    loadDashboard();
    loadReports();
  }

  if (document.getElementById('userPanelName')) {
    loadUserPanel();
  }
});
