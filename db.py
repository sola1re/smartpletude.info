#!/usr/bin/env python3
"""
Script d'initialisation de la base de données pour Smartpletude
Ce script initialise la base de données et peut créer des utilisateurs de test
"""

import sys
from sqlalchemy import inspect
from app import app, db, User, bcrypt
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
import secrets


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()  # Charge .env
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')


# Fix for potential encoding issues in DATABASE_URL
def get_safe_database_url():
    """Récupère l'URL de la base de données en gérant les problèmes d'encodage"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Essayer de décoder et re-encoder proprement
            return database_url.encode('utf-8').decode('utf-8')
        return None
    except UnicodeDecodeError:
        print("❌ Erreur d'encodage dans DATABASE_URL")
        print("💡 Essayez de recréer votre fichier .env avec l'encodage UTF-8")
        return None

SQLALCHEMY_DATABASE_URI = get_safe_database_url()
SQLALCHEMY_TRACK_MODIFICATIONS = False

def test_database_connection():
    """Test la connexion à la base de données"""
    print("Test de connexion à la base de données...")
    
    if not SQLALCHEMY_DATABASE_URI:
        print("❌ DATABASE_URL non trouvée ou invalide")
        return False
    
    try:
        with app.app_context():
            # Méthode alternative avec inspect
            inspector = inspect(db.engine)
            inspector.get_table_names()  # Ceci teste la connexion
            print("✅ Connexion à la base de données réussie")
            return True
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        print("\n🔧 Solutions possibles:")
        print("1. Vérifiez que PostgreSQL est démarré")
        print("2. Vérifiez les paramètres de connexion dans .env")
        print("3. Vérifiez que la base de données 'smartpletude' existe")
        print("4. Vérifiez l'encodage de votre fichier .env (UTF-8)")
        return False
    
    
def init_database():
    """Initialise la base de données"""
    print("Initialisation de la base de données...")

    if not test_database_connection():
        return False

    try:
        with app.app_context():
            db.drop_all()
            print("Tables existantes supprimées")

            db.create_all()
            print("Tables créées avec succès")

            tables = inspect(db.engine).get_table_names()
            print(f"Tables créées: {', '.join(tables)}")
            return True
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        return False

def create_test_users():
    """Crée des utilisateurs de test"""
    print("Création des utilisateurs de test...")

    try:
        with app.app_context():
            prof_password = bcrypt.generate_password_hash('prof123').decode('utf-8')
            prof = User(
                email='prof@smartpletude.info',
                nom='Dupont',
                prenom='Marie',
                user_type='professeur',
                password_hash=prof_password
            )

            etudiant_password = bcrypt.generate_password_hash('etudiant123').decode('utf-8')
            etudiant = User(
                email='etudiant@smartpletude.info',
                nom='Martin',
                prenom='Pierre',
                user_type='etudiant',
                password_hash=etudiant_password
            )

            db.session.add_all([prof, etudiant])
            db.session.commit()
            print("✅ Utilisateurs de test créés avec succès")
            print("   Professeur: prof@smartpletude.info / prof123")
            print("   Étudiant: etudiant@smartpletude.info / etudiant123")
            return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la création des utilisateurs: {e}")
        return False

def show_database_info():
    """Affiche les informations sur la base de données"""
    print("Informations sur la base de données:")

    if not test_database_connection():
        return

    try:
        with app.app_context():
            user_count = User.query.count()
            prof_count = User.query.filter_by(user_type='professeur').count()
            etudiant_count = User.query.filter_by(user_type='etudiant').count()

            print(f"   Total utilisateurs: {user_count}")
            print(f"   Professeurs: {prof_count}")
            print(f"   Étudiants: {etudiant_count}")

            users = User.query.all()
            if users:
                print("Liste des utilisateurs:")
                for user in users:
                    print(f"   - {user.email} ({user.user_type}) - {user.prenom} {user.nom}")
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des informations: {e}")

def reset_database():
    """Remet à zéro complètement la base de données"""
    print("Remise à zéro complète de la base de données...")

    if init_database():
        create_test_users()
    else:
        print("❌ Échec de la remise à zéro")

def delete_user_by_email():
    """Supprime un utilisateur à partir de son email"""
    print("\n🗑️ Suppression d'un utilisateur")
    
    if not test_database_connection():
        return
        
    email = input("Entrez l'email de l'utilisateur à supprimer: ").strip()

    try:
        with app.app_context():
            user = User.query.filter_by(email=email).first()
            if user:
                confirm = input(f"Confirmer la suppression de {user.prenom} {user.nom} ({user.email}) ? (oui/non): ").lower()
                if confirm in ['oui', 'o', 'yes', 'y']:
                    db.session.delete(user)
                    db.session.commit()
                    print(f"✅ Utilisateur {email} supprimé avec succès.")
                else:
                    print("❌ Suppression annulée.")
            else:
                print(f"❌ Aucun utilisateur trouvé avec l'email: {email}")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la suppression: {e}")

def check_environment():
    """Vérifie la configuration de l'environnement"""
    print("🔍 Vérification de l'environnement...")
    
    # Vérifier le fichier .env
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ Fichier {env_file} trouvé")
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'DATABASE_URL' in content:
                    print("✅ DATABASE_URL trouvée dans .env")
                else:
                    print("❌ DATABASE_URL non trouvée dans .env")
        except UnicodeDecodeError:
            print("❌ Problème d'encodage dans le fichier .env")
            print("💡 Recréez le fichier .env avec l'encodage UTF-8")
    else:
        print(f"❌ Fichier {env_file} non trouvé")
    
    # Vérifier les variables d'environnement
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        print("✅ DATABASE_URL chargée")
        # Masquer le mot de passe pour l'affichage
        safe_url = database_url
        if '@' in safe_url:
            parts = safe_url.split('@')
            if ':' in parts[0]:
                user_pass = parts[0].split(':')
                if len(user_pass) >= 2:
                    safe_url = f"{user_pass[0]}:***@{parts[1]}"
        print(f"   URL: {safe_url}")
    else:
        print("❌ DATABASE_URL non chargée")

def main():
    """Fonction principale avec menu interactif"""
    print("=" * 50)
    print("SMARTPLETUDE - Gestionnaire de Base de Données")
    print("=" * 50)

    while True:
        print("\nQue souhaitez-vous faire?")
        print("1. Initialiser la base de données")
        print("2. Créer des utilisateurs de test")
        print("3. Afficher les informations de la base")
        print("4. Remise à zéro complète")
        print("5. Quitter")
        print("6. Supprimer un utilisateur par email")
        print("7. Vérifier l'environnement")
        print("8. Tester la connexion")

        choice = input("\nVotre choix (1-8): ").strip()

        if choice == '1':
            init_database()
        elif choice == '2':
            create_test_users()
        elif choice == '3':
            show_database_info()
        elif choice == '4':
            confirm = input("Êtes-vous sûr de vouloir tout supprimer ? (oui/non): ")
            if confirm.lower() in ['oui', 'o', 'yes', 'y']:
                reset_database()
            else:
                print("❌ Opération annulée")
        elif choice == '5':
            print("👋 Au revoir.")
            break
        elif choice == '6':
            delete_user_by_email()
        elif choice == '7':
            check_environment()
        elif choice == '8':
            test_database_connection()
        else:
            print("❌ Choix invalide, veuillez réessayer.")

if __name__ == '__main__':
    main()