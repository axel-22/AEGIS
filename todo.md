# Schéma technique détaillé - Implémentation du système de vote

---

## 1. Fichiers principaux concernés

| Fichier                  | Rôle principal                                             |
|--------------------------|------------------------------------------------------------|
| `interfaces/cli.py`      | Interface utilisateur CLI : demande saisies, affichage     |
| `services/votes.py`      | Logique métier vote : création, ouverture, fermeture, vote |
| `services/users.py`      | Gestion utilisateur, récupération données utilisateur      |
| `services/badges.py`     | Vérification badge (authentification, validation)          |
| `services/totp.py`       | Vérification TOTP                                          |
| `core/_models.py`        | Modèles SQLAlchemy (VOTES, NONCES, ENVELOPES, USERS, etc)  |
| `core/_database.py`      | Session SQLAlchemy, transactions                            |
| `services/audit.py`      | Fonctions d’audit, validation intégrité chaîne de votes    |

---

## 2. Fonctionnalités + Fonctions à coder

| Fonction (proposition)                            | Fichier           | Rôle / Description                                                                              |
|-------------------------------------------------|-------------------|------------------------------------------------------------------------------------------------|
| `cli_create_vote()`                              | `interfaces/cli.py`| CLI : saisie question, description, type vote, durée, etc.                                    |
| `cli_assign_voters()`                            | `interfaces/cli.py`| CLI : saisie ou sélection des utilisateurs concernés (votants)                                |
| `votes_create_vote(vote_data, creator_user_id)` | `services/votes.py`| Crée l’objet Vote en base, statut `pending` ou `created`                                      |
| `votes_generate_nonces(vote_id, user_ids)`      | `services/votes.py`| Pour chaque utilisateur, créer un nonce unique lié au vote et à l’utilisateur                 |
| `votes_open_vote(vote_id)`                       | `services/votes.py`| Passe le vote en `open`, stocke `opened_at` et `timeout_at`                                   |
| `votes_cast_vote(vote_id, user_id, badge_id, totp, vote_choice, nonce)` | `services/votes.py`| Vérifie auth badge + TOTP, valide nonce, stocke l’enveloppe, marque nonce utilisé             |
| `votes_close_vote(vote_id)`                      | `services/votes.py`| Change statut en `closed`, verrouille le vote                                                 |
| `votes_count_results(vote_id)`                   | `services/votes.py`| Calcule les résultats selon le type de vote                                                   |
| `audit_validate_chain(vote_id)`                  | `services/audit.py`| Vérifie intégrité de la chaîne de hash des enveloppes                                         |
| `audit_generate_report(vote_id)`                  | `services/audit.py`| Produit un rapport d’audit, liste votants, résultats, horodatages                             |
| `badges_verify_badge(badge_id, user_id)`        | `services/badges.py`| Vérifie que le badge appartient bien à l’utilisateur et qu’il est actif                       |
| `totp_verify(totp_code, secret)`                  | `services/totp.py`  | Vérifie que le code TOTP est valide                                                          |
| `users_get_user_by_badge(badge_id)`              | `services/users.py` | Retourne utilisateur lié au badge (utile pour vote authentifié)                              |
| `users_get_user_by_username(username)`           | `services/users.py` | Retourne utilisateur par nom (utile pour CLI, admin)                                         |

---

## 3. Flux détaillé et vérifications (Mode auditable)

### Étape 1 : Création du vote (Admin)

- CLI (`interfaces/cli.py`) :  
  - `cli_create_vote()` → demande question, type, description, durée, etc.  
  - `cli_assign_voters()` → liste utilisateurs ou saisie noms des votants  
- Appelle `votes_create_vote()` avec les données + `creator_user_id` (authentifié)  
- `votes_create_vote()` :  
  - Valide les données (question non vide, vote_type reconnu, durée cohérente)  
  - Crée le vote en base avec statut `pending`  
- Appelle `votes_generate_nonces(vote_id, user_ids)` :  
  - Pour chaque user_id, créer une entrée NONCE unique  
  - Lier nonce à vote + utilisateur  
  - `used=False` par défaut

---

### Étape 2 : Ouverture du vote

- CLI ou automatique  
- `votes_open_vote(vote_id)` :  
  - Vérifie que vote est en statut `pending`  
  - Modifie statut en `open`  
  - Enregistre `opened_at` et `timeout_at`  
  - Rend le vote accessible aux votants

---

### Étape 3 : Vote (utilisateur authentifié)

