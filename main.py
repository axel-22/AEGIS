# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-04-11
# Main entry point for the AEGIS application

import sys
import time
from datetime import datetime

import aegis.interfaces.cli as a

def print_header():
    print("\n" + "═" * 100)
    print(" " *34 +"🔐 AEGIS Secure Voting System")
    print(" " *28 + "Prototype de démonstration de vote sécurisé")
    print("═" * 100 + "\n")
    print(f"🕒  Démarrage à {datetime.now().strftime('%H:%M:%S')} \n")

def show_menu():
    print("Veuillez sélectionner une action - Section puis Action (ex A1 pour lister les utilisteurs actifs):\n")

    print("👥  Utilisateurs - A")
    print("  1 →  📋 Lister les tous les utilisateurs")
    print("  2 →  ✅ Lister les utilisateurs actifs")
    print("  3 →  🚫 Lister les utilisateurs révoqués")
    print("  4 →  ➕ Ajouter un utilisateur")
    print("  5 →  🔄 Editer un utilisateur")
    print("  6 →  🗑️ Supprimer un utilisateur\n")
    

    print("🎫  Badges - B")
    print("  1 →  🪪 Lister tous les badges")
    print("  2 →  ✅ Lister les badges actifs")
    print("  3 →  ⌛ Lister les badges expirés")
    print("  4 →  🚫 Révoquer un badge compromis\n")


    print("🗳️  Votes - C")
    print("  1 →  📩 Créer un nouveau vote")
    print("  2 →  👀 Voir le vote en cours")
    print("  3 →  🧾 Lister les votes précédents")
    print("  4 →  🔗 Vérifier la chaîne d’intégrité (blockchain)\n")

    print("🧠  Sécurité & Outils - D")
    print("  1 →   🔑 Générer la clé secret Fernet")
    print("  2 →   🔑 Générer une paire de clés RSA")
    print("  3 →   🤳 Simuler un challenge d’authentification (Tap + TOTP)")


    print("📦  Maintenance & Logs - E")
    print("  1 →  📰 Voir les logs récents")
    print("  2 →  📊 Exporter les événements vers le SIEM")
    print("  3 →  💾 Sauvegarder la base de données\n")

    print("❌  0 →  Quitter l’application\n")

def main():
    print_header()

    while True:
        show_menu()
        
        choice = input("➡️  Votre choix : ").strip()
        
        while not (choice == "0" or (len(choice) == 2 and choice[0] in "ABCDE" and choice[1] in "123456")):
            print("⚠️  Choix invalide, veuillez réessayer.")
            choice = input("➡️  Votre choix (ex A1 pour lister les utilisteurs actifs) : ").strip() 

        #Section A - Utilisateurs
        if choice[0] == "A" and choice[1] == "1":
            print("\n 📋Liste de tous les utilisateurs...\n")
            a.list_all_users()
            print("Enter pour continuer...")
            input()
        elif choice[0] == "A" and choice[1] == "2":
            print("\n ✅ Liste des utilisateurs actifs...\n")
            a.list_users(False)
            print("Enter pour continuer...")
            input()
        elif choice[0] == "A" and choice[1] == "3":
            print("\n🚫 Liste des utilisateurs révoqués...\n")
            a.list_users(True)
            print("Enter pour continuer...")
            input()
        elif choice[0] == "A" and choice[1] == "4":
            print("\n👤 Ajout d’un nouvel utilisateur...\n")
            a.create_user()
            print("Enter pour continuer...")
            input()
        elif choice[0] == "A" and choice[1] == "5":
            print("\n🔄 Edition d’un utilisateur...\n")
            a.edit_user()
            print("Enter pour continuer...")
            input()  
        elif choice[0] == "A" and choice[1] == "6":
            print("\n🗑️ Suppression d’un utilisateur...\n")
            a.remove_user()
            print("Enter pour continuer...")
            input()    
        
        #Section B - Badges
        elif choice[0] == "B" and choice[1] == "1":
            print("\n🪪 Liste de tous les badges...\n")
            print("Enter pour continuer...")
            input()
        elif choice[0] == "B" and choice[1] == "1":
            print("\n✅ Liste des badges actifs...\n")
            print("Enter pour continuer...")
            input()
        elif choice[0] == "B" and choice[1] == "2":
            print("\n⌛ Liste des badges expirés...\n")
            print("Enter pour continuer...")
            input()
        elif choice[0] == "B" and choice[1] == "3":
            print("\n🚫 Révocation d’un badge compromis...\n")
            print("Enter pour continuer...")
            input()

        #Section C - Votes
        elif choice[0] == "C" and choice[1] == "1":
            print("\n📩 Création d’un nouveau vote...\n")
            print("Enter pour continuer...")
            input()
        elif choice[0] == "C" and choice[1] == "2":
            print("\n👀 Affichage du vote en cours...\n")
            print("Enter pour continuer...")
            input()
        elif choice[0] == "C" and choice[1] == "3":
            print("\n🧾 Historique des votes précédents...\n")
            print("Enter pour continuer...")
            input()
        elif choice[0] == "C" and choice[1] == "4":
            print("\n🔗 Vérification de la chaîne d’intégrité (hashchain)...\n")
            print("Enter pour continuer...")
            input()

        #Section D - Sécurité & Outils
        elif choice[0] == "D" and choice[1] == "1":
            print("\n🔑 Génération de la clé secret Fernet \n")
            a.fernet_key()
            print("Enter pour continuer...")
            input()
        elif choice[0] == "D" and choice[1] == "2":
            print("\n🔑 Génération d’une paire de clés RSA...\n")
            print("Enter pour continuer...")
            input()
        elif choice[0] == "D" and choice[1] == "3":
            print("\n🤳 Simulation d’un challenge TOTP + Tap...\n")
            print("Enter pour continuer...")
            input()
        #Section E - Maintenance & Logs
        elif choice[0] == "E" and choice[1] == "1":
            print("\n📰 Vérification de la cohérence interne de la base...\n")
            print("Enter pour continuer...")
            input()
        elif choice[0] == "E" and choice[1] == "2":
            print("\n 📊  Export des logs vers le SIEM...\n")
            print("Enter pour continuer...")
            input()
        elif choice[0] == "E" and choice[1] == "3":
            print("\n💾 Sauvegarde complète de la base de données...\n")
            print("Enter pour continuer...")
            input()

        # Exit option    
        elif choice == "0": 
            print("\n🔐  Exit AEGIS... \n")
            sys.exit(0)
        else:
            print("⚠️ Choix invalide, veuillez réessayer.\n")

if __name__ == "__main__":
    main()