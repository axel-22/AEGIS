#!/usr/bin/env python3
"""
AEGIS — Suite de tests
Exécuter depuis la racine du projet :  python test.py
"""

import os
import sys
import time
import tempfile
import hashlib
import unittest

# ── Environnement de test ──────────────────────────────────────────────────────
os.environ["DEV_MODE"]          = "false"
os.environ["AEGIS_API_DEBUG"]   = "false"
os.environ["AEGIS_SQLALCHEMY_DEBUG"] = "false"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Patch DB → fichier temporaire AVANT tout import de service ────────────────
# _database.py a son propre DB_PATH hardcodé ; on le remplace avant que
# les services (users, badges…) appellent db.set_debug() à l'import.
_TEST_DB = tempfile.mktemp(suffix=".db", prefix="aegis_test_")

import aegis.core._database as _db
from aegis.core._models import Base
_db.DB_PATH = _TEST_DB
# Pré-créer l'engine en mémoire pour que init_db() trouve quelque chose
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
_db.engine       = create_engine(f"sqlite:///{_TEST_DB}", echo=False,
                                  connect_args={"check_same_thread": False})
_db.SessionLocal = sessionmaker(bind=_db.engine)
Base.metadata.create_all(bind=_db.engine)

# ── Couleurs terminal ──────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"
B = "\033[1m";  _= "\033[0m"


# ══════════════════════════════════════════════════════════════════════════════
# 1. RBAC  — logique pure, aucun accès DB
# ══════════════════════════════════════════════════════════════════════════════
from aegis.services import rbac

class TestRBAC(unittest.TestCase):

    def test_superadmin_ne_peut_pas_voter(self):
        self.assertFalse(rbac.has_permission("superadmin", "votes.cast"))

    def test_tous_les_autres_roles_peuvent_voter(self):
        for role in ("admin", "manager", "member", "auditor"):
            self.assertTrue(rbac.has_permission(role, "votes.cast"), role)

    def test_admin_gestion_complete_utilisateurs(self):
        for p in ("users.create", "users.edit", "users.delete", "users.list"):
            self.assertTrue(rbac.has_permission("admin", p), p)

    def test_superadmin_gestion_complete_utilisateurs(self):
        for p in ("users.create", "users.edit", "users.delete", "users.list"):
            self.assertTrue(rbac.has_permission("superadmin", p), p)

    def test_member_aucune_gestion_utilisateurs(self):
        for p in ("users.create", "users.edit", "users.delete"):
            self.assertFalse(rbac.has_permission("member", p), p)

    def test_auditor_peut_auditer(self):
        self.assertTrue(rbac.has_permission("auditor", "votes.audit"))
        self.assertTrue(rbac.has_permission("auditor", "votes.results.all"))

    def test_member_ne_voit_pas_tous_les_resultats(self):
        self.assertFalse(rbac.has_permission("member", "votes.results.all"))

    def test_superadmin_genere_cles(self):
        self.assertTrue(rbac.has_permission("superadmin", "keys.generate"))

    def test_manager_peut_creer_et_fermer_votes(self):
        self.assertTrue(rbac.has_permission("manager", "votes.create"))
        self.assertTrue(rbac.has_permission("manager", "votes.close"))

    def test_manager_ne_gere_pas_utilisateurs(self):
        self.assertFalse(rbac.has_permission("manager", "users.create"))

    def test_role_inconnu_aucune_permission(self):
        self.assertFalse(rbac.has_permission("pirate", "users.delete"))
        self.assertEqual(rbac.get_permissions("pirate"), frozenset())

    def test_require_permission_leve_PermissionError(self):
        with self.assertRaises(PermissionError):
            rbac.require_permission("member", "users.delete")

    def test_require_permission_ne_leve_rien_si_ok(self):
        rbac.require_permission("member", "votes.cast")   # aucune exception

    def test_tous_les_roles_ont_secrets_view_own(self):
        for role in rbac.VALID_ROLES:
            self.assertTrue(rbac.has_permission(role, "secrets.view_own"), role)

    def test_toutes_les_permissions_sont_des_strings(self):
        for role, perms in rbac.ROLE_PERMISSIONS.items():
            for p in perms:
                self.assertIsInstance(p, str, f"{role}: {p!r}")

    def test_superadmin_pas_de_votes_cast(self):
        # superadmin supervise ; il ne vote pas
        self.assertFalse(rbac.has_permission("superadmin", "votes.cast"))

    def test_admin_peut_sauvegarder_logs(self):
        self.assertTrue(rbac.has_permission("admin", "logs.backup"))

    def test_5_roles_valides(self):
        self.assertEqual(len(rbac.VALID_ROLES), 5)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Validation des champs utilisateur  — fonctions pures
