from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo
import os
import secrets
import json
from datetime import datetime
from datetime import datetime, timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
import unicodedata
import logging
import bleach
from wtforms.validators import Regexp
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL, NTLM
from flask_wtf.csrf import CSRFProtect
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='template')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


# Configuration simplifiée
PORT = int(os.environ.get('PORT', 8080))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   # Protège contre le CSRF (Lax est un bon compromis)
LDAP_SERVER = os.environ.get('LDAP_SERVER')
LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN')


# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

#Configuration du logger
if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = logging.FileHandler('logs/app.log', encoding='utf-8', errors='replace')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

app.logger.info('Application démarrée')


# User Model simplifié
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'etudiant' or 'professeur'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.email}>'

# Forms simplifiés
class RegistrationForm(FlaskForm):
    email = StringField(
        'Email', 
        validators=[
            DataRequired(), 
            Email(message="Adresse email invalide"),
            Regexp(r'^[\w\.-]+@[\w\.-]+\.\w+$', message="Format d'email invalide")
        ]
    )
    nom = StringField(
        'Nom', 
        validators=[
            DataRequired(), 
            Length(min=2, max=100),
            Regexp(r"^[A-Za-zÀ-ÿ\s'-]+$", message="Le nom contient des caractères invalides.")
        ]
    )
    prenom = StringField(
        'Prénom', 
        validators=[
            DataRequired(), 
            Length(min=2, max=100),
            Regexp(r"^[A-Za-zÀ-ÿ\s'-]+$", message="Le prénom contient des caractères invalides.")
        ]
    )
    password = PasswordField(
        'Mot de passe', 
        validators=[
            DataRequired(), 
            Length(min=6, message='Le mot de passe doit contenir au moins 6 caractères')
        ]
    )
    password2 = PasswordField(
        'Confirmer le mot de passe', 
        validators=[
            DataRequired(), 
            EqualTo('password', message='Les mots de passe doivent correspondre')
        ]
    )
    user_type = SelectField(
        'Type de compte', 
        choices=[('etudiant', 'Étudiant'), ('professeur', 'Professeur')], 
        validators=[DataRequired()]
    )
    submit = SubmitField('S\'inscrire')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class SearchForm(FlaskForm):
    query = StringField('Rechercher un cours', validators=[DataRequired()])
    submit = SubmitField('Rechercher')

# Helper functions
def is_logged_in():
    return 'user_id' in session

def get_current_user():
    if is_logged_in():
        return User.query.get(session['user_id'])
    return None

