import os
from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'tanzania_plots_2026_safe'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# --- MODELS ---
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

# --- FILTERS & GLOBALS ---
@app.template_filter('format_currency')
def format_currency(value):
    try:
        if value is None: return "0"
        return "{:,.0f}".format(float(value))
    except:
        return "0"

@app.context_processor
def inject_globals():
    return dict(phone="0658 200 422", email="info@tanzaniaplots.co.tz")

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
    try:
        plot = Plot.query.get_or_404(plot_id)
        return render_template('property_detail.html', plot=plot)
    except Exception as e:
        return f"Database Error on Property Detail: {str(e)}"

# --- ADMIN ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'password':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials. Try again.', 'error')
    return render_template('admin/login.html')

# THE MISSING ROUTE THAT CAUSED THE 500 ERROR
@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    # Kick out users who aren't logged in
    if 'logged_in' not in session: 
        return redirect(url_for('admin_login'))
    
    try:
        plots_count = Plot.query.count()
        return render_template('admin/dashboard.html', plots_count=plots_count)
    except Exception as e:
        return f"Database Error on Dashboard: {str(e)}"

@app.route('/admin/plots/create', methods=['GET', 'POST'])
def admin_plot_create():
    # Kick out users who aren't logged in
    if 'logged_in' not in session: 
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            plot = Plot(
                title=request.form.get('title'),
                location=request.form.get('location'),
                price=float(request.form.get('price', 0)),
                sqm_size=request.form.get('sqm_size'),
                status=request.form.get('status', 'Available'),
                description=request.form.get('description')
            )
            db.session.add(plot)
            db.session.flush() # Get the ID before saving images
            
            images = request.files.getlist('images')
            for img in images:
                if img and img.filename != '':
                    filename = secure_filename(f"{plot.id}_{img.filename}")
                    img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    db.session.add(PlotImage(filename=filename, plot_id=plot.id))
            
            db.session.commit()
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            return f"Error creating property: {str(e)}"
            
    return render_template('admin/plot_edit.html')

# --- INITIALIZE DB ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