# ══════════════════════════════════════════════════════════════════════════════
from aegis.services.users import is_valid_email, is_valid_username, is_valid_name

class TestValidationUsers(unittest.TestCase):

    # ── emails ────────────────────────────────────────────────────────────────
    def test_email_valides(self):
        for e in ("jean@ensibs.fr", "j.dupont@example.co.uk", "a@b.io",
                  "user.name@domain.fr"):
            self.assertTrue(is_valid_email(e), e)

    def test_email_invalides(self):
        for e in ("pas-un-email", "@domaine.com", "user@", "", "a" * 51 + "@x.fr"):
            self.assertFalse(is_valid_email(e), e)

    # ── usernames ─────────────────────────────────────────────────────────────
    def test_username_valides(self):
        for u in ("jean.dupont", "user_42", "JD2025", "abc"):
            self.assertTrue(is_valid_username(u), u)

    def test_username_invalides(self):
        for u in ("jean dupont", "jean@corp", "", "a" * 51, "x!x"):
            self.assertFalse(is_valid_username(u), u)

    # ── noms/prénoms ──────────────────────────────────────────────────────────
    def test_noms_valides(self):
        for n in ("Jean", "O'Brien", "Saint-Exupéry", "Müller", "Björk"):
            self.assertTrue(is_valid_name(n), n)

    def test_noms_invalides(self):
        for n in ("Jean Dupont", "Jean123", "", "a" * 51, "A B"):
            self.assertFalse(is_valid_name(n), n)

    # ── create_user : chemins d'erreur ────────────────────────────────────────
    def test_create_user_role_invalide(self):
        from aegis.services.users import create_user
        with self.assertRaises(ValueError):
            create_user({"first_name": "Alice", "last_name": "Martin",
                         "username": "a.martin", "the_role": "hacker",
                         "email": None, "job": None})

    def test_create_user_prenom_invalide(self):
        from aegis.services.users import create_user
        with self.assertRaises(ValueError):
            create_user({"first_name": "Alice 123", "last_name": "Martin",
                         "username": "a.martin", "the_role": "member",
                         "email": None, "job": None})

    def test_create_user_nom_invalide(self):
        from aegis.services.users import create_user
        with self.assertRaises(ValueError):
            create_user({"first_name": "Alice", "last_name": "Mar tin",
                         "username": "a.martin", "the_role": "member",
                         "email": None, "job": None})

    def test_create_user_username_invalide(self):
        from aegis.services.users import create_user
        with self.assertRaises(ValueError):
            create_user({"first_name": "Alice", "last_name": "Martin",
                         "username": "alice martin!", "the_role": "member",
                         "email": None, "job": None})

    def test_create_user_succes_et_unicite(self):
        from aegis.services.users import create_user
        data = {"first_name": "Bob", "last_name": "Dupont",
                "username": "b.dupont.test", "the_role": "member",
                "email": None, "job": None}
        user = create_user(data)
        self.assertIsNotNone(user.user_id)
        self.assertEqual(user.username, "b.dupont.test")
        # Doublon doit échouer
        with self.assertRaises(ValueError):
            create_user(data)

    def test_tous_les_roles_valides_acceptes(self):
        from aegis.services.users import create_user
        for i, role in enumerate(("admin", "manager", "auditor")):
            u = create_user({"first_name": "Test", "last_name": "Role",
                             "username": f"test.role.{i}", "the_role": role,
                             "email": None, "job": None})
            self.assertEqual(u.the_role, role)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Secret Sharing