def load_courses():
    """Charge les cours depuis le fichier JSON"""
    try:
        courses_file = os.path.join(os.path.dirname(__file__), 'static', 'courses.json')
        with open(courses_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('courses', [])
    except FileNotFoundError:
        print("Erreur : Fichier courses.json introuvable.")
        return []
    except json.JSONDecodeError:
        print("Erreur lors du parsing du fichier JSON.")
        return []
    except Exception as e:
        print(f"Erreur inconnue lors du chargement des cours : {e}")
        return []



def ldap_find_user_dn(email):
    try:
        server = Server(os.environ.get('LDAP_SERVER'), get_info=ALL)
        conn = Connection(
            server,
            user=os.environ.get('LDAP_BIND_DN'),
            password=os.environ.get('LDAP_BIND_PASSWORD'),
            auto_bind=True
        )

        search_filter = f"(mail={email})"
        conn.search(
            search_base=os.environ.get('LDAP_BASE_DN'),
            search_filter=search_filter,
            attributes=['distinguishedName', 'cn', 'mail']
        )

        if conn.entries:
            user_dn = conn.entries[0].entry_dn
            app.logger.info(f"DN trouvé pour {email} : {user_dn}")
            return user_dn
        else:
            app.logger.warning(f"Aucun DN trouvé pour {email} en LDAP.")
            return None
    except Exception as e:
        app.logger.warning(f"Erreur lors de la recherche LDAP de l'utilisateur {email} : {e}")
        return None


def ldap_authenticate(user_dn, password):
    try:
        server = Server(os.environ.get('LDAP_SERVER'), get_info=ALL)
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        return conn.bound
    except Exception as e:
        app.logger.warning(f"Erreur lors de l'authentification LDAP avec le DN {user_dn} : {e}")
        return False

def ldap_get_user_info(user_dn):
    try:
        server = Server(os.environ.get('LDAP_SERVER'), get_info=ALL)
        conn = Connection(
            server,
            user=os.environ.get('LDAP_BIND_DN'),
            password=os.environ.get('LDAP_BIND_PASSWORD'),
            auto_bind=True
        )

        conn.search(
            search_base=user_dn,
            search_filter='(objectClass=person)',
            attributes=['givenName', 'sn', 'cn']
        )

        if conn.entries:
            entry = conn.entries[0]

            nom = entry.sn.value if 'sn' in entry and entry.sn.value else None
            prenom = entry.givenName.value if 'givenName' in entry and entry.givenName.value else None

            if not nom or not prenom:
                cn = entry.cn.value if 'cn' in entry else None
                if cn:
                    parts = cn.strip().split(' ', 1)
                    if len(parts) == 2:
                        prenom = prenom or parts[0]
                        nom = nom or parts[1]
                    else:
                        prenom = prenom or parts[0]
                        nom = nom or "NomInconnu"

            # Fallback final si toujours rien
            nom = nom or "NomInconnu"
            prenom = prenom or "PrenomInconnu"

            app.logger.info(f"Infos LDAP extraites pour {user_dn} → nom: {nom}, prénom: {prenom}")
            return {'nom': nom, 'prenom': prenom}
        else:
            app.logger.warning(f"Aucune entrée LDAP trouvée pour DN: {user_dn}")
            return {'nom': 'NomInconnu', 'prenom': 'PrenomInconnu'}

    except Exception as e:
        app.logger.error(f"Erreur extraction infos LDAP pour {user_dn} : {e}")
        return {'nom': 'NomInconnu', 'prenom': 'PrenomInconnu'}


def normalize(text):
    """Supprime les accents et met en minuscules"""
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower()

def search_courses(query):
    """Recherche intelligente dans les cours"""
    if not query or len(query.strip()) < 2:
        return []

    courses = load_courses()
    query_words = normalize(query).split()
    results = []

    for course in courses:
        score = 0

        # Normalisation de tous les champs utiles
        title = normalize(course.get('title', ''))
        description = normalize(course.get('description', ''))
        subject = normalize(course.get('subject', ''))
        level = normalize(course.get('level', ''))
        keywords = [normalize(k) for k in course.get('keywords', [])]

        # Recherche
        for word in query_words:
            if word in title:
                score += 3
            if word in description:
                score += 2
            if any(word in k for k in keywords):
                score += 4
            if word in subject or word in level:
                score += 3

        if score > 0:
            course_copy = course.copy()
            course_copy['relevance_score'] = score
            results.append(course_copy)

    return sorted(results, key=lambda x: x['relevance_score'], reverse=True)



# Routes
@app.route('/')
def home():
    current_user = get_current_user()
    search_form = SearchForm()
    return render_template('index.html', current_user=current_user, search_form=search_form)

@app.route('/about')
def about():
    current_user = get_current_user()
    return render_template('about.html', current_user=current_user)

@app.route('/search', methods=['GET', 'POST'])
def search():
    current_user = get_current_user()
    form = SearchForm()
    courses = []
    query = ""
    
    if request.method == 'POST' and form.validate_on_submit():
        query = form.query.data
        courses = search_courses(query)
        
        if not courses:
            flash(f'Aucun cours trouvé pour "{query}". Essayez avec d\'autres mots-clés.', 'info')
    
    elif request.method == 'GET' and request.args.get('q'):
        query = request.args.get('q', '').strip()
        if query:
            form.query.data = query
            courses = search_courses(query)
    
    return render_template('search.html', 
                         current_user=current_user, 
                         form=form, 
                         courses=courses, 
                         query=query)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if app.debug:
        return f"<pre>{error}</pre>", 500
    return render_template('500.html'), 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        app.logger.info("Tentative d'accès à la page d'inscription par un utilisateur déjà connecté.")
        return redirect(url_for('home'))

    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Vérification explicite du type d'utilisateur
        if form.user_type.data not in ['etudiant', 'professeur']:
            app.logger.warning(f"Type d'utilisateur invalide soumis : {form.user_type.data}")
            flash("Type d'utilisateur invalide.", 'error')
            return render_template('register.html', form=form)

        email = bleach.clean(form.email.data.lower().strip())
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            app.logger.warning(f"Tentative d'inscription avec un email déjà existant : {form.email.data}")
            flash('Un compte avec cet email existe déjà.', 'error')
            return render_template('register.html', form=form)

        # Créer un nouveau utilisateur
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            email=email,
            nom=bleach.clean(form.nom.data.strip()),
            prenom=bleach.clean(form.prenom.data.strip()),
            user_type=form.user_type.data,
            password_hash=hashed_password
        )

        try:
            db.session.add(user)
            db.session.commit()

            app.logger.info(f"Nouvel utilisateur inscrit : {user.email} ({user.user_type})")

            flash('Votre compte a été créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de l'inscription de l'utilisateur {user.email} : {e}")
            flash('Une erreur est survenue lors de la création du compte.', 'error')

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        email = bleach.clean(form.email.data.lower().strip())
        password = form.password.data

        app.logger.info(f"Login attempt for email: {email}")

        # 1) Recherche DN utilisateur dans LDAP
        user_dn = ldap_find_user_dn(email)
        if user_dn:
            app.logger.info(f"Utilisateur LDAP trouvé : {email} avec DN {user_dn}")

            # 2) Tente d'authentifier en LDAP avec DN + mot de passe
            if ldap_authenticate(user_dn, password):
                app.logger.info(f"Authentification LDAP réussie pour {email}")

                # 3) Cherche utilisateur localement
                user = User.query.filter_by(email=email).first()

                # 4) Si utilisateur local n'existe pas, crée-le avec données LDAP basiques
                if not user:
                    app.logger.info(f"Utilisateur {email} absent en local, création...")
                    ldap_info = ldap_get_user_info(user_dn)
                    nom = ldap_info.get('nom', 'NomInconnu')
                    prenom = ldap_info.get('prenom', 'PrenomInconnu')

                    # Logique user_type selon email
                    if email.endswith('@smartpletude.info'):
                        user_type = 'admin'
                    else:
                        user_type = 'professeur'

                    user = User(
                        email=email,
                        nom=nom,
                        prenom=prenom,
                        user_type=user_type,
                        password_hash=bcrypt.generate_password_hash(secrets.token_urlsafe(16)).decode('utf-8')  # mdp random car on utilise LDAP
                    )
                    try:
                        db.session.add(user)
                        db.session.commit()
                        app.logger.info(f"Utilisateur {email} créé en local avec succès en tant que {user_type}.")
                    except Exception as e:
                        db.session.rollback()
                        app.logger.error(f"Erreur création utilisateur local {email}: {e}")
                        flash('Erreur lors de la création de votre compte local.', 'error')
                        return render_template('login.html', form=form)

                # 5) Connexion réussie : session etc
                session.clear()
                session['user_id'] = user.id
                session.permanent = form.remember_me.data
                flash(f'Bienvenue {user.prenom}!', 'success')

                # Redirection selon type
                if user.user_type == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user.user_type == 'professeur':
                    return redirect(url_for('professeurs'))
                else:
                    return redirect(url_for('etudiants'))

            else:
                app.logger.warning(f"Échec authentification LDAP pour {email} : mot de passe incorrect")
                flash('Mot de passe LDAP incorrect.', 'error')
                return render_template('login.html', form=form)

        else:
            app.logger.info(f"Utilisateur {email} non trouvé en LDAP, tentative auth base locale...")

            # Essaye auth locale si user existe dans BDD locale
            user = User.query.filter_by(email=email).first()
            if user and bcrypt.check_password_hash(user.password_hash, password):
                session.clear()
                session['user_id'] = user.id
                session.permanent = form.remember_me.data

                app.logger.info(f"Connexion réussie (base locale) : {email} ({user.user_type})")
                flash(f'Bienvenue {user.prenom}!', 'success')

                if user.user_type == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user.user_type == 'professeur':
                    return redirect(url_for('professeurs'))
                else:
                    return redirect(url_for('etudiants'))
            else:
                app.logger.warning(f"Tentative de connexion échouée pour l'email : {email}")
                flash('Email ou mot de passe incorrect.', 'error')

    return render_template('login.html', form=form)



@app.route('/logout')
def logout():
    user = get_current_user()
    if user:
        app.logger.info(f"Déconnexion de l'utilisateur : {user.email}")
    else:
        app.logger.info("Déconnexion d'une session anonyme ou expirée.")
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('home'))


