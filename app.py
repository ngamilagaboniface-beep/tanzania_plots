import os
from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'tanzania_plots_secure_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class Plot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, default=0.0)
    location = db.Column(db.String(200))
    sqm_size = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Available')
    images = db.relationship('PlotImage', backref='plot', lazy=True, cascade="all, delete-orphan")

class PlotImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    plot_id = db.Column(db.Integer, db.ForeignKey('plot.id'), nullable=False)

# --- THE 500 ERROR FIX (CURRENCY FILTER) ---
@app.template_filter('format_currency')
def format_currency(value):
    try:
        if value is None: return "0"
        if isinstance(value, str):
            value = value.replace(',', '').replace(' ', '')
        return "{:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return "0"

@app.context_processor
def inject_globals():
    return dict(phone="0658 200 422", email="info@tanzaniaplots.co.tz")

# --- LOGIN PROTECTION ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash("Please login first.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    plots = Plot.query.filter_by(status='Available').order_by(Plot.id.desc()).all()
    return render_template('index.html', plots=plots)

@app.route('/properties')
def properties():
    plots = Plot.query.order_by(Plot.id.desc()).all()
    return render_template('properties.html', plots=plots)

@app.route('/property/<int:plot_id>')
def property_detail(plot_id):
    plot = Plot.query.get_or_404(plot_id)
    return render_template('property_detail.html', plot=plot)

# --- ADMIN ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        # Simple, fast login without complex form validators
        if request.form.get('username') == 'admin' and request.form.get('password') == 'password':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    plots_count = Plot.query.count()
    return render_template('admin/dashboard.html', plots_count=plots_count)

@app.route('/admin/plots/create', methods=['GET', 'POST'])
@login_required
def admin_plot_create():
    if request.method == 'POST':
        try:
            # Safely handle the price to prevent math crashes
            raw_price = request.form.get('price', '0')
            clean_price = float(raw_price.replace(',', '').replace(' ', '')) if raw_price else 0.0
            
            plot = Plot(
                title=request.form.get('title'),
                location=request.form.get('location'),
                price=clean_price,
                sqm_size=request.form.get('sqm_size'),
                status=request.form.get('status'),
                description=request.form.get('description')
            )
            db.session.add(plot)
            db.session.flush()

            # Handle basic image uploads
            images = request.files.getlist('images')
            for image in images:
                if image and image.filename != '':
                    filename = secure_filename(f"{plot.id}_{image.filename}")
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(image_path) 
                    db.session.add(PlotImage(filename=filename, plot_id=plot.id))

            db.session.commit()
            flash('Property published successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading property: {str(e)}', 'error')
            
    return render_template('admin/plot_edit.html')

# --- INITIALIZE DB ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