# ══════════════════════════════════════════════════════════════════════════════
try:
    from sslib import shamir as _sss
    _SSLIB_OK = True
except ImportError:
    _sss      = None
    _SSLIB_OK = False

_skip_sslib = unittest.skipUnless(_SSLIB_OK, "sslib non installé — pip install sslib")

@_skip_sslib
class TestSecretSharingMath(unittest.TestCase):

    @staticmethod
    def _roundtrip(text: str, k: int, n: int) -> str:
        raw  = _sss.split_secret(text.encode(), k, n)
        b64  = _sss.to_base64(raw)
        back = _sss.recover_secret(_sss.from_base64({
            "required_shares": k,
            "prime_mod":       b64["prime_mod"],
            "shares":          b64["shares"],
        }))
        return back.decode()

    def test_2_of_3(self):
        self.assertEqual(self._roundtrip("CLÉSECRETE2025", 2, 3), "CLÉSECRETE2025")

    def test_3_of_5(self):
        self.assertEqual(self._roundtrip("topSecret!#@", 3, 5), "topSecret!#@")

    def test_2_of_2(self):
        self.assertEqual(self._roundtrip("min", 2, 2), "min")

    def test_parts_insuffisantes_erreur(self):
        raw = _sss.split_secret(b"motdepasse", 3, 5)
        b64 = _sss.to_base64(raw)
        with self.assertRaises(Exception):
            _sss.recover_secret(_sss.from_base64({
                "required_shares": 3,
                "prime_mod":       b64["prime_mod"],
                "shares":          b64["shares"][:2],
            }))

    def test_toute_combinaison_k_parmi_n(self):
        secret = "consistance"
        raw    = _sss.split_secret(secret.encode(), 2, 4)
        b64    = _sss.to_base64(raw)
        shares = b64["shares"]
        for i in range(len(shares)):
            for j in range(i + 1, len(shares)):
                r = _sss.recover_secret(_sss.from_base64({
                    "required_shares": 2,
                    "prime_mod":       b64["prime_mod"],
                    "shares":          [shares[i], shares[j]],
                }))
                self.assertEqual(r.decode(), secret, f"parts {i},{j}")


# Validation pré-DB (levée avant tout accès session) — indépendant de sslib
class TestSecretSharingValidation(unittest.TestCase):

    def _call(self, *a):
        # import inline : si sslib absent, ImportError ici → on skipte
        try:
            from aegis.services.secret_sharing import split_and_store
        except ImportError:
            self.skipTest("sslib non installé")
        return split_and_store(*a)

    def test_secret_vide_refuse(self):
        with self.assertRaises(ValueError):
            self._call("label", "", 2, [1, 2], 1)

    def test_label_vide_refuse(self):
        with self.assertRaises(ValueError):
            self._call("", "secret", 2, [1, 2], 1)

    def test_k_inferieur_2_refuse(self):
        with self.assertRaises(ValueError):
            self._call("lbl", "sec", 1, [1, 2], 1)

    def test_k_superieur_n_refuse(self):
        with self.assertRaises(ValueError):
            self._call("lbl", "sec", 5, [1, 2], 1)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Chaîne de hachage des enveloppes  — logique pure
# ══════════════════════════════════════════════════════════════════════════════
class TestHashChain(unittest.TestCase):

    @staticmethod
    def _h(vote_id, user_id, choice, prev):
        return hashlib.sha256(f"{vote_id}:{user_id}:{choice}:{prev}".encode()).hexdigest()

    def test_hash_deterministe(self):
        h1 = self._h(1, 2, 0, "genesis")
        h2 = self._h(1, 2, 0, "genesis")
        self.assertEqual(h1, h2)

    def test_hash_different_si_choix_different(self):
        self.assertNotEqual(self._h(1, 2, 0, "g"), self._h(1, 2, 1, "g"))

    def test_hash_different_si_prev_different(self):
        self.assertNotEqual(self._h(1, 2, 0, "aaa"), self._h(1, 2, 0, "bbb"))

    def test_chaine_integre(self):
        chain, prev = [], "0" * 64
        for i in range(10):
            h = self._h(1, i + 1, i % 2, prev)
            chain.append({"hash": h, "prev": prev})
            prev = h
        for i in range(1, len(chain)):
            self.assertEqual(chain[i]["prev"], chain[i - 1]["hash"])

    def test_corruption_detectable(self):
        hashes, prev = [], "0" * 64
        for i in range(6):
            h = self._h(1, i + 1, 0, prev)
            hashes.append(h)
            prev = h
        hashes[3] = "x" * 64      # corrompt l'entrée 3
        corrupted = any(
            hashes[i] != self._h(1, i + 1, 0, hashes[i - 1])
            for i in range(1, len(hashes))
        )
        self.assertTrue(corrupted)

    def test_hash_longueur_sha256(self):
        h = self._h(1, 1, 0, "prev")
        self.assertEqual(len(h), 64)   # SHA-256 → 64 hex chars


