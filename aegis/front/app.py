from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import hashlib
import secrets
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
has_initialized = False

def init_db():
    global has_initialized
    if has_initialized: return
    conn = sqlite3.connect('aegis.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS badges 
                 (uid TEXT PRIMARY KEY, nom TEXT, actif INTEGER DEFAULT 1, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scrutins 
                 (id INTEGER PRIMARY KEY, titre TEXT, question TEXT, options TEXT, 
                  date_debut TEXT, date_fin TEXT, actif INTEGER DEFAULT 0, quorum INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS votes 
                 (id INTEGER PRIMARY KEY, scrutin_id INTEGER, badge_uid TEXT, bulletin TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit (timestamp TEXT, action TEXT, details TEXT)''')
    
    # Badges test
    c.execute("INSERT OR IGNORE INTO badges (uid, nom, is_admin) VALUES (?, ?, ?)", ('badge_admin_123', 'Admin', 1))
    c.execute("INSERT OR IGNORE INTO badges (uid, nom, is_admin) VALUES (?, ?, ?)", ('badge_user_456', 'User 1', 0))
    c.execute("INSERT OR IGNORE INTO badges (uid, nom, is_admin) VALUES (?, ?, ?)", ('badge_user_789', 'User 2', 0))
    
    conn.commit()
    conn.close()
    has_initialized = True

# DECORATEUR ADMIN CORRIGÉ
def admin_required(f):
    def wrap(*args, **kwargs):
        if not session.get('is_admin') == 1:  # Vérifie is_admin == 1
            flash('Accès administrateur requis')
            return redirect(url_for('connexion'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap


@app.before_request
def restrict_access():
    if request.remote_addr != '127.0.0.1' and request.remote_addr != '::1':
        return "Accès interdit", 403
    init_db()

@app.route('/')
@app.route('/index')
def index():
    return render_template('vote.html')

@app.route('/scrutins_actifs')
def scrutins_actifs():
    conn = sqlite3.connect('aegis.db')
    scrutin = conn.execute("SELECT * FROM scrutins WHERE actif=1 LIMIT 1").fetchone()
    conn.close()
    if scrutin:
        return jsonify({'scrutin': {'id': scrutin[0], 'titre': scrutin[1], 'question': scrutin[2], 'options': scrutin[3]}})
    return jsonify({'scrutin': None})

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        uid = request.form.get('badge_uid', '').strip()
        conn = sqlite3.connect('aegis.db')
        c = conn.cursor()
        c.execute("SELECT nom, is_admin FROM badges WHERE uid=? AND actif=1", (uid,))
        badge = c.fetchone()
        conn.close()
        
        if badge:
            session['badge_uid'] = uid
            session['badge_nom'] = badge[0]
            session['is_admin'] = badge[1]
            log_audit('LOGIN', f"{badge[0]} ({uid})")
            flash(f'Connecté: {badge[0]}')
            return redirect(url_for('index'))
        flash('Badge inconnu')
    
    return render_template('connexion.html')

@app.route('/deconnexion')
def deconnexion():
    if 'badge_uid' in session:
        log_audit('LOGOUT', session['badge_nom'])
    session.clear()
    flash('Déconnecté')
    return redirect(url_for('index'))


@app.route('/administration', methods=['GET', 'POST'])
@admin_required
def administration():
    if request.method == 'POST':
        if 'logout' in request.form:
            return deconnexion()
        
        titre = request.form.get('titre')
        question = request.form.get('question')
        options = request.form.get('options')
        quorum = int(request.form.get('quorum', 0))
        
        if titre and question and options:
            conn = sqlite3.connect('aegis.db')
            c = conn.cursor()
            c.execute("INSERT INTO scrutins (titre, question, options, date_debut, quorum) VALUES (?, ?, ?, ?, ?)",
                      (titre, question, options, datetime.now().isoformat(), quorum))
            scrutin_id = c.lastrowid
            c.execute("UPDATE scrutins SET actif=1 WHERE id=?", (scrutin_id,))
            conn.commit()
            conn.close()
            log_audit('CREATE_SCRUTIN', f"ID:{scrutin_id} {titre}")
            flash('Scrutin créé!')
    
    conn = sqlite3.connect('aegis.db')
    scrutins = conn.execute("SELECT * FROM scrutins ORDER BY id DESC LIMIT 5").fetchall()
    badges = conn.execute("SELECT * FROM badges WHERE actif=1").fetchall()
    conn.close()
    return render_template('administration.html', scrutins=scrutins, badges=badges)

@app.route('/statistiques')
@admin_required
def statistiques():
    conn = sqlite3.connect('aegis.db')
    stats = {
        'total_badges': conn.execute("SELECT COUNT(*) FROM badges WHERE actif=1").fetchone()[0],
        'scrutins': len(conn.execute("SELECT * FROM scrutins").fetchall()),
        'votes': len(conn.execute("SELECT * FROM votes").fetchall())
    }
    bulletins = conn.execute("""
        SELECT v.id, s.titre, b.nom, v.timestamp, v.bulletin 
        FROM votes v 
        JOIN scrutins s ON v.scrutin_id=s.id 
        JOIN badges b ON v.badge_uid=b.uid 
        ORDER BY v.timestamp DESC LIMIT 20
    """).fetchall()
    audits = conn.execute("SELECT * FROM audit ORDER BY timestamp DESC LIMIT 10").fetchall()
    conn.close()
    return render_template('statistiques.html', stats=stats, bulletins=bulletins, audits=audits)

@app.route('/vote', methods=['POST'])
def process_vote():
    badge_uid = request.form.get('badge_uid')
    scrutin_id = request.form.get('scrutin_id')
    choix = request.form.get('choix')
    
    conn = sqlite3.connect('aegis.db')
    c = conn.cursor()
    c.execute("SELECT * FROM badges WHERE uid=? AND actif=1", (badge_uid,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'Badge non autorisé'})
    
    c.execute("SELECT * FROM votes WHERE scrutin_id=? AND badge_uid=?", (scrutin_id, badge_uid))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'Déjà voté'})
    
    c.execute("SELECT * FROM scrutins WHERE id=? AND actif=1", (scrutin_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'Aucun scrutin actif'})
    
    bulletin_hash = hashlib.sha256(f"{badge_uid}:{choix}".encode()).hexdigest()
    c.execute("INSERT INTO votes (scrutin_id, badge_uid, bulletin, timestamp) VALUES (?, ?, ?, ?)",
              (scrutin_id, badge_uid, bulletin_hash, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    log_audit('VOTE', f"Badge:{badge_uid} Scrutin:{scrutin_id}")
    return jsonify({'success': 'Vote enregistré'})

def log_audit(action, details):
    conn = sqlite3.connect('aegis.db')
    c = conn.cursor()
    c.execute("INSERT INTO audit (timestamp, action, details) VALUES (?, ?, ?)",
              (datetime.now().isoformat(), action, details))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5000, debug=True)