- L’utilisateur s’authentifie avec badge + TOTP (interface CLI ou Web futur)  
- `votes_cast_vote(vote_id, user_id, badge_id, totp, vote_choice, nonce)` :  
  - Vérifie :  
    - Badge valide et actif (`badges_verify_badge()`)  
    - TOTP correct (`totp_verify()`)  
    - Nonce correspond au user et vote, non utilisé  
    - Vote en statut `open` et dans délai  
  - Stocke enveloppe (vote_choice signé/hasher, hash précédent)  
  - Met à jour nonce `used=True`, avec timestamp  
  - Calcule et stocke le `current_hash` de la chaîne  
  - Retourne succès ou erreur

---

### Étape 4 : Fermeture du vote

- CLI ou automatique  
- `votes_close_vote(vote_id)` :  
  - Statut passe à `closed`  
  - Enregistre `closed_at`  
  - Empêche tout nouveau vote

---

### Étape 5 : Comptage et audit

- `votes_count_results(vote_id)` :  
  - Récupère enveloppes valides  
  - Calcule résultats selon règle (majorité, etc.)  
- `audit_validate_chain(vote_id)` :  
  - Recalcule tous les hashes de la chaîne d’enveloppes  
  - Vérifie intégrité  
- `audit_generate_report(vote_id)` :  
  - Produit rapport listant :  
    - Qui a voté (nonce utilisés)  
    - Votes (en clair, car mode auditable)  
    - Intégrité chaîne hash  
    - Dates et logs

---

## 4. Flux détaillé (Mode confidentiel)

### Différences clés

- NONCES sont liés au vote, mais pas à un utilisateur précis (ou de façon anonymisée)  
- Vote soumis avec nonce, mais enveloppe stocke **vote_choice chiffré ou signé** pour masquer le choix  
- On stocke uniquement dans les logs que le nonce a été utilisé → on sait si la personne a voté, pas ce qu’elle a voté  
- Les audits listent uniquement les utilisateurs ayant voté (nonce utilisés), mais pas le contenu des votes  
- Le déchiffrement des votes se fait seulement pour le décompte, sans associer au voter

---

## 5. Organisation par fichier (concrètement)

| Fichier                 | Fonctions principales à écrire                                  | Vérifications majeures                                      | Notes                                      |
|-------------------------|-----------------------------------------------------------------|-------------------------------------------------------------|--------------------------------------------|
| `cli.py`                | `cli_create_vote()`, `cli_assign_voters()`, `cli_cast_vote()`    | Vérifier entrées, afficher erreurs, confirmer actions       | Interface utilisateur                      |
| `services/votes.py`     | `votes_create_vote()`, `votes_generate_nonces()`, `votes_open_vote()`, `votes_cast_vote()`, `votes_close_vote()`, `votes_count_results()` | Vérifier permissions, état du vote, validité nonces, authenticité badge+totp, validité temps | Logique métier vote                       |
| `services/badges.py`    | `badges_verify_badge()`                                         | Badge actif, appartient à user                               | Authentification                          |
| `services/totp.py`      | `totp_verify()`                                                 | Code TOTP valide                                            | Authentification                          |
| `services/users.py`     | `users_get_user_by_badge()`, `users_get_user_by_username()`    | Existence utilisateur                                        | Utilisateurs                              |
| `services/audit.py`     | `audit_validate_chain()`, `audit_generate_report()`             | Intégrité de la chaîne, corrélation utilisateurs/votes     | Audit et conformité                       |

---

## Conclusion : Priorités immédiates

- Coder dans `cli.py` un `cli_create_vote()` + `cli_assign_voters()` (sans auth pour l’instant)  
- Coder dans `votes.py` :  
  - `votes_create_vote()` → crée en base  
  - `votes_generate_nonces()` → crée les nonces utilisateurs liés au vote  
  - `votes_open_vote()` → démarre le vote  
- Coder dans `votes.py` `votes_cast_vote()` avec vérification badge + TOTP + nonce valide + enregistrement enveloppe + hash chain  
- Coder dans `badges.py` + `totp.py` les fonctions d’authentification (sécurisées)  
- Penser à faire un `votes_close_vote()`  
- Penser à faire dans `audit.py` une fonction d’intégrité de la chaîne  
- Plus tard, prévoir dans `cli.py` une interface `cli_cast_vote()` qui appelle la fonction vote_cast_vote avec authentification badge + totp

---

## Questions pour avancer

Veux-tu qu’on commence par écrire ensemble `votes_create_vote()` ?  
Ou préfères-tu qu’on travaille d’abord sur la vérification badge+totp ?

---

# Fin du schéma technique détaillé
