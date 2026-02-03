--AEGIS - NowBlackout ENSIBS 2025
--Last modified: 2025-27-10
--Database schema for the AEGIS voting system

-- ========== 0. RESET DES TABLES ==============
DROP TABLE IF EXISTS SECRETS;
DROP TABLE IF EXISTS NONCES;
DROP TABLE IF EXISTS ENVELOPES;
DROP TABLE IF EXISTS ANSWERS;
DROP TABLE IF EXISTS VOTES;
DROP TABLE IF EXISTS BADGES;
DROP TABLE IF EXISTS USERS;
DROP TABLE IF EXISTS SHARES;

-- ========== 1. UTILISATEURS ===================
CREATE TABLE USERS (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(50) UNIQUE,
    job VARCHAR(50),
    the_role VARCHAR(50), -- (member, validator, admin, superadmin etc.)
    created_at DATETIME,
    updated_at DATETIME
);

-- ========= 2. BADGES =======================
CREATE TABLE BADGES (
    badge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    the_user INTEGER REFERENCES USERS(user_id),
    header_id VARCHAR(100) NOT NULL,          
    issued_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    totp_secret VARCHAR(100) NOT NULL,
    is_revoked BOOLEAN NOT NULL CHECK (is_revoked IN (0, 1)),
    revoked_at DATETIME,
    revoked_reason VARCHAR(100)
);

-- ========== 3. VOTES =======================
CREATE TABLE VOTES (
    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
    question VARCHAR(500) NOT NULL,
    description_text VARCHAR(1000),
    is_boolean NOT NULL CHECK (is_boolean IN (0, 1)),
    creator_user_id INTEGER REFERENCES USERS(user_id),
    vote_mode VARCHAR(100), -- (autability, anonymity)
    vote_type VARCHAR(100) NOT NULL, -- (unanimity, majority, min_ok, etc.)
    k_required INTEGER DEFAULT 0, -- pour le type min_ok
    vote_status VARCHAR(50), -- (open, closed, aborted, timeout, etc.)
    opened_at DATETIME,
    timeout_at DATETIME,
    is_active BOOLEAN NOT NULL CHECK (is_active IN (0, 1)),
    closed_at DATETIME,
    vote_result VARCHAR(1000) -- answer (approved, rejected, etc.)
);

-- ========== 4. ENVELOPPES DE VOTE ==========
CREATE TABLE ENVELOPES (
    envelope_id INTEGER PRIMARY KEY AUTOINCREMENT,
    the_vote REFERENCES VOTES(vote_id),
    the_user REFERENCES USERS(user_id),
    the_date DATETIME NOT NULL,
    the_badge INTEGER REFERENCES BADGES(badge_id),
    vote_choice INTEGER NOT NULL,
    prev_hash VARCHAR(100),
    current_hash VARCHAR(100) NOT NULL,
    siem_loged BOOLEAN NOT NULL CHECK (siem_loged IN (0, 1)) -- Envoyé au SIEM ?
);

-- ========== 5. NONCES  ====================
CREATE TABLE NONCES (
    nonce_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nonce VARCHAR(50),
    the_envelope REFERENCES ENVELOPES(envelope_id),
    issued_at DATETIME,
    used BOOLEAN NOT NULL CHECK (used IN (0, 1)),
    the_user INTEGER REFERENCES USERS(user_id),
    used_at DATETIME
);

-- ========== 6. ANSWERS  =========================
CREATE TABLE ANSWERS (
    answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    the_vote REFERENCES VOTES(vote_id),
    answer_text VARCHAR(500) NOT NULL
);
-- ========== 7. SECRET SHAMIR  ====================
CREATE TABLE SECRETS (
    secret_id INTEGER PRIMARY KEY AUTOINCREMENT,
    secret_value VARCHAR(500) NOT NULL,
    secret_type VARCHAR(50) NOT NULL,
    secret_action VARCHAR(50),
    secret_share_n INTEGER NOT NULL,
    secret_share_k INTEGER NOT NULL,
    creator_user_id REFERENCES USERS(user_id),
    issued_at DATETIME,
    used BOOLEAN NOT NULL CHECK (used IN (0, 1)),
    used_at DATETIME
);

-- ========== 8. PARTAGE DE SECRET  =======================
CREATE TABLE SHARES (
    share_id INTEGER PRIMARY KEY AUTOINCREMENT,
    the_secret REFERENCES SECRETS(secret_id),
    the_badge REFERENCES BADGES(badge_id),
    shamir_value VARCHAR(50),
    used_at DATETIME
);
-- ========== 9. INSERT DEFAULT USERS ==============

INSERT INTO USERS (username, first_name, last_name, email, job, the_role) VALUES
('admin', 'Admin', 'Admin', 'admin@aegis.com', 'Admin', 'superadmin');

INSERT INTO USERS (username, first_name, last_name, email, job, the_role) VALUES
('default', 'Default', 'User', 'default@aegis.com', 'User', 'member');