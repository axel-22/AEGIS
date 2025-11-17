--AEGIS - NowBlackout ENSIBS 2025
--Last modified: 2025-27-10
--Database schema for the AEGIS voting system

-- ========== 0. RESET DES TABLES ==============
DROP TABLE IF EXISTS SECRETS;
DROP TABLE IF EXISTS NONCES;
DROP TABLE IF EXISTS ENVELOPES;
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
    can_vote BOOLEAN NOT NULL CHECK (can_vote IN (0, 1)),
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
    json_path VARCHAR(100) NOT NULL,
    json_integrity VARCHAR(100) NOT NULL,
    totp_secret VARCHAR(100) NOT NULL,
    totp_salt VARCHAR(100) NOT NULL,
    is_revoked BOOLEAN NOT NULL CHECK (is_revoked IN (0, 1)),
    revoked_at DATETIME,
    revoked_reason VARCHAR(100)
);

-- ========== 3. VOTES =======================
CREATE TABLE VOTES (
    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
    question VARCHAR(300) NOT NULL,
    creator_user_id UUID REFERENCES USERS(user_id),
    vote_type VARCHAR(500) NOT NULL, -- (unanimity, majority, min_ok, etc.)
    k_required INTEGER DEFAULT 0, -- pour le type min_ok
    vote_status VARCHAR(50), -- (open, closed, aborted, timeout, etc.)
    opened_at DATETIME,
    timeout_at DATETIME,
    is_active BOOLEAN NOT NULL CHECK (is_active IN (0, 1)),
    closed_at DATETIME
);

-- ========== 4. ENVELOPPES DE VOTE ==========
CREATE TABLE ENVELOPES (
    envelope_id INTEGER PRIMARY KEY AUTOINCREMENT,
    the_vote REFERENCES VOTES(vote_id),
    the_user REFERENCES USERS(user_id),
    the_date DATETIME NOT NULL,
    the_badge INTEGER REFERENCES badges(badge_id),
    vote_choice JSONB NOT NULL,              -- Contenu du vote signé (choix, nonce, etc.)
    user_signature_valid BOOLEAN NOT NULL CHECK (user_signature_valid IN (0, 1)), -- Signature valide ?
    entry_hash VARCHAR(100) NOT NULL,
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
    used_by UUID REFERENCES users(user_id),
    used_at DATETIME
);

-- ========== 5. SECRET SHAMIR  ====================
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

-- ========== 6. PARTAGE DE SECRET  =======================
CREATE TABLE SHARES (
    share_id INTEGER PRIMARY KEY AUTOINCREMENT,
    the_secret REFERENCES SECRETS(secret_id),
    the_badge REFERENCES BADGES(badge_id),
    shamir_value VARCHAR(50),
    used_at DATETIME
);
-- ========== 7. INSERT DEFAULT USERS ==============

INSERT INTO USERS (username, first_name, last_name, email, job, the_role, can_vote) VALUES
('admin', 'Admin', 'Admin', 'admin@aegis.com', 'Admin', 'superadmin', 1);

INSERT INTO USERS (username, first_name, last_name, email, job, the_role, can_vote) VALUES
('default', 'Default', 'User', 'default@aegis.com', 'User', 'member', 1);