@app.route('/professeurs')
def professeurs():
    current_user = get_current_user()

    if not current_user:
        app.logger.warning("Accès non autorisé à /professeurs sans être connecté.")
        flash('Vous devez être connecté pour accéder à cette page.', 'error')
        return redirect(url_for('login'))

    if current_user.user_type not in ['professeur', 'admin']:
        app.logger.warning(f"Utilisateur non autorisé ({current_user.email}) a tenté d'accéder à /professeurs.")
        flash('Accès réservé aux professeurs et admins.', 'error')
        return redirect(url_for('home'))

    app.logger.info(f"Page /professeurs visitée par : {current_user.email}")
    return render_template('professeurs.html', current_user=current_user)


@app.route('/etudiants')
def etudiants():
    current_user = get_current_user()

    if not current_user:
        app.logger.warning("Accès non autorisé à /etudiants sans être connecté.")
        flash('Vous devez être connecté pour accéder à cette page.', 'error')
        return redirect(url_for('login'))

    if current_user.user_type not in ['etudiant', 'admin']:
        app.logger.warning(f"Utilisateur non autorisé ({current_user.email}) a tenté d'accéder à /etudiants.")
        flash('Accès réservé aux étudiants et admins.', 'error')
        return redirect(url_for('home'))

    app.logger.info(f"Page /etudiants visitée par : {current_user.email}")
    return render_template('etudiants.html', current_user=current_user)

@app.route('/admin_dashboard')
def admin_dashboard():
    current_user = get_current_user()

    if not current_user or current_user.user_type != 'admin':
        app.logger.warning(f"Accès non autorisé à /admin par {current_user.email if current_user else 'utilisateur non connecté'}")
        flash('Accès réservé aux administrateurs.', 'error')
        return redirect(url_for('home'))

    return render_template('admin_dashboard.html', current_user=current_user)


# Gestionnaire d'erreurs
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Initialisation de la base de données
def init_db():
    with app.app_context():
        try:
            db.create_all()
            print("Base de données PostgreSQL initialisée avec succès !")
        except Exception as e:
            app.logger.error(f"Erreur lors de l'initialisation de la BDD : {e}")
            print(repr(e))  # <-- ajoute ceci
            print("Échec de l'initialisation de la base de données.")




if __name__ == '__main__':
    init_db()
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, host='127.0.0.1', port=PORT)
