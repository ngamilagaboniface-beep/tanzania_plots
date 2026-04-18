import os
from flask import Flask, render_with_template, request, flash, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, Plot, PlotImage, User
from forms import PlotForm, LoginForm, PasswordChangeForm

# Configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_for_flask_tanzania_plots' # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Admin login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("You must be logged in to view this page.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Context processor to make code logo and company info available to all templates
@app.context_processor
def inject_globals():
    return dict(
        company_name="Tanzania Plots Company Limited",
        tagline="OWN LAND, BUILD YOUR LEGACY",
        phone="0658 200 422",
        email="info@tanzaniaplots.co.tz"
    )

# PUBLIC ROUTES

@app.route('/')
def index():
    plots = Plot.query.filter_by(status='Available').order_by(Plot.id.desc()).limit(3).all()
    return render_with_template('index.html', plots=plots)

@app.route('/properties')
def properties():
    plots = Plot.query.filter_by(status='Available').order_by(Plot.id.desc()).all()
    return render_with_template('properties.html', plots=plots)

@app.route('/property/<int:plot_id>')
def property_detail(plot_id):
    plot = Plot.query.get_or_404(plot_id)
    return render_with_template('property_detail.html', plot=plot)

# ADMIN ROUTES

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session['admin_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    return render_with_template('admin/login.html', form=form)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    plots_count = Plot.query.count()
    users_count = User.query.count()
    return render_with_template('admin/dashboard.html', plots_count=plots_count, users_count=users_count)

@app.route('/admin/plots')
@login_required
def admin_plots():
    plots = Plot.query.order_by(Plot.id.desc()).all()
    return render_with_template('admin/plots.html', plots=plots)

@app.route('/admin/plots/create', methods=['GET', 'POST'])
@login_required
def admin_plot_create():
    form = PlotForm()
    if form.validate_on_submit():
        plot = Plot(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            location=form.location.data,
            sqm_size=form.sqm_size.data,
            status=form.status.data
        )
        db.session.add(plot)
        db.session.commit() # Get plot.id for images

        if 'images' in request.files:
            images = request.files.getlist('images')
            for image in images:
                if image and allowed_file(image.filename):
                    filename = secure_filename(f"plot_{plot.id}_{image.filename}")
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    plot_image = PlotImage(filename=filename, plot=plot)
                    db.session.add(plot_image)
        db.session.commit() # Save images
        flash('Plot created successfully!', 'success')
        return redirect(url_for('admin_plots'))
    return render_with_template('admin/plot_edit.html', form=form, title="Create Plot")

@app.route('/admin/plots/edit/<int:plot_id>', methods=['GET', 'POST'])
@login_required
def admin_plot_edit(plot_id):
    plot = Plot.query.get_or_404(plot_id)
    form = PlotForm(obj=plot)
    if form.validate_on_submit():
        plot.title = form.title.data
        plot.description = form.description.data
        plot.price = form.price.data
        plot.location = form.location.data
        plot.sqm_size = form.sqm_size.data
        plot.status = form.status.data
        db.session.commit()

        # Simple image management: just add new ones for now
        if 'images' in request.files:
            images = request.files.getlist('images')
            for image in images:
                if image and allowed_file(image.filename):
                    filename = secure_filename(f"plot_{plot.id}_{image.filename}")
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    plot_image = PlotImage(filename=filename, plot=plot)
                    db.session.add(plot_image)
            db.session.commit()
        flash('Plot updated successfully!', 'success')
        return redirect(url_for('admin_plots'))
    return render_with_template('admin/plot_edit.html', form=form, title="Edit Plot", plot=plot)

@app.route('/admin/plots/delete/<int:plot_id>')
@login_required
def admin_plot_delete(plot_id):
    plot = Plot.query.get_or_404(plot_id)
    for image in plot.images:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
        db.session.delete(image)
    db.session.delete(plot)
    db.session.commit()
    flash('Plot and its images deleted successfully!', 'success')
    return redirect(url_for('admin_plots'))

@app.route('/admin/change-password', methods=['GET', 'POST'])
@login_required
def admin_change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        user = User.query.get(session['admin_id'])
        if user and check_password_hash(user.password_hash, form.old_password.data):
            user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect old password.', 'error')
    return render_with_template('admin/change_password.html', form=form)

# Create database and first admin user on first run
# Run `python -c "from app import db; db.create_all(); from models import User; from werkzeug.security import generate_password_hash; admin=User(username='admin', password_hash=generate_password_hash('password')); db.session.add(admin); db.session.commit()"`
# in your venv to set up the DB and an admin (username: admin, password: password). Change this immediately.

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Check if an admin user exists, if not create one
        if not User.query.filter_by(username='admin').first():
            from models import User
            from werkzeug.security import generate_password_hash
            default_admin = User(username='admin', password_hash=generate_password_hash('password'))
            db.session.add(default_admin)
            db.session.commit()
            print("Default admin created (username: admin, password: password). Change this immediately.")
    app.run(debug=True, port=5000)
