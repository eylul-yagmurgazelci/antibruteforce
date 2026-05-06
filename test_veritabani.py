"""
Siber Güvenlik Projesi — Veritabanı Test Script'i
4_kisi_veritabani_loglama.sql dosyasındaki tüm SQL'leri çalıştırır ve test eder.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "siber_guvenlik_test.db")

# Eğer eski test DB'si varsa sil (temiz başlangıç)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("🗑️  Eski test veritabanı silindi.\n")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON;")  # Foreign key desteğini aç
cur = conn.cursor()

SEPARATOR = "=" * 65

def baslik(text):
    print(f"\n{SEPARATOR}")
    print(f"  {text}")
    print(SEPARATOR)

def tablo_yazdir(rows, headers):
    """Basit tablo çıktısı"""
    if not rows:
        print("  (sonuç yok)")
        return
    # Sütun genişliklerini hesapla
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val) if val is not None else "NULL"))
    
    # Header
    header_line = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
    print(f"  {header_line}")
    print(f"  {'-+-'.join('-' * w for w in col_widths)}")
    
    # Rows
    for row in rows:
        line = " | ".join(
            str(val if val is not None else "NULL").ljust(col_widths[i])
            for i, val in enumerate(row)
        )
        print(f"  {line}")
    print(f"  → {len(rows)} satır döndü")


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 1: TABLO OLUŞTURMA
# ═══════════════════════════════════════════════════════════════
baslik("BÖLÜM 1: TABLO OLUŞTURMA")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    email           VARCHAR(100) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    is_locked       BOOLEAN      DEFAULT FALSE,
    failed_attempts INTEGER      DEFAULT 0,
    lock_until      DATETIME     DEFAULT NULL
);
""")
print("✅ users tablosu oluşturuldu.")

cur.execute("""
CREATE TABLE IF NOT EXISTS login_logs (
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER      NOT NULL,
    ip_address   VARCHAR(45)  NOT NULL,
    attempt_time DATETIME     DEFAULT CURRENT_TIMESTAMP,
    status       VARCHAR(10)  NOT NULL CHECK (status IN ('success', 'failed')),
    reason       VARCHAR(255) DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
""")
print("✅ login_logs tablosu oluşturuldu.")

cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_user_id   ON login_logs(user_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_ip        ON login_logs(ip_address);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_time      ON login_logs(attempt_time);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
print("✅ İndeksler oluşturuldu.")
conn.commit()


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 8 (önce): TEST VERİSİ EKLEME
# ═══════════════════════════════════════════════════════════════
baslik("BÖLÜM 8: TEST VERİSİ EKLEME")

cur.executemany(
    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?);",
    [
        ('ahmet_y',  'ahmet@test.com',  '$2b$12$ORNEKHASHDEGERIXYZ001'),
        ('elif_k',   'elif@test.com',   '$2b$12$ORNEKHASHDEGERIXYZ002'),
        ('mehmet_d', 'mehmet@test.com',  '$2b$12$ORNEKHASHDEGERIXYZ003'),
        ('admin',    'admin@test.com',   '$2b$12$ORNEKHASHDEGERIXYZ004'),
    ]
)
print("✅ 4 kullanıcı eklendi.")

cur.executemany(
    "INSERT INTO login_logs (user_id, ip_address, status, reason) VALUES (?, ?, ?, ?);",
    [
        (1, '192.168.1.10', 'failed',  'Wrong password'),
        (1, '192.168.1.10', 'failed',  'Wrong password'),
        (1, '192.168.1.10', 'failed',  'Wrong password'),
        (1, '192.168.1.10', 'failed',  'Wrong password'),
        (1, '192.168.1.10', 'failed',  'Wrong password'),
        (2, '10.0.0.5',     'success', None),
        (3, '172.16.0.1',   'failed',  'Account locked'),
        (4, '192.168.1.99', 'success', None),
    ]
)
print("✅ 8 log kaydı eklendi.")
conn.commit()


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 2: KULLANICI KAYIT VE GİRİŞ İŞLEMLERİ
# ═══════════════════════════════════════════════════════════════
baslik("BÖLÜM 2: KULLANICI SORGULAMA")

print("\n📌 2.2 — Kullanıcı adıyla sorgula (username = 'ahmet_y'):")
cur.execute("""
    SELECT id, username, password_hash, is_locked, failed_attempts, lock_until
    FROM   users
    WHERE  username = ?;
""", ('ahmet_y',))
tablo_yazdir(cur.fetchall(), ['id', 'username', 'password_hash', 'is_locked', 'failed_attempts', 'lock_until'])

print("\n📌 2.3 — E-posta ile sorgula (email = 'elif@test.com'):")
cur.execute("""
    SELECT id, username, password_hash, is_locked, failed_attempts, lock_until
    FROM   users
    WHERE  email = ?;
""", ('elif@test.com',))
tablo_yazdir(cur.fetchall(), ['id', 'username', 'password_hash', 'is_locked', 'failed_attempts', 'lock_until'])


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3: LOG SİSTEMİ TESTİ
# ═══════════════════════════════════════════════════════════════
baslik("BÖLÜM 3: LOG SİSTEMİ TESTİ")