# ══════════════════════════════════════════════════════════════════════════════
# 5. API Flask  — client de test, même DB temporaire
# ══════════════════════════════════════════════════════════════════════════════
class TestAPIFlask(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from aegis.interfaces.api import app
        app.config["TESTING"]    = True
        app.config["SECRET_KEY"] = "test-secret-key-aegis"
        cls.client = app.test_client()
        cls.app    = app

    def _j(self, r):
        return r.get_json() or {}

    # ── Pages HTML ────────────────────────────────────────────────────────────
    def test_page_connexion_200(self):
        r = self.client.get("/connexion")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"AEGIS", r.data)

    def test_page_vote_200(self):
        self.assertEqual(self.client.get("/vote").status_code, 200)

    def test_page_admin_200(self):
        self.assertEqual(self.client.get("/admin").status_code, 200)

    def test_page_super_admin_200(self):
        self.assertEqual(self.client.get("/super_admin").status_code, 200)

    def test_page_stats_200(self):
        self.assertEqual(self.client.get("/stats").status_code, 200)

    def test_page_compte_200(self):
        self.assertEqual(self.client.get("/compte").status_code, 200)

    # ── Endpoints sans session → 401 ─────────────────────────────────────────
    def _assert_401(self, method, path, **kw):
        fn  = getattr(self.client, method)
        r   = fn(path, **kw)
        self.assertEqual(r.status_code, 401,
                         f"{method.upper()} {path} devrait retourner 401, got {r.status_code}")

    def test_me_sans_session(self):
        self._assert_401("get", "/api/me")

    def test_logout_sans_session(self):
        self._assert_401("post", "/api/logout")

    def test_users_list_sans_session(self):
        self._assert_401("get", "/api/users")

    def test_user_create_sans_session(self):
        self._assert_401("post", "/api/users",
                         json={"first_name": "x", "last_name": "y",
                               "username": "xy", "role": "member"})

    def test_badges_list_sans_session(self):
        self._assert_401("get", "/api/badges")

    def test_votes_list_sans_session(self):
        self._assert_401("get", "/api/votes")

    def test_vote_pending_sans_session(self):
        self._assert_401("get", "/api/votes/pending")

    def test_vote_create_sans_session(self):
        self._assert_401("post", "/api/votes", json={"question": "Test?"})

    def test_vote_cast_sans_session(self):
        self._assert_401("post", "/api/votes/1/cast",
                         json={"nonce": "x", "answer_id": 1,
                               "header_id": "x", "totp_code": "000000"})

    def test_vote_results_sans_session(self):
        self._assert_401("get", "/api/votes/1/results")

    def test_vote_close_sans_session(self):
        self._assert_401("post", "/api/votes/1/close")

    def test_logs_sans_session(self):
        self._assert_401("get", "/api/logs")

    def test_backup_sans_session(self):
        self._assert_401("post", "/api/maintenance/backup")

    def test_integrity_sans_session(self):
        self._assert_401("get", "/api/maintenance/integrity")

    def test_secrets_list_sans_session(self):
        self._assert_401("get", "/api/secrets")

    def test_secrets_mine_sans_session(self):
        self._assert_401("get", "/api/secrets/mine")

    def test_secret_create_sans_session(self):
        self._assert_401("post", "/api/secrets",
                         json={"label": "x", "secret": "y",
                               "k": 2, "badge_ids": [1]})

    def test_keys_generate_sans_session(self):
        self._assert_401("post", "/api/keys/generate", json={"type": "totp"})

    # ── Lookup & Login ────────────────────────────────────────────────────────
    def test_lookup_utilisateur_inconnu_404(self):
        r = self.client.get("/api/auth/lookup?username=fantome_inexistant")
        self.assertEqual(r.status_code, 404)

    def test_lookup_sans_username_400(self):
        r = self.client.get("/api/auth/lookup")
        self.assertIn(r.status_code, (400, 404))

    def test_login_payload_vide_400(self):
        r = self.client.post("/api/login", json={})
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", self._j(r))

    def test_login_champs_manquants_400(self):
        r = self.client.post("/api/login",
                             json={"username": "jean", "totp_code": "123456"})
        self.assertEqual(r.status_code, 400)

    def test_login_utilisateur_inexistant_401(self):
        r = self.client.post("/api/login", json={
            "username": "personne", "header_id": "abc", "totp_code": "000000"
        })
        self.assertEqual(r.status_code, 401)

    # ── Format JSON des réponses d'erreur ─────────────────────────────────────
    def test_erreurs_contiennent_champ_error(self):
        endpoints = [
            ("get",  "/api/me"),
            ("get",  "/api/users"),
            ("get",  "/api/votes"),
            ("get",  "/api/badges"),
        ]
        for method, path in endpoints:
            r = getattr(self.client, method)(path)
            d = self._j(r)
            self.assertIn("error", d, f"{method.upper()} {path}")


