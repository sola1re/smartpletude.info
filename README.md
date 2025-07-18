# 🎓 Smartpletude (PA8)

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
- **Base de données Postgresql** sur un server distant

## 🏗️ Architecture technique

### Stack technique
- **Backend** : Flask 2.3.3 (Python)
- **Base de données** : PostgreSQL / Possible avec MySQL
- **ORM** : SQLAlchemy
- **Authentification** : Flask-Bcrypt (hashage des mots de passe)
- **Formulaires** : Flask-WTF + WTForms
- **Templates** : Jinja2

## 🚀 Installation

1. **Cloner le projet**
```bash
git clone <url-du-repo>
cd smartpletude
```

2. **Créer un environnement virtuel**
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

5. **Lancer l'application**
```bash
python app.py
```
ou avec gunicorn pour un serveur en prod
```bash
gunicorn -w 4 app:app
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
