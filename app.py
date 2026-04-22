import os
from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, Plot, PlotImage, User
from forms import PlotForm, LoginForm, PasswordChangeForm
from PIL import Image

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'tanzania_plots_2026_secure_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# --- LOGIN PROTECTION ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Login required to access the admin panel.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- BULLETPROOF PRICE FILTER ---
@app.template_filter('format_currency')
def format_currency(value):
    try:
        if value is None: return "0"
        return "{:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return "0"

# --- ROUTES ---

@app.route('/')
def index():
    # Only show available plots on home
    plots = Plot.query.filter_by(status='Available').order_by(Plot.id.desc()).limit(6).all()
    return render_template('index.html', plots=plots)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session['admin_id'] = user.id
            return redirect(url_for('admin_dashboard'))
        flash("Invalid credentials", "error")
    return render_template('admin/login.html', form=form)

@app.route('/admin')
@login_required
def admin_dashboard():
    try:
        plots_count = Plot.query.count()
        return render_template('admin/dashboard.html', plots_count=plots_count)
    except Exception as e:
        return f"Database Error: {str(e)}. Please restart the server."

@app.route('/admin/change-password', methods=['GET', 'POST'])
@login_required
def admin_change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        user = User.query.get(session['admin_id'])
        if check_password_hash(user.password_hash, form.old_password.data):
            user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            flash("Password updated!", "success")
            return redirect(url_for('admin_dashboard'))
        flash("Incorrect current password", "error")
    return render_template('admin/change_password.html', form=form)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('index'))

# --- DATABASE INITIALIZATION ---
with app.app_context():
    db.create_all()
    # Create default admin if none exists
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('password123')
        default_admin = User(username='admin', password_hash=hashed_pw)
        db.session.add(default_admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
