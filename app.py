import os
from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'tanzania_plots_final_v1'
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
    price = db.Column(db.Float, default=0.0) # Ensure this exists!
    location = db.Column(db.String(200))
    sqm_size = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Available')
    images = db.relationship('PlotImage', backref='plot', lazy=True, cascade="all, delete-orphan")

class PlotImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    plot_id = db.Column(db.Integer, db.ForeignKey('plot.id'), nullable=False)

# --- FILTER ---
@app.template_filter('format_currency')
def format_currency(value):
    try:
        if value is None: return "0"
        return "{:,.0f}".format(float(value))
    except:
        return "0"

# --- ROUTES ---
@app.route('/property/<int:plot_id>')
def property_detail(plot_id):
    try:
        plot = Plot.query.get_or_404(plot_id)
        return render_template('property_detail.html', plot=plot)
    except Exception as e:
        # This will show you the real error on the webpage if it fails
        return f"Database Error: {str(e)}. Try deleting site.db and redeploying."

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'password':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid login', 'error')
    return render_template('admin/login.html')

# Add all other routes (index, admin_dashboard, etc.) as provided in the previous step
# ... (Keeping it short for clarity)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