# Başarılı giriş logu ekle
cur.execute("INSERT INTO login_logs (user_id, ip_address, status) VALUES (?, ?, 'success');", (1, '192.168.1.10'))
print("✅ 3.1 — Başarılı giriş logu eklendi (user_id=1)")

# Başarısız giriş logu ekle
cur.execute("INSERT INTO login_logs (user_id, ip_address, status, reason) VALUES (?, ?, 'failed', ?);",
            (2, '10.0.0.5', 'Wrong password'))
print("✅ 3.2 — Başarısız giriş logu eklendi (user_id=2, reason='Wrong password')")
conn.commit()


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 4: HESAP KİLİTLEME SİSTEMİ
# ═══════════════════════════════════════════════════════════════
baslik("BÖLÜM 4: HESAP KİLİTLEME SİSTEMİ")

# 4.1 Başarısız giriş sayacını artır (ahmet_y - 5 kez yanlış girdi)
for i in range(5):
    cur.execute("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?;", (1,))
print("✅ 4.1 — ahmet_y için failed_attempts 5 kez artırıldı")

# 4.2 Hesabı kilitle
cur.execute("""
    UPDATE users
    SET    is_locked  = TRUE,
           lock_until = DATETIME('now', '+10 minutes')
    WHERE  id = ?;
""", (1,))
print("✅ 4.2 — ahmet_y hesabı 10 dakika süreyle kilitlendi")

# Kontrol: ahmet_y'nin durumu
cur.execute("SELECT username, is_locked, failed_attempts, lock_until FROM users WHERE id = 1;")
tablo_yazdir(cur.fetchall(), ['username', 'is_locked', 'failed_attempts', 'lock_until'])

# 4.3 Başarılı girişten sonra sıfırlama (elif_k için)
cur.execute("""
    UPDATE users
    SET    failed_attempts = 0,
           is_locked       = FALSE,
           lock_until      = NULL
    WHERE  id = ?;
""", (2,))
print("\n✅ 4.3 — elif_k için sayaç sıfırlandı ve kilit kaldırıldı")

# 4.5 Kilitli mi kontrol
print("\n📌 4.5 — ahmet_y kilitli mi?")
cur.execute("SELECT is_locked, lock_until FROM users WHERE id = ?;", (1,))
tablo_yazdir(cur.fetchall(), ['is_locked', 'lock_until'])
conn.commit()


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 5: ADMIN PANELİ İÇİN VERİ SAĞLAMA
# ═══════════════════════════════════════════════════════════════
baslik("BÖLÜM 5: ADMIN PANELİ SORGULARI")

print("\n📌 5.1 — Tüm kullanıcılar:")
cur.execute("""
    SELECT id, username, email, created_at, is_locked, failed_attempts, lock_until
    FROM   users
    ORDER  BY created_at DESC;
""")
tablo_yazdir(cur.fetchall(),
             ['id', 'username', 'email', 'created_at', 'is_locked', 'failed_attempts', 'lock_until'])

print("\n📌 5.2 — Kilitli hesaplar:")
cur.execute("""
    SELECT id, username, email, failed_attempts, lock_until
    FROM   users
    WHERE  is_locked = TRUE
    ORDER  BY lock_until DESC;
""")
tablo_yazdir(cur.fetchall(), ['id', 'username', 'email', 'failed_attempts', 'lock_until'])

print("\n📌 5.3 — Aktif (kilitli olmayan) kullanıcılar:")
cur.execute("""
    SELECT id, username, email, created_at
    FROM   users
    WHERE  is_locked = FALSE
    ORDER  BY username ASC;
""")
tablo_yazdir(cur.fetchall(), ['id', 'username', 'email', 'created_at'])

print("\n📌 5.4 — ahmet_y'nin tüm log geçmişi:")
cur.execute("""
    SELECT ll.log_id, ll.ip_address, ll.attempt_time, ll.status, ll.reason
    FROM   login_logs ll
    JOIN   users      u ON ll.user_id = u.id
    WHERE  u.username = ?
    ORDER  BY ll.attempt_time DESC;
""", ('ahmet_y',))
tablo_yazdir(cur.fetchall(), ['log_id', 'ip_address', 'attempt_time', 'status', 'reason'])


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 6: LOG FİLTRELEME
# ═══════════════════════════════════════════════════════════════
baslik("BÖLÜM 6: LOG FİLTRELEME")

print("\n📌 6.1 — Son 24 saat logları:")
cur.execute("""
    SELECT ll.log_id, u.username, ll.ip_address, ll.attempt_time, ll.status, ll.reason
    FROM   login_logs ll
    JOIN   users      u ON ll.user_id = u.id
    WHERE  ll.attempt_time >= DATETIME('now', '-1 day')
    ORDER  BY ll.attempt_time DESC;
""")
tablo_yazdir(cur.fetchall(), ['log_id', 'username', 'ip_address', 'attempt_time', 'status', 'reason'])

