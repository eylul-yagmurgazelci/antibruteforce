from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import bcrypt
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)
# -----------------------
# 3. KİŞİ: GÜVENLİK MEKANİZMASI (ZAMANLI BRUTE FORCE)
# -----------------------
# Yapı: { "ip_adresi": {"deneme": 0, "kilit_bitis": 0} }
login_attempts = {}

# -----------------------
# 4. KİŞİ: VERİTABANI VE LOGLAMA
# -----------------------
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # Kullanıcı tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        password BLOB
    )
    """)
    conn.commit()
    conn.close()

def log_yaz(mesaj):
    # Bu kısım ilerde 4. kişi tarafından DB loglamasına çevrilebilir
    with open("log.txt", "a", encoding="utf-8") as f:
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{zaman}] {mesaj}\n")

init_db()

# -----------------------
# 2. KİŞİ: BACKEND (REGISTER)
# -----------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Veri alınamadı"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    # 1. Kişi (Frontend) için form doğrulaması
    if not username or not email or not password:
        return jsonify({"status": "error", "message": "Lütfen tüm alanları doldurun"}), 400

    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        # E-posta çakışma kontrolü
        cursor.execute("SELECT email FROM users WHERE email=?", (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Bu e-posta zaten kayıtlı"}), 409

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed)
        )
        conn.commit()
        log_yaz(f"YENİ KAYIT: {email}")
        return jsonify({"status": "success", "message": "Kayıt başarıyla oluşturuldu"}), 201

    except Exception as e:
        return jsonify({"status": "error", "message": "Sistemsel bir hata oluştu"}), 500
    finally:
        conn.close()

# -----------------------
# 2. KİŞİ & 3. KİŞİ: LOGIN VE GÜVENLİK
# -----------------------
@app.route("/login", methods=["POST"])
def login():
    ip = request.remote_addr
    simdi = time.time()

    # 3. Kişi: Brute Force ve Kilit Süresi Kontrolü[cite: 1]
    if ip in login_attempts:
        if login_attempts[ip]['kilit_bitis'] > simdi:
            kalan_sure = int(login_attempts[ip]['kilit_bitis'] - simdi)
            return jsonify({
                "status": "locked", 
                "message": f"Çok fazla deneme! {kalan_sure} saniye sonra tekrar deneyin."
            }), 403

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"status": "error", "message": "Eksik bilgi"}), 400

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE email=?", (email,))
    user = cursor.fetchone()
    conn.close()

    # Giriş Mantığı
    if user and bcrypt.checkpw(password.encode(), user[0]):
        # Başarılı giriş: Sayacı sıfırla
        login_attempts[ip] = {'deneme': 0, 'kilit_bitis': 0}
        log_yaz(f"BAŞARILI GİRİŞ: {email}")
        return jsonify({"status": "success", "message": "Giriş başarılı! Yönlendiriliyorsunuz..."})

    else:
        # Başarısız giriş: Sayacı artır[cite: 1]
        stats = login_attempts.get(ip, {'deneme': 0, 'kilit_bitis': 0})
        stats['deneme'] += 1
        
        if stats['deneme'] >= 5:
            stats['kilit_bitis'] = simdi + 300  # 5 Dakika (300 saniye) kilit[cite: 1]
            log_yaz(f"HESAP KİLİTLENDİ: {ip} - {email}")
            login_attempts[ip] = stats
            return jsonify({"status": "locked", "message": "5 hatalı deneme! 5 dakika kilitlendiniz."}), 403
        
        login_attempts[ip] = stats
        log_yaz(f"HATALI DENEME ({stats['deneme']}/5): {email}")
        return jsonify({"status": "error", "message": "E-posta veya şifre hatalı"}), 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)