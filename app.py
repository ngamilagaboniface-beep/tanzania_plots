import os
from flask import Flask, render_template, request, flash, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, Plot, PlotImage, User
from forms import PlotForm, LoginForm, PasswordChangeForm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Please log in to access the admin panel.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_globals():
    return dict(
        company_name="Tanzania Plots Company Limited",
        phone="0658 200 422",
        email="info@tanzaniaplots.co.tz"
    )

# --- PUBLIC ROUTES ---

@app.route('/')
def index():
    # Fetch all available plots for the slideshow
    all_plots = Plot.query.filter_by(status='Available').order_by(Plot.id.desc()).all()
    return render_template('index.html', plots=all_plots)

@app.route('/properties')
def properties():
    all_plots = Plot.query.filter_by(status='Available').order_by(Plot.id.desc()).all()
    return render_template('properties.html', plots=all_plots)

@app.route('/property/<int:plot_id>')
def property_detail(plot_id):
    plot = Plot.query.get_or_404(plot_id)
    return render_template('property_detail.html', plot=plot)

# --- ADMIN ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session['admin_id'] = user.id
            flash('Welcome back!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('admin/login.html', form=form)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template('admin/dashboard.html', plots_count=Plot.query.count())

@app.route('/admin/plots')
@login_required
def admin_plots():
    plots = Plot.query.order_by(Plot.id.desc()).all()
    return render_template('admin/plots.html', plots=plots)

@app.route('/admin/plots/create', methods=['GET', 'POST'])
@login_required
def admin_plot_create():
    form = PlotForm()
    if form.validate_on_submit():
        plot = Plot(title=form.title.data, description=form.description.data, 
                    price=form.price.data, location=form.location.data, 
                    sqm_size=form.sqm_size.data, status=form.status.data)
        db.session.add(plot)
        db.session.commit()

        images = request.files.getlist('images')
        for img in images:
            if img:
                filename = secure_filename(f"{plot.id}_{img.filename}")
                img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db.session.add(PlotImage(filename=filename, plot=plot))
        db.session.commit()
        flash('Plot added!', 'success')
        return redirect(url_for('admin_plots'))
    return render_template('admin/plot_edit.html', form=form, title="New Plot")

@app.route('/admin/change-password', methods=['GET', 'POST'])
@login_required
def admin_change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        user = User.query.get(session['admin_id'])
        if check_password_hash(user.password_hash, form.old_password.data):
            user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            flash('Password updated!', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin/change_password.html', form=form)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password_hash=generate_password_hash('password')))
            db.session.commit()
    app.run(debug=True)
