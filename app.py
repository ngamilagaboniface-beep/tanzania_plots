import os
from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, Plot, PlotImage, User
from forms import PlotForm, LoginForm, PasswordChangeForm
from PIL import Image

app = Flask(__name__)

# CONFIGURATION
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tanzania_plots_secure_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        default_admin = User(username='admin', password_hash=generate_password_hash('password'))
        db.session.add(default_admin)
        db.session.commit()

# DECORATORS & FILTERS
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Please login to access the admin panel.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.template_filter('format_currency')
def format_currency(value):
    try:
        if isinstance(value, str):
            value = value.replace(',', '').replace(' ', '')
        return "{:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return "0"

@app.context_processor
def inject_globals():
    return dict(phone="0658 200 422", email="info@tanzaniaplots.co.tz")

# PUBLIC ROUTES
@app.route('/')
def index():
    plots = Plot.query.filter_by(status='Available').order_by(Plot.id.desc()).all()
    return render_template('index.html', plots=plots)

@app.route('/properties')
def properties():
    query = Plot.query
    location = request.args.get('location')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    if location:
        query = query.filter(Plot.location.ilike(f'%{location}%'))
    if min_price:
        query = query.filter(Plot.price >= min_price)
    if max_price:
        query = query.filter(Plot.price <= max_price)
        
    plots = query.order_by(Plot.id.desc()).all()
    return render_template('properties.html', plots=plots)

@app.route('/property/<int:plot_id>')
def property_detail(plot_id):
    plot = Plot.query.get_or_404(plot_id)
    return render_template('property_detail.html', plot=plot)

# ADMIN ROUTES
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session['admin_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('admin/login.html', form=form)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    plots_count = Plot.query.count()
    return render_template('admin/dashboard.html', plots_count=plots_count)

@app.route('/admin/change-password', methods=['GET', 'POST'])
@login_required
def admin_change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        user = User.query.get(session['admin_id'])
        if check_password_hash(user.password_hash, form.old_password.data):
            user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Old password incorrect.', 'error')
    return render_template('admin/change_password.html', form=form)

@app.route('/admin/plots/create', methods=['GET', 'POST'])
@login_required
def admin_plot_create():
    form = PlotForm()
    if form.validate_on_submit():
        try:
            plot = Plot(
                title=form.title.data, description=form.description.data, 
                price=form.price.data, location=form.location.data, 
                sqm_size=form.sqm_size.data, status=form.status.data
            )
            db.session.add(plot)
            db.session.flush() 
            
            images = request.files.getlist('images')
            for image in images:
                if image and image.filename != '':
                    filename = secure_filename(f"{plot.id}_{image.filename}")
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    img = Image.open(image)
                    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                    img.thumbnail((1024, 1024))
                    img.save(image_path, optimize=True, quality=75)
                    db.session.add(PlotImage(filename=filename, plot_id=plot.id))
            
            db.session.commit()
            flash('Property published!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception:
            db.session.rollback()
            flash('Error uploading.', 'error')
    return render_template('admin/plot_edit.html', form=form, title="Add Property")

if __name__ == '__main__':
    app.run(debug=True)
