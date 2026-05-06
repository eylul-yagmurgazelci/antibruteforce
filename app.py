"""
Siber Güvenlik Projesi — Flask Backend
eylül.sql şemasını gerçek SQLite veritabanı ile kullanır.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import bcrypt
import os
from datetime import datetime, timedelta, timezone

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# Kademeli kilitleme sureleri (saniye) — demo/sunum icin saniye cinsinden
LOCK_DURATIONS = [5, 10, 20, 40, 60]  # 1.=5sn, 2.=10sn, 3.=20sn, 4.=40sn, 5.=60sn
# 5. kilitin suresi dolunca -> sifre sifirlama zorunlu

DB_PATH = os.path.join(os.path.dirname(__file__), "siber_guvenlik.db")


# ═══════════════════════════════════════════════════════════════
# YARDIMCI: UTC şimdiki zaman
# ═══════════════════════════════════════════════════════════════

def utcnow():
    """SQLite CURRENT_TIMESTAMP ile uyumlu UTC zaman"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ═══════════════════════════════════════════════════════════════
# VERİTABANI YARDIMCI FONKSİYONLARI
# ═══════════════════════════════════════════════════════════════

def get_db():
    """Veritabanı bağlantısı al"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row  # dict-like erişim
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")  # Concurrent read/write
    return conn


def init_db():
    """eylül.sql şemasını kullanarak tabloları oluştur"""
    conn = get_db()
    cur = conn.cursor()

    # TABLO: users (kademeli kilitleme destekli)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        username        VARCHAR(50)  NOT NULL UNIQUE,
        email           VARCHAR(100) NOT NULL UNIQUE,
        password_hash   VARCHAR(255) NOT NULL,
        created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
        is_locked       BOOLEAN      DEFAULT FALSE,
        failed_attempts INTEGER      DEFAULT 0,
        lock_until      DATETIME     DEFAULT NULL,
        lock_count      INTEGER      DEFAULT 0,
        requires_reset  BOOLEAN      DEFAULT FALSE
    );
    """)

    # Mevcut tabloya yeni sutunlari ekle (migration)
    for col, definition in [
        ("lock_count",     "INTEGER DEFAULT 0"),
        ("requires_reset", "BOOLEAN DEFAULT FALSE"),
    ]:
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass  # Sutun zaten var

    # TABLO: login_logs
    # FIX: user_id NULL kabul ediyor (bilinmeyen kullanici girisimleri icin)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS login_logs (
        log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER      DEFAULT NULL,
        ip_address   VARCHAR(45)  NOT NULL,
        attempt_time DATETIME     DEFAULT CURRENT_TIMESTAMP,
        status       VARCHAR(10)  NOT NULL CHECK (status IN ('success', 'failed')),
        reason       VARCHAR(255) DEFAULT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    # İNDEKSLER (eylül.sql)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_user_id   ON login_logs(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_ip        ON login_logs(ip_address);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_time      ON login_logs(attempt_time);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")

    conn.commit()

    # Varsayılan admin kullanıcısı
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("admin", "admin@test.com", hashed.decode())
        )
        conn.commit()
        print("[OK] Varsayilan admin kullanicisi olusturuldu (admin / admin123)")

    conn.close()


def check_and_unlock_expired():
    """Suresi dolmus kilitleri otomatik ac — kademeli kilitleme destekli"""
    conn = get_db()

    # 1-4. kilit: suresi dolunca kilidi ac (lock_count korunur)
    conn.execute("""
        UPDATE users
        SET    is_locked       = FALSE,
               lock_until      = NULL,
               failed_attempts = 0
        WHERE  is_locked = TRUE
          AND  requires_reset = FALSE
          AND  lock_count < ?
          AND  lock_until IS NOT NULL
          AND  lock_until < CURRENT_TIMESTAMP;
    """, (len(LOCK_DURATIONS),))

    # 5. kilit (60 dk): suresi dolunca -> sifre sifirlama zorunlu yap
    conn.execute("""
        UPDATE users
        SET    requires_reset = TRUE,
               lock_until     = NULL
        WHERE  is_locked = TRUE
          AND  requires_reset = FALSE
          AND  lock_count >= ?
          AND  lock_until IS NOT NULL
          AND  lock_until < CURRENT_TIMESTAMP;
    """, (len(LOCK_DURATIONS),))

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# SAYFA YÖNLENDİRME
# ═══════════════════════════════════════════════════════════════

