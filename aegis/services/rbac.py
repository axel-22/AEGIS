# AEGIS - NowBlackout ENSIBS 2025
# RBAC Service - Role-Based Access Control

VALID_ROLES = frozenset({"superadmin", "admin", "manager", "member", "auditor"})

# Matrice des permissions par rôle
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    # Accès total : gestion utilisateurs, badges, votes, logs, clés
    "superadmin": frozenset({
        "users.create", "users.list", "users.edit", "users.delete",
        "badges.list", "badges.revoke",
        "votes.create", "votes.manage", "votes.assign", "votes.close",
        "votes.cast", "votes.results.all", "votes.results.own", "votes.audit",
        "logs.view", "logs.export", "logs.backup",
        "keys.generate",
    }),
    # Gestion des logs, consultation utilisateurs/badges/résultats
    "admin": frozenset({
        "users.list",
        "badges.list", "badges.revoke",
        "votes.results.all", "votes.results.own",
        "logs.view", "logs.export", "logs.backup",
    }),
    # Création et gestion des votes, consultation des résultats de ses propres votes
    "manager": frozenset({
        "users.list",
        "votes.create", "votes.manage", "votes.assign", "votes.close",
        "votes.results.own",
    }),
    # Vote uniquement + consultation de ses propres votes
    "member": frozenset({
        "votes.cast",
        "votes.results.own",
    }),
    # Consultation de tous les résultats + audit (qui a voté quoi en mode auditable)
    "auditor": frozenset({
        "votes.results.all",
        "votes.results.own",
        "votes.audit",
    }),
}


def has_permission(role: str, permission: str) -> bool:
    """Retourne True si le rôle dispose de la permission donnée."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def require_permission(role: str, permission: str) -> None:
    """Lève PermissionError si le rôle ne dispose pas de la permission."""
    if not has_permission(role, permission):
        raise PermissionError(
            f"Accès refusé : le rôle '{role}' ne dispose pas de la permission '{permission}'."
        )


def get_permissions(role: str) -> frozenset[str]:
    """Retourne l'ensemble des permissions d'un rôle."""
    return ROLE_PERMISSIONS.get(role, frozenset())
