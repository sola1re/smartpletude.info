from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo
import os
import secrets
from datetime import datetime, timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

# Initialize Flask app
app = Flask(__name__, template_folder='template')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configuration simplifiée
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///smartpletude.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_SECURE'] = True      # Active le cookie uniquement en HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True    # Empêche l'accès via JS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   # Protège contre le CSRF (Lax est un bon compromis)

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

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
    email = StringField('Email', validators=[DataRequired(), Email()])
    nom = StringField('Nom', validators=[DataRequired(), Length(min=2, max=100)])
    prenom = StringField('Prénom', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(), 
        Length(min=6, message='Le mot de passe doit contenir au moins 6 caractères')
    ])
    password2 = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(), EqualTo('password', message='Les mots de passe doivent correspondre')
    ])
    user_type = SelectField('Type de compte', choices=[
        ('etudiant', 'Étudiant'), 
        ('professeur', 'Professeur')
    ], validators=[DataRequired()])
    submit = SubmitField('S\'inscrire')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

# Helper functions
def is_logged_in():
    return 'user_id' in session

def get_current_user():
    if is_logged_in():
        return User.query.get(session['user_id'])
    return None

# Routes
@app.route('/')
def home():
    current_user = get_current_user()
    return render_template('index.html', current_user=current_user)

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
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
    # Vérification explicite du type d'utilisateur
        if form.user_type.data not in ['etudiant', 'professeur']:
            flash("Type d'utilisateur invalide.", 'error')
            return render_template('register.html', form=form)

        existing_user = User.query.filter_by(email=form.email.data.lower()).first()
        if existing_user:
            flash('Un compte avec cet email existe déjà.', 'error')
            return render_template('register.html', form=form)
        
        # Créer un nouveau utilisateur
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            email=form.email.data.lower().strip(),
            nom=form.nom.data.strip(),
            prenom=form.prenom.data.strip(),
            user_type=form.user_type.data,
            password_hash=hashed_password
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            
            flash('Votre compte a été créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Une erreur est survenue lors de la création du compte.', 'error')
            print(f"Erreur lors de la création du compte: {e}")
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            session.clear()
            session['user_id'] = user.id
            session.permanent = form.remember_me.data
            
            flash(f'Bienvenue {user.prenom}!', 'success')
            
            # Rediriger vers la page appropriée selon le type d'utilisateur
            if user.user_type == 'professeur':
                return redirect(url_for('professeurs'))
            else:
                return redirect(url_for('etudiants'))
        else:
            flash('Email ou mot de passe incorrect.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('home'))

@app.route('/professeurs')
def professeurs():
    current_user = get_current_user()
    if not current_user:
        flash('Vous devez être connecté pour accéder à cette page.', 'error')
        return redirect(url_for('login'))
    if current_user.user_type != 'professeur':
        flash('Accès réservé aux professeurs.', 'error')
        return redirect(url_for('home'))
    return render_template('professeurs.html', current_user=current_user)

@app.route('/etudiants')
def etudiants():
    current_user = get_current_user()
    if not current_user:
        flash('Vous devez être connecté pour accéder à cette page.', 'error')
        return redirect(url_for('login'))
    if current_user.user_type != 'etudiant':
        flash('Accès réservé aux étudiants.', 'error')
        return redirect(url_for('home'))
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
    app.run(debug=debug_mode, host='127.0.0.1', port=5000)