@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(".", filename)


# ═══════════════════════════════════════════════════════════════
# API: KAYIT OL
# ═══════════════════════════════════════════════════════════════

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Veri alınamadı"}), 400

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "Tüm alanları doldurun!"}), 400
    if len(password) < 6:
        return jsonify({"status": "error", "message": "Şifre en az 6 karakter olmalı!"}), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cur.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Bu kullanıcı adı zaten alınmış!"}), 409

    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cur.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Bu e-posta zaten kayıtlı!"}), 409

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    cur.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, hashed.decode())
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Kayıt başarılı! Giriş yapabilirsiniz."}), 201


# ═══════════════════════════════════════════════════════════════
# API: GİRİŞ YAP
# ═══════════════════════════════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def login():
    check_and_unlock_expired()

    data = request.get_json()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    ip = request.remote_addr or "127.0.0.1"

    if not username or not password:
        return jsonify({"status": "error", "message": "Kullanıcı adı ve şifre girin!"}), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, email, password_hash, is_locked, failed_attempts,
               lock_until, lock_count, requires_reset
        FROM users WHERE username = ?
    """, (username,))
    user = cur.fetchone()

    if not user:
        # FIX: user_id NULL olarak loglanıyor (0 değil — foreign key ihlali önlendi)
        cur.execute(
            "INSERT INTO login_logs (user_id, ip_address, status, reason) VALUES (NULL, ?, 'failed', ?)",
            (ip, "User not found")
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "error", "message": "Kullanici bulunamadi!"}), 404

    # Kalici kilit kontrolu — sifre degistirme zorunlu
    if user["requires_reset"]:
        cur.execute(
            "INSERT INTO login_logs (user_id, ip_address, status, reason) VALUES (?, ?, 'failed', ?)",
            (user["id"], ip, "Requires password reset")
        )
        conn.commit()
        conn.close()
        return jsonify({
            "status": "requires_reset",
            "message": "Kilitleme suresi doldu! Hesabiniza giris yapabilmek icin sifrenizi sifirlamaniz gerekmektedir."
        }), 403

    # Hesap kilitli mi? (sureli kilit)
    if user["is_locked"]:
        if user["lock_until"]:
            lock_end = datetime.fromisoformat(user["lock_until"])
            # FIX: UTC farkı giderildi
            now = utcnow()
            remaining_total = max(0, int((lock_end - now).total_seconds()))
            remaining_sec = remaining_total
        else:
            remaining_sec = 0
        cur.execute(
            "INSERT INTO login_logs (user_id, ip_address, status, reason) VALUES (?, ?, 'failed', ?)",
            (user["id"], ip, "Account locked")
        )
        conn.commit()
        conn.close()

        lock_num = user["lock_count"] or 0
        return jsonify({
            "status": "error",
            "locked": True,
            "remaining_seconds": remaining_sec,
            "message": f"Hesap kilitli! ({lock_num}. kilitleme) {remaining_sec} saniye sonra tekrar deneyin."
        }), 403

    # Sifre kontrolu
    if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        # Basarili giris — tum sayaclari sifirla
        cur.execute("""
            UPDATE users
            SET    failed_attempts = 0,
                   is_locked       = FALSE,
                   lock_until      = NULL,
                   lock_count      = 0,
                   requires_reset  = FALSE
            WHERE  id = ?
        """, (user["id"],))

        cur.execute(
            "INSERT INTO login_logs (user_id, ip_address, status) VALUES (?, ?, 'success')",
            (user["id"], ip)
        )
        conn.commit()
        conn.close()

        role = "admin" if user["username"] == "admin" else "user"
        return jsonify({
            "status": "success",
            "message": "Giris basarili! Yonlendiriliyorsunuz...",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "loginTime": utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "ip": ip,
                "role": role
            }
        })
    else:
        # Basarisiz giris — sayac artir
        new_attempts = user["failed_attempts"] + 1
        cur.execute(
            "UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?",
            (user["id"],)
        )
        cur.execute(
            "INSERT INTO login_logs (user_id, ip_address, status, reason) VALUES (?, ?, 'failed', ?)",
            (user["id"], ip, "Wrong password")
        )

        # 5 yanlis giris → kademeli kilitleme
        if new_attempts >= 5:
            current_lock_count = (user["lock_count"] or 0) + 1

            lock_index = min(current_lock_count, len(LOCK_DURATIONS)) - 1
            lock_seconds = LOCK_DURATIONS[lock_index]
            # FIX: UTC kullanılıyor — saniye cinsinden kilitleme
            lock_until = (utcnow() + timedelta(seconds=lock_seconds)).strftime("%Y-%m-%d %H:%M:%S")

            cur.execute("""
                UPDATE users
                SET    is_locked       = TRUE,
                       lock_until      = ?,
                       lock_count      = ?,
                       failed_attempts = 0
                WHERE  id = ?
            """, (lock_until, current_lock_count, user["id"]))

            conn.commit()
            conn.close()

            if current_lock_count >= len(LOCK_DURATIONS):
                return jsonify({
                    "status": "error",
                    "locked": True,
                    "remaining_seconds": lock_seconds,
                    "message": f"Hesap kilitlendi! ({current_lock_count}. kilitleme - SON) {lock_seconds} saniye bekleyin. Sure doldugunda sifre sifirlama gerekecek."
                }), 403
            else:
                return jsonify({
                    "status": "error",
                    "locked": True,
                    "remaining_seconds": lock_seconds,
                    "message": f"Hesap kilitlendi! ({current_lock_count}. kilitleme) {lock_seconds} saniye bekleyin."
                }), 403

        conn.commit()
        conn.close()
        return jsonify({
            "status": "error",
            "message": f"Sifre yanlis! ({new_attempts}/5 deneme)"
        }), 401


# ═══════════════════════════════════════════════════════════════
# API: ŞİFREMİ UNUTTUM
# ═══════════════════════════════════════════════════════════════

reset_codes = {}  # { email: { code, expires } }

@app.route("/api/send-code", methods=["POST"])
def send_code():
    data = request.get_json()
    email = (data.get("email") or "").strip()
    if not email:
        return jsonify({"status": "error", "message": "E-posta adresinizi girin!"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    if not cur.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Bu e-posta kayıtlı değil!"}), 404
    conn.close()

    import random
    code = str(random.randint(100000, 999999))
    reset_codes[email] = {"code": code, "expires": utcnow() + timedelta(minutes=5)}

    return jsonify({
        "status": "success",
        "message": f"Doğrulama kodu: {code} (5 dk geçerli)"
    })


@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = (data.get("email") or "").strip()
    code = (data.get("code") or "").strip()
    new_pass = data.get("newPassword") or ""

    if not email or not code or not new_pass:
        return jsonify({"status": "error", "message": "Tüm alanları doldurun!"}), 400
    if len(new_pass) < 6:
        return jsonify({"status": "error", "message": "Yeni şifre en az 6 karakter olmalı!"}), 400

    entry = reset_codes.get(email)
    if not entry:
        return jsonify({"status": "error", "message": "Önce doğrulama kodu gönderin!"}), 400
    if utcnow() > entry["expires"]:
        return jsonify({"status": "error", "message": "Kodun süresi dolmuş! Tekrar gönderin."}), 400
    if entry["code"] != code:
        return jsonify({"status": "error", "message": "Kod yanlış!"}), 400

    hashed = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt())
    conn = get_db()
    conn.execute("""
        UPDATE users
        SET    password_hash   = ?,
               failed_attempts = 0,
               is_locked       = FALSE,
               lock_until      = NULL,
               lock_count      = 0,
               requires_reset  = FALSE
        WHERE  email = ?
    """, (hashed.decode(), email))
    conn.commit()
    conn.close()

    del reset_codes[email]
    return jsonify({"status": "success", "message": "Sifre degistirildi! Giris yapabilirsiniz."})


# ═══════════════════════════════════════════════════════════════
# API: DASHBOARD — TÜM KULLANICILAR
# ═══════════════════════════════════════════════════════════════

@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    check_and_unlock_expired()
    conn = get_db()
    cur = conn.cursor()

    all_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    locked_count = cur.execute(
        "SELECT COUNT(*) FROM users WHERE is_locked = TRUE"
    ).fetchone()[0]

    row = cur.execute("""
        SELECT
            COUNT(*)                                                AS toplam_deneme,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)   AS basarili,
            SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END)   AS basarisiz,
            ROUND(
                100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
                / MAX(COUNT(*), 1), 2
            )                                                       AS basarisizlik_yuzdesi
        FROM login_logs
    """).fetchone()

    top_ips = cur.execute("""
        SELECT
            ip_address,
            COUNT(*)                                            AS deneme_sayisi,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS basarisiz_sayisi
        FROM   login_logs
        GROUP  BY ip_address
        ORDER  BY deneme_sayisi DESC
        LIMIT  5
    """).fetchall()

    conn.close()

    return jsonify({
        "allUsers": all_users,
        "lockedCount": locked_count,
        "totalLogins": row[0] or 0,
        "successLogins": row[1] or 0,
        "failedLogins": row[2] or 0,
        "failRate": row[3] or 0,
        "topIPs": [{"ip": r[0], "total": r[1], "failed": r[2]} for r in top_ips]
    })


# ═══════════════════════════════════════════════════════════════
# API: KULLANICI LOG GEÇMİŞİ
# ═══════════════════════════════════════════════════════════════

@app.route("/api/dashboard/user-logs/<username>", methods=["GET"])
def user_logs(username):
    conn = get_db()
    rows = conn.execute("""
        SELECT ll.log_id, ll.ip_address, ll.attempt_time, ll.status, ll.reason
        FROM   login_logs ll
        JOIN   users      u ON ll.user_id = u.id
        WHERE  u.username = ?
        ORDER  BY ll.attempt_time DESC
        LIMIT 10
    """, (username,)).fetchall()
    conn.close()

    return jsonify([{
        "id": r[0], "ip": r[1], "time": r[2],
        "status": r[3], "reason": r[4]
    } for r in rows])


# ═══════════════════════════════════════════════════════════════
# API: TÜM SİSTEM LOGLARI
# ═══════════════════════════════════════════════════════════════

@app.route("/api/dashboard/all-logs", methods=["GET"])
def all_logs():
    conn = get_db()
    rows = conn.execute("""
        SELECT ll.log_id, u.username, ll.ip_address, ll.attempt_time, ll.status, ll.reason
        FROM   login_logs ll
        LEFT JOIN users u ON ll.user_id = u.id
        ORDER  BY ll.attempt_time DESC
        LIMIT 20
    """).fetchall()
    conn.close()

    return jsonify([{
        "id": r[0], "username": r[1] or "—", "ip": r[2],
        "time": r[3], "status": r[4], "reason": r[5]
    } for r in rows])


# ═══════════════════════════════════════════════════════════════
# API: LOG FİLTRELEME
# ═══════════════════════════════════════════════════════════════

@app.route("/api/dashboard/filter-logs", methods=["GET"])
def filter_logs():
    username = request.args.get("username", "").strip()
    ip = request.args.get("ip", "").strip()
    date_start = request.args.get("dateStart", "").strip()
    date_end = request.args.get("dateEnd", "").strip()
    status = request.args.get("status", "").strip()

    conn = get_db()

    query = """
        SELECT ll.log_id, u.username, ll.ip_address, ll.attempt_time, ll.status, ll.reason
        FROM   login_logs ll
        LEFT JOIN users u ON ll.user_id = u.id
        WHERE 1=1
    """
    params = []

    if username:
        query += " AND u.username LIKE ?"
        params.append(f"%{username}%")
    if ip:
        query += " AND ll.ip_address LIKE ?"
        params.append(f"%{ip}%")
    if date_start:
        query += " AND ll.attempt_time >= ?"
        params.append(date_start.replace("T", " "))
    if date_end:
        query += " AND ll.attempt_time <= ?"
        params.append(date_end.replace("T", " "))
    if status:
        query += " AND ll.status = ?"
        params.append(status)

    query += " ORDER BY ll.attempt_time DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([{
        "id": r[0], "username": r[1] or "—", "ip": r[2],
        "time": r[3], "status": r[4], "reason": r[5]
    } for r in rows])


# ═══════════════════════════════════════════════════════════════
# API: RAPORLAMA
# ═══════════════════════════════════════════════════════════════

@app.route("/api/dashboard/reports", methods=["GET"])
def reports():
    check_and_unlock_expired()
    conn = get_db()
    cur = conn.cursor()

    risky = cur.execute("""
        SELECT
            u.username, u.email, u.is_locked,
            COUNT(ll.log_id) AS basarisiz_giris_sayisi
        FROM   login_logs ll
        JOIN   users      u ON ll.user_id = u.id
        WHERE  ll.status = 'failed'
        GROUP  BY u.id, u.username, u.email, u.is_locked
        ORDER  BY basarisiz_giris_sayisi DESC
        LIMIT  10
    """).fetchall()

    top_ips = cur.execute("""
        SELECT
            ip_address,
            COUNT(*)                                            AS deneme_sayisi,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS basarisiz_sayisi
        FROM   login_logs
        GROUP  BY ip_address
        ORDER  BY deneme_sayisi DESC
        LIMIT  5
    """).fetchall()

    daily = cur.execute("""
        SELECT
            DATE(attempt_time) AS tarih,
            COUNT(*)           AS toplam_deneme,
            SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) AS basarisiz,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS basarili
        FROM   login_logs
        WHERE  attempt_time >= DATETIME('now', '-7 days')
        GROUP  BY DATE(attempt_time)
        ORDER  BY tarih DESC
    """).fetchall()

    hourly = cur.execute("""
        SELECT
            CAST(strftime('%H', attempt_time) AS INTEGER) AS saat,
            COUNT(*) AS sayi
        FROM   login_logs
        WHERE  DATE(attempt_time) = DATE('now')
          AND  status = 'failed'
        GROUP  BY saat
        ORDER  BY saat
    """).fetchall()

    locked = cur.execute("""
        SELECT id, username, email, failed_attempts, lock_until
        FROM   users
        WHERE  is_locked = TRUE
        ORDER  BY lock_until DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "riskyUsers": [{
            "username": r[0], "email": r[1],
            "isLocked": bool(r[2]), "failCount": r[3]
        } for r in risky],
        "topIPs": [{
            "ip": r[0], "total": r[1], "failed": r[2]
        } for r in top_ips],
        "daily": [{
            "date": r[0], "total": r[1], "failed": r[2], "success": r[3]
        } for r in daily],
        "hourly": [{
            "hour": r[0], "count": r[1]
        } for r in hourly],
        "lockedAccounts": [{
            "username": r[1], "email": r[2],
            "failedAttempts": r[3], "lockUntil": r[4]
        } for r in locked]
    })


# ═══════════════════════════════════════════════════════════════
# API: LOGLARI TEMİZLE
# ═══════════════════════════════════════════════════════════════

@app.route("/api/dashboard/clear-logs", methods=["POST"])
def clear_logs():
    conn = get_db()
    conn.execute("DELETE FROM login_logs")
    conn.execute("""
        UPDATE users
        SET    failed_attempts = 0,
               is_locked       = FALSE,
               lock_until      = NULL
    """)
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Tüm loglar temizlendi!"})


# ═══════════════════════════════════════════════════════════════
# BAŞLAT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()
    print(f"\n[DB] Veritabani: {DB_PATH}")
    print(f"[WEB] http://127.0.0.1:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
    