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

# Initialize Flask app
app = Flask(__name__, template_folder='template')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


# Configuration simplifiée
PORT = int(os.environ.get('PORT', 8080))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///smartpletude.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   # Protège contre le CSRF (Lax est un bon compromis)


# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

#Configuration du logger
if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
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
        user = User.query.filter_by(email=email).first()


        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            session.clear()
            session['user_id'] = user.id
            session.permanent = form.remember_me.data

            app.logger.info(f"Connexion réussie : {user.email} ({user.user_type})")

            flash(f'Bienvenue {user.prenom}!', 'success')
            if user.user_type == 'professeur':
                return redirect(url_for('professeurs'))
            else:
                return redirect(url_for('etudiants'))
        else:
            app.logger.warning(f"Tentative de connexion échouée pour l'email : {form.email.data}")
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

    if current_user.user_type != 'professeur':
        app.logger.warning(f"Utilisateur non autorisé ({current_user.email}) a tenté d'accéder à /professeurs.")
        flash('Accès réservé aux professeurs.', 'error')
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

    if current_user.user_type != 'etudiant':
        app.logger.warning(f"Utilisateur non autorisé ({current_user.email}) a tenté d'accéder à /etudiants.")
        flash('Accès réservé aux étudiants.', 'error')
        return redirect(url_for('home'))

    app.logger.info(f"Page /etudiants visitée par : {current_user.email}")
    return render_template('etudiants.html', current_user=current_user)


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
        db.create_all()
        print("Base de données initialisée avec succès!")

if __name__ == '__main__':
    init_db()
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, host='127.0.0.1', port=PORT)