# ══════════════════════════════════════════════════════════════════════════════
# Runner coloré avec résumé
# ══════════════════════════════════════════════════════════════════════════════
class _ColorResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.ok  = 0
        self._t0 = time.time()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.ok += 1
        print(f"  {G}✓{_} {test._testMethodName}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        print(f"  {R}✗{_} {test._testMethodName}")
        print(f"    {R}{str(err[1]).splitlines()[-1]}{_}")

    def addError(self, test, err):
        super().addError(test, err)
        print(f"  {Y}!{_} {test._testMethodName}")
        print(f"    {Y}{str(err[1]).splitlines()[-1]}{_}")

    def summary(self):
        elapsed = time.time() - self._t0
        total   = self.ok + len(self.failures) + len(self.errors)
        print()
        print("─" * 56)
        if not self.failures and not self.errors:
            print(f"{G}{B}  ✅  {self.ok}/{total} tests passés  ({elapsed:.2f}s){_}")
        else:
            ko = len(self.failures) + len(self.errors)
            print(f"{R}{B}  ❌  {ko} échec(s) / {total} tests  ({elapsed:.2f}s){_}")
            for t, tb in self.failures:
                print(f"  {R}FAIL{_}  {t}  →  {tb.splitlines()[-1]}")
            for t, tb in self.errors:
                print(f"  {Y}ERR {_}  {t}  →  {tb.splitlines()[-1]}")
        print("─" * 56)
        return not self.failures and not self.errors


SUITES = [
    ("RBAC",                     TestRBAC),
    ("Validation utilisateurs",  TestValidationUsers),
    ("Secret Sharing (math)",    TestSecretSharingMath),
    ("Secret Sharing (valid.)",  TestSecretSharingValidation),
    ("Chaîne de hachage",        TestHashChain),
    ("API Flask",                TestAPIFlask),
]

if __name__ == "__main__":
    print(f"\n{C}{B}══════════════════════════════════════════════════════")
    print( "  AEGIS — Suite de tests")
    print(f"══════════════════════════════════════════════════════{_}\n")

    result = _ColorResult()

    for name, klass in SUITES:
        print(f"{B}{C}▶  {name}{_}")
        unittest.TestLoader().loadTestsFromTestCase(klass).run(result)
        print()

    ok = result.summary()

    # Nettoyage DB temporaire
    try:
        os.remove(_TEST_DB)
    except OSError:
        pass

    sys.exit(0 if ok else 1)
