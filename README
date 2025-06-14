# 🎓 Smartpletude - Plateforme de cours particuliers

Une application web Flask simple et sécurisée pour mettre en relation professeurs et étudiants pour des cours particuliers.

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture technique](#-architecture-technique)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Structure du projet](#-structure-du-projet)
- [Base de données](#-base-de-données)
- [Sécurité](#-sécurité)

## ✨ Fonctionnalités

- **Inscription/Connexion** sécurisée pour professeurs et étudiants
- **Gestion des sessions** avec option "Se souvenir de moi"
- **Interface différenciée** selon le type d'utilisateur
- **Validation des formulaires** côté serveur
- **Gestion d'erreurs** avec pages personnalisées
- **Base de données SQLite** simple à déployer

## 🏗️ Architecture technique

### Stack technique
- **Backend** : Flask 2.3.3 (Python)
- **Base de données** : SQLite (par défaut) / PostgreSQL (optionnel)
- **ORM** : SQLAlchemy
- **Authentification** : Flask-Bcrypt (hashage des mots de passe)
- **Formulaires** : Flask-WTF + WTForms
- **Templates** : Jinja2

### Composants principaux

#### 1. **app.py** - Application principale
```python
# Points clés de l'implémentation :
- Configuration Flask simplifiée mais sécurisée
- Modèle User avec champs essentiels
- Routes protégées avec vérification de session
- Hashage des mots de passe avec bcrypt (12 rounds)
- Validation des formulaires côté serveur
```

#### 2. **db.py** - Gestionnaire de base de données
```python
# Fonctionnalités :
- Initialisation automatique des tables
- Création d'utilisateurs de test
- Interface en ligne de commande interactive
- Fonctions de maintenance (reset, stats)
```

## 🚀 Installation

### Prérequis
- Python 3.8+ installé
- pip (gestionnaire de paquets Python)

### Étapes d'installation

1. **Cloner le projet**
```bash
git clone <url-du-repo>
cd smartpletude
```

2. **Créer un environnement virtuel** (recommandé)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Initialiser la base de données**
```bash
python db.py
```
Choisissez l'option 1 puis 2 pour initialiser et créer les utilisateurs de test.

5. **Lancer l'application**
```bash
python app.py
```

L'application sera accessible sur : **http://127.0.0.1:5000**

## 🖥️ Utilisation

### Comptes de test
Après avoir initialisé la base avec `db.py` :

- **Professeur** : `prof@smartpletude.info` / `prof123`
- **Étudiant** : `etudiant@smartpletude.info` / `etudiant123`

### Navigation
1. **Page d'accueil** : `/` - Présentation du site
2. **Inscription** : `/register` - Création de compte
3. **Connexion** : `/login` - Authentification
4. **Espace professeur** : `/professeurs` - Interface dédiée aux profs
5. **Espace étudiant** : `/etudiants` - Interface dédiée aux étudiants

### Gestionnaire de base de données
```bash
python db.py
```

Menu interactif avec options :
- **1** : Initialiser la base de données
- **2** : Créer des utilisateurs de test
- **3** : Afficher les statistiques
- **4** : Remise à zéro complète
- **5** : Quitter

## 📁 Structure du projet

```
smartpletude/
├── app.py                 # Application Flask principale
├── db.py                  # Gestionnaire de base de données
├── requirements.txt       # Dépendances Python
├── .env                   # Configuration (optionnel)
├── smartpletude.db       # Base de données SQLite (générée)
├── template/             # Templates HTML
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── professeurs.html
│   ├── etudiants.html
│   ├── 404.html
│   └── 500.html
└── static/               # Fichiers statiques (CSS, JS, images)
    └── style.css
```

## 🗄️ Base de données

### Modèle User
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    user_type VARCHAR(20) NOT NULL,  -- 'etudiant' ou 'professeur'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Migration vers PostgreSQL (optionnel)
Pour passer à PostgreSQL en production :

1. **Installer psycopg2**
```bash
pip install psycopg2-binary
```

2. **Configurer DATABASE_URL**
```bash
# Dans .env
DATABASE_URL=postgresql://username:password@localhost/smartpletude
```

3. **Réinitialiser la base**
```bash
python db.py  # Option 4 pour reset
```

## 🔒 Sécurité

### Mesures implémentées
- **Hashage des mots de passe** : bcrypt avec 12 rounds
- **Protection CSRF** : Flask-WTF automatique
- **Validation des formulaires** : côté serveur avec WTForms
- **Sessions sécurisées** : clé secrète aléatoire
- **Validation des emails** : format et unicité
- **Sanitisation des entrées** : strip() sur les champs texte

### Bonnes pratiques
- **Clé secrète** : Générez une clé unique en production
- **HTTPS** : Activez en production
- **Variables d'environnement** : Utilisez `.env` pour les secrets
- **Logs** : Surveillez les tentatives de connexion

## 🛠️ Développement

### Commandes utiles
```bash
# Mode debug
export FLASK_ENV=development  # Linux/Mac
set FLASK_ENV=development     # Windows
python app.py

# Vérifier la base de données
python db.py

# Réinstaller les dépendances
pip install -r requirements.txt --force-reinstall
```

### Ajouter de nouvelles fonctionnalités
1. **Nouvelles routes** : Ajoutez dans `app.py`
2. **Nouveaux champs** : Modifiez le modèle `User`
3. **Nouveaux templates** : Créez dans `template/`
4. **Styles** : Modifiez `static/style.css`

### Debugging
- **Logs** : `print()` statements dans les routes
- **Base de données** : Utilisez `python db.py` option 3
- **Sessions** : Vérifiez dans les outils développeur du navigateur

## 📞 Support

En cas de problème :
1. Vérifiez que toutes les dépendances sont installées
2. Assurez-vous que la base de données est initialisée
3. Consultez les logs d'erreur Flask
4. Utilisez `python db.py` pour diagnostiquer la base
