#!/usr/bin/env python3
"""
Script d'initialisation de la base de données pour Smartpletude
Ce script initialise la base de données et peut créer des utilisateurs de test
"""

import os
import sys
from datetime import datetime

# Ajouter le répertoire parent au path pour importer app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, bcrypt

def init_database():
    """Initialise la base de données"""
    print("🔧 Initialisation de la base de données...")
    
    with app.app_context():
        # Supprimer toutes les tables existantes
        db.drop_all()
        print("📋 Tables existantes supprimées")
        
        # Créer toutes les tables
        db.create_all()
        print("✅ Tables créées avec succès")
        
        # Vérifier que les tables ont été créées
        tables = db.engine.table_names()
        print(f"📊 Tables créées: {', '.join(tables)}")

def create_test_users():
    """Crée des utilisateurs de test"""
    print("\n👥 Création des utilisateurs de test...")
    
    with app.app_context():
        # Utilisateur professeur de test
        prof_password = bcrypt.generate_password_hash('prof123').decode('utf-8')
        prof = User(
            email='prof@smartpletude.info',
            nom='Dupont',
            prenom='Marie',
            user_type='professeur',
            password_hash=prof_password
        )
        
        # Utilisateur étudiant de test
        etudiant_password = bcrypt.generate_password_hash('etudiant123').decode('utf-8')
        etudiant = User(
            email='etudiant@smartpletude.info',
            nom='Martin',
            prenom='Pierre',
            user_type='etudiant',
            password_hash=etudiant_password
        )
        
        try:
            db.session.add_all([prof, etudiant])
            db.session.commit()
            
            print("✅ Utilisateurs de test créés:")
            print("   👨‍🏫 Professeur: prof@smartpletude.info / prof123")
            print("   👨‍🎓 Étudiant: etudiant@smartpletude.info / etudiant123")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la création des utilisateurs: {e}")

def show_database_info():
    """Affiche les informations sur la base de données"""
    print("\n📊 Informations sur la base de données:")
    
    with app.app_context():
        user_count = User.query.count()
        prof_count = User.query.filter_by(user_type='professeur').count()
        etudiant_count = User.query.filter_by(user_type='etudiant').count()
        
        print(f"   👥 Total utilisateurs: {user_count}")
        print(f"   👨‍🏫 Professeurs: {prof_count}")
        print(f"   👨‍🎓 Étudiants: {etudiant_count}")
        
        # Afficher la liste des utilisateurs
        users = User.query.all()
        if users:
            print("\n📋 Liste des utilisateurs:")
            for user in users:
                print(f"   - {user.email} ({user.user_type}) - {user.prenom} {user.nom}")

def reset_database():
    """Remet à zéro complètement la base de données"""
    print("🔄 Remise à zéro complète de la base de données...")
    
    # Supprimer le fichier de base de données SQLite s'il existe
    db_file = 'smartpletude.db'
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"🗑️  Fichier {db_file} supprimé")
    
    init_database()
    create_test_users()

def main():
    """Fonction principale avec menu interactif"""
    print("=" * 50)
    print("🎓 SMARTPLETUDE - Gestionnaire de Base de Données")
    print("=" * 50)
    
    while True:
        print("\nQue souhaitez-vous faire?")
        print("1. Initialiser la base de données")
        print("2. Créer des utilisateurs de test")
        print("3. Afficher les informations de la base")
        print("4. Remise à zéro complète")
        print("5. Quitter")
        
        choice = input("\nVotre choix (1-5): ").strip()
        
        if choice == '1':
            init_database()
        elif choice == '2':
            create_test_users()
        elif choice == '3':
            show_database_info()
        elif choice == '4':
            confirm = input("⚠️  Êtes-vous sûr de vouloir tout supprimer? (oui/non): ")
            if confirm.lower() in ['oui', 'o', 'yes', 'y']:
                reset_database()
            else:
                print("❌ Opération annulée")
        elif choice == '5':
            print("👋 Au revoir!")
            break
        else:
            print("❌ Choix invalide, veuillez réessayer")

if __name__ == '__main__':
    main()