print("\n📌 6.4 — IP adresine göre (192.168.1.10):")
cur.execute("""
    SELECT ll.log_id, u.username, ll.attempt_time, ll.status, ll.reason
    FROM   login_logs ll
    JOIN   users      u ON ll.user_id = u.id
    WHERE  ll.ip_address = ?
    ORDER  BY ll.attempt_time DESC;
""", ('192.168.1.10',))
tablo_yazdir(cur.fetchall(), ['log_id', 'username', 'attempt_time', 'status', 'reason'])

print("\n📌 6.5 — Yalnızca başarısız girişler:")
cur.execute("""
    SELECT ll.log_id, u.username, ll.ip_address, ll.attempt_time, ll.reason
    FROM   login_logs ll
    JOIN   users      u ON ll.user_id = u.id
    WHERE  ll.status = 'failed'
    ORDER  BY ll.attempt_time DESC;
""")
tablo_yazdir(cur.fetchall(), ['log_id', 'username', 'ip_address', 'attempt_time', 'reason'])

print("\n📌 6.6 — Yalnızca başarılı girişler:")
cur.execute("""
    SELECT ll.log_id, u.username, ll.ip_address, ll.attempt_time
    FROM   login_logs ll
    JOIN   users      u ON ll.user_id = u.id
    WHERE  ll.status = 'success'
    ORDER  BY ll.attempt_time DESC;
""")
tablo_yazdir(cur.fetchall(), ['log_id', 'username', 'ip_address', 'attempt_time'])


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 7: RAPORLAMA SORGULARI
# ═══════════════════════════════════════════════════════════════
baslik("BÖLÜM 7: RAPORLAMA SORGULARI")

print("\n📌 7.1 — Genel özet istatistikler:")
cur.execute("""
    SELECT
        COUNT(*)                                                AS toplam_deneme,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)    AS basarili,
        SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END)    AS basarisiz,
        ROUND(
            100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
            / COUNT(*), 2
        )                                                       AS basarisizlik_yuzdesi
    FROM login_logs;
""")
tablo_yazdir(cur.fetchall(), ['toplam_deneme', 'basarili', 'basarisiz', 'basarisizlik_yuzde'])

print("\n📌 7.2 — En çok başarısız giriş yaşayan kullanıcılar (Top 10):")
cur.execute("""
    SELECT
        u.username,
        u.email,
        u.is_locked,
        COUNT(ll.log_id) AS basarisiz_giris_sayisi
    FROM   login_logs ll
    JOIN   users      u ON ll.user_id = u.id
    WHERE  ll.status = 'failed'
    GROUP  BY u.id, u.username, u.email, u.is_locked
    ORDER  BY basarisiz_giris_sayisi DESC
    LIMIT  10;
""")
tablo_yazdir(cur.fetchall(), ['username', 'email', 'is_locked', 'basarisiz_giris'])

print("\n📌 7.3 — En çok saldırı gelen IP adresleri (Top 5):")
cur.execute("""
    SELECT
        ip_address,
        COUNT(*)                                                AS deneme_sayisi,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)     AS basarisiz_sayisi
    FROM   login_logs
    GROUP  BY ip_address
    ORDER  BY deneme_sayisi DESC
    LIMIT  5;
""")
tablo_yazdir(cur.fetchall(), ['ip_address', 'deneme_sayisi', 'basarisiz_sayisi'])

print("\n📌 7.4 — Son 24 saatlik özet:")
cur.execute("""
    SELECT
        COUNT(*)                                                 AS son_24s_toplam,
        SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END)     AS son_24s_basarisiz,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)     AS son_24s_basarili
    FROM login_logs
    WHERE attempt_time >= DATETIME('now', '-1 day');
""")
tablo_yazdir(cur.fetchall(), ['son_24s_toplam', 'son_24s_basarisiz', 'son_24s_basarili'])

print("\n📌 7.5 — Son 7 günlük günlük dağılım:")
cur.execute("""
    SELECT
        DATE(attempt_time) AS tarih,
        COUNT(*)           AS toplam_deneme,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS basarisiz
    FROM   login_logs
    WHERE  attempt_time >= DATETIME('now', '-7 days')
    GROUP  BY DATE(attempt_time)
    ORDER  BY tarih DESC;
""")
tablo_yazdir(cur.fetchall(), ['tarih', 'toplam_deneme', 'basarisiz'])

print("\n📌 7.6 — Şu an kilitli hesap sayısı:")
cur.execute("SELECT COUNT(*) AS kilitli_hesap_sayisi FROM users WHERE is_locked = TRUE;")
tablo_yazdir(cur.fetchall(), ['kilitli_hesap_sayisi'])


# ═══════════════════════════════════════════════════════════════
# SONUÇ
# ═══════════════════════════════════════════════════════════════
baslik("✅ TÜM TESTLER TAMAMLANDI")
print(f"\n  Veritabanı dosyası: {DB_PATH}")
print(f"  Toplam kullanıcı  : {cur.execute('SELECT COUNT(*) FROM users').fetchone()[0]}")
print(f"  Toplam log kaydı  : {cur.execute('SELECT COUNT(*) FROM login_logs').fetchone()[0]}")
print()

conn.close()
