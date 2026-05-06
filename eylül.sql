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

CREATE TABLE IF NOT EXISTS login_logs (
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER      NOT NULL,
    ip_address   VARCHAR(45)  NOT NULL,
    attempt_time DATETIME     DEFAULT CURRENT_TIMESTAMP,
    status       VARCHAR(10)  NOT NULL CHECK (status IN ('success', 'failed')),
    reason       VARCHAR(255) DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_logs_user_id   ON login_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_ip        ON login_logs(ip_address);
CREATE INDEX IF NOT EXISTS idx_logs_time      ON login_logs(attempt_time);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);


UPDATE users
SET    failed_attempts = failed_attempts + 1
WHERE  id = :user_id;

UPDATE users
SET    is_locked       = TRUE,
       lock_until      = DATETIME('now', '+10 minutes')
WHERE  id = :user_id;

UPDATE users
SET    failed_attempts = 0,
       is_locked       = FALSE,
       lock_until      = NULL
WHERE  id = :user_id;

UPDATE users
SET    is_locked       = FALSE,
       lock_until      = NULL,
       failed_attempts = 0
WHERE  is_locked = TRUE
  AND  lock_until IS NOT NULL
  AND  lock_until < CURRENT_TIMESTAMP;

SELECT is_locked, lock_until
FROM   users
WHERE  id = :user_id;


SELECT id, username, email, created_at, is_locked, failed_attempts, lock_until
FROM   users
ORDER  BY created_at DESC;

SELECT id, username, email, failed_attempts, lock_until
FROM   users
WHERE  is_locked = TRUE
ORDER  BY lock_until DESC;

SELECT id, username, email, created_at
FROM   users
WHERE  is_locked = FALSE
ORDER  BY username ASC;

SELECT ll.log_id, ll.ip_address, ll.attempt_time, ll.status, ll.reason
FROM   login_logs ll
JOIN   users      u  ON ll.user_id = u.id
WHERE  u.username = :username
ORDER  BY ll.attempt_time DESC;


SELECT ll.log_id, u.username, ll.ip_address, ll.attempt_time, ll.status, ll.reason
FROM   login_logs ll
JOIN   users      u ON ll.user_id = u.id
WHERE  ll.attempt_time >= DATETIME('now', '-1 day')
ORDER  BY ll.attempt_time DESC;

SELECT ll.log_id, u.username, ll.ip_address, ll.attempt_time, ll.status, ll.reason
FROM   login_logs ll
JOIN   users      u ON ll.user_id = u.id
WHERE  ll.attempt_time >= DATETIME('now', '-7 days')
ORDER  BY ll.attempt_time DESC;

SELECT ll.log_id, ll.ip_address, ll.attempt_time, ll.status, ll.reason
FROM   login_logs ll
JOIN   users      u ON ll.user_id = u.id
WHERE  u.username = :username
ORDER  BY ll.attempt_time DESC;

SELECT ll.log_id, u.username, ll.attempt_time, ll.status, ll.reason
FROM   login_logs ll
JOIN   users      u ON ll.user_id = u.id
WHERE  ll.ip_address = :ip_address
ORDER  BY ll.attempt_time DESC;

SELECT ll.log_id, u.username, ll.ip_address, ll.attempt_time, ll.reason
FROM   login_logs ll
JOIN   users      u ON ll.user_id = u.id
WHERE  ll.status = 'failed'
ORDER  BY ll.attempt_time DESC;

SELECT ll.log_id, u.username, ll.ip_address, ll.attempt_time
FROM   login_logs ll
JOIN   users      u ON ll.user_id = u.id
WHERE  ll.status = 'success'
ORDER  BY ll.attempt_time DESC;

SELECT ll.log_id, ll.ip_address, ll.attempt_time, ll.status, ll.reason
FROM   login_logs ll
JOIN   users      u ON ll.user_id = u.id
WHERE  u.username       = :username
  AND  ll.attempt_time  BETWEEN :baslangic AND :bitis
  AND  ll.status        = :durum
ORDER  BY ll.attempt_time DESC;


SELECT
    COUNT(*)                                        AS toplam_deneme,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS basarili,
    SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) AS basarisiz,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
        / COUNT(*), 2
    )                                               AS basarisizlik_yuzdesi
FROM login_logs;

SELECT
    u.username,
    u.email,
    u.is_locked,
    COUNT(ll.log_id)   AS basarisiz_giris_sayisi
FROM   login_logs ll
JOIN   users      u ON ll.user_id = u.id
WHERE  ll.status = 'failed'
GROUP  BY u.id, u.username, u.email, u.is_locked
ORDER  BY basarisiz_giris_sayisi DESC
LIMIT  10;

SELECT
    ip_address,
    COUNT(*)           AS deneme_sayisi,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS basarisiz_sayisi
FROM   login_logs
GROUP  BY ip_address
ORDER  BY deneme_sayisi DESC
LIMIT  5;

SELECT
    COUNT(*)                                            AS son_24s_toplam,
    SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END) AS son_24s_basarisiz,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS son_24s_basarili
FROM login_logs
WHERE attempt_time >= DATETIME('now', '-1 day');

SELECT
    DATE(attempt_time)  AS tarih,
    COUNT(*)            AS toplam_deneme,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS basarisiz
FROM   login_logs
WHERE  attempt_time >= DATETIME('now', '-7 days')
GROUP  BY DATE(attempt_time)
ORDER  BY tarih DESC;

SELECT COUNT(*) AS kilitli_hesap_sayisi
FROM   users
WHERE  is_locked = TRUE;


INSERT OR IGNORE INTO users (username, email, password_hash) VALUES
    ('ahmet_y',   'ahmet@test.com',  '$2b$12$ORNEKHASHDEGERIXYZ001'),
    ('elif_k',    'elif@test.com',   '$2b$12$ORNEKHASHDEGERIXYZ002'),
    ('mehmet_d',  'mehmet@test.com', '$2b$12$ORNEKHASHDEGERIXYZ003'),
    ('admin',     'admin@test.com',  '$2b$12$ORNEKHASHDEGERIXYZ004');


INSERT OR IGNORE INTO login_logs (user_id, ip_address, status, reason) VALUES
    (1, '192.168.1.10', 'failed',  'Wrong password'),
    (1, '192.168.1.10', 'failed',  'Wrong password'),
    (1, '192.168.1.10', 'failed',  'Wrong password'),
    (1, '192.168.1.10', 'failed',  'Wrong password'),
    (1, '192.168.1.10', 'failed',  'Wrong password'),
    (2, '10.0.0.5',     'success', NULL),
    (3, '172.16.0.1',   'failed',  'Account locked'),
    (4, '192.168.1.99', 'success', NULL);
