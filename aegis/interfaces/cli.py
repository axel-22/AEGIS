# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# CLI Interface - Command Line Interface for AEGIS Application

from aegis.services import users, badges, ac

def create_user():
    """Interface CLI pour créer un nouvel utilisateur."""
    name = input("➡️  Prénom : ").strip().lower()
    nom = input("➡️  Nom de famille : ").strip().lower()
    username = input("➡️  Nom d'utilisateur : ").strip().lower()
    email = input("➡️  Email : ").strip().lower()
    vote_input = input("➡️  Peut voter ? (oui/non) (par défaut) oui : ").strip().lower()
    metier = input("➡️  Métier (par défaut) développeur: ").strip().lower()
    role = input("➡️  Rôle : (par défaut) membre : ").strip().lower()

    user_data = {
        "first_name": name,
        "last_name": nom,
        "username": username,
        "email": email,
        "can_vote": vote_input != "non",
        "job": metier if metier else "développeur",
        "the_role": role if role else "membre"
    }
  
    try:
        user = users.create_user(user_data)
        #print(f"Utilisateur créé avec l'ID {user.user_id}")
        print("✅"+"═" * 25 +f"Utilisateur '{user.username}' créé avec succès !\n"+"═" * 25)
        print("🪪 Récapitulation des informations ajoutées")
        print(f"  - Prénom : {user.first_name}")
        print(f"  - Nom de famille : {user.last_name}")
        print(f"  - Nom d'utilisateur : {user.username}")
        print(f"  - Email : {user.email}")
        print(f"  - Peut voter : {user.can_vote}")
        print(f"  - Métier : {user.job}")
        print(f"  - Rôle : {user.the_role}\n")
    except ValueError as e:
        print(f"Erreur de validation : {e}")
    except Exception as e:
        print(f"Erreur lors de la création : {e}")

    try:
        new_user = users.get_user_by_username(user_data.get("username"))
    except Exception as e:
        print(f"Erreur lors de la récupération de l'utilisateur par son nom: {e}")
        return

    yes_no = "oui"

    try:
        exist = badges.is_keys_existing(new_user.username)
        if not exist:
            pass
    except FileExistsError as e:
        print(f"/!\ Warning les clés pour {new_user.username} existe déja, souhaitez vous les renouvelers : {e}")
        yes_no = input("➡️  Entrée 'oui' pour renouveler les clés, ou 'non' pour quitter : ").strip().lower()      
        while yes_no not in ["oui", "non"]:
            print("❌ Entrée invalide. Veuillez répondre par 'oui' ou 'non'.")
            yes_no = input("➡️  Entrée 'oui' pour renouveler les clés, ou 'non' pour quitter : ").strip().lower()
    
    if yes_no == "oui":
        secret = badges.generate_totp_secret()
        print("➡️  Veuillez enregistrer ce secret dans votre application Google Authenticator :", secret)
        print("➡️  Un badge TOTP va être créé et attaché à l'utilisateur.")
        print("🚫   Ne partager ce secret à personne !")
        ac_passphrase = input("➡️  Entrée la passphrase de l'AC pour signer le badge : ").strip()
        try:
            b = badges.create_badge(new_user.username, secret, ac_passphrase)
        except Exception as e:
            print(f"Erreur lors de la création du badge : {e}")
            return
        
        badges.attach_badge_to_user(b.badge_id, new_user.user_id)

def list_users(is_revoked: bool):
    """Interface CLI pour lister les utilisateurs."""
    allusers = users.list_users(is_revoked)
    status = "révoqués" if is_revoked else "actifs"
    print(f"\n📋 Liste des utilisateurs {status} :\n")
    for user in allusers:
        print(f"  - ID: {user.user_id}, Username: {user.username}, Name: {user.first_name} {user.last_name}, Email: {user.email}, Can Vote: {user.can_vote}, Job: {user.job}, Role: {user.the_role}")

    print("\n👤"+"═" * 30 +f" Total: {len(allusers)} utilisateurs {status} dans la base "+"═" * 30)


def ac_setup():
    """Interface CLI pour configurer le service AC."""
    print("⚙️  Configuration du service AC")
    yes_no = "oui"
    try:
        exist = ac.is_ac_keys_existing()
        if not exist:
            pass
    except FileExistsError as e:
        print(f"/!\ Warning les clés Maitres existe déja, souhaitez vous les renouvelers : {e}")
        yes_no = input("➡️  Entrée 'oui' pour renouveler les clés, ou 'non' pour quitter : ").strip().lower()      
        while yes_no not in ["oui", "non"]:
            print("❌ Entrée invalide. Veuillez répondre par 'oui' ou 'non'.")
            yes_no = input("➡️  Entrée 'oui' pour renouveler les clés, ou 'non' pour quitter : ").strip().lower()
    
    if yes_no == "oui":
        print("/!\ Veuillez garder cette passphrase en sécurité et la mémoriser! sinon les données perdu /!\ ")
        passphrase = input("➡️  Entrée la passphrase  : ").strip()
        verify_passphrase = input("➡️  Entrée de nouveaux la passphrase : ").strip()
        while passphrase != verify_passphrase:
            print("❌ Les passphrases ne correspondent pas. Veuillez réessayer.")
            passphrase = input("➡️  Entrée la passphrase  : ").strip()
            verify_passphrase = input("➡️  Entrée de nouveaux la passphrase : ").strip()

        ac.generate_ac_keys(passphrase)    

        print("[AC] Generated new AC keypair and saved to disk.")
    else:
        print("❌ Configuration annulée par l'utilisateur.")
    print("✅Configuration terminée.")



if __name__ == "__main__":
    #ac_setup()
    create_user()
