import os
from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, Plot, PlotImage, User
from forms import PlotForm, LoginForm, PasswordChangeForm

app = Flask(__name__)

# ==========================================
# CONFIGURATION
# ==========================================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tanzania_plots_secure_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Database
db.init_app(app)

# AUTO-DB CREATION FOR RENDER
with app.app_context():
    db.create_all()
    # Create default admin if none exists
    if not User.query.filter_by(username='admin').first():
        default_admin = User(username='admin', password_hash=generate_password_hash('password'))
        db.session.add(default_admin)
        db.session.commit()

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Please login to access the admin panel.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_globals():
    # Makes these variables available in every HTML template automatically
    return dict(phone="0658 200 422", email="info@tanzaniaplots.co.tz")

# ==========================================
# PUBLIC ROUTES
# ==========================================
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

# ==========================================
# ADMIN AUTHENTICATION ROUTES
# ==========================================
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
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

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
    return render_template('admin/change_password.html', form=form, title="Change Password")

# ==========================================
# ADMIN DASHBOARD & MANAGEMENT ROUTES
# ==========================================
@app.route('/admin')
@login_required
def admin_dashboard():
    plots_count = Plot.query.count()
    return render_template('admin/dashboard.html', plots_count=plots_count)

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
        try:
            # 1. Create the plot object
            plot = Plot(
                title=form.title.data, 
                description=form.description.data, 
                price=form.price.data, 
                location=form.location.data, 
                sqm_size=form.sqm_size.data, 
                status=form.status.data
            )
            db.session.add(plot)
            
            # 2. Flush to securely generate the Plot ID without a full commit
            db.session.flush() 
            
            # 3. Handle multiple image uploads securely
            images = request.files.getlist('images')
            for image in images:
                if image and image.filename != '':
                    filename = secure_filename(f"{plot.id}_{image.filename}")
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(image_path)
                    
                    # Link image to the plot in the database
                    db.session.add(PlotImage(filename=filename, plot_id=plot.id))
            
            # 4. Commit everything together safely
            db.session.commit()
            flash('Property successfully published!', 'success')
            return redirect(url_for('admin_plots'))
            
        except Exception as e:
            # Cancel the save if something crashes to prevent database corruption
            db.session.rollback() 
            flash('Server error during upload. Please try again with smaller images.', 'error')
            print(f"Upload Error: {str(e)}") # This prints to Render's event logs
            
    return render_template('admin/plot_edit.html', form=form, title="Add Property")

# ==========================================
# APP EXECUTION
# ==========================================
if __name__ == '__main__':
    app.run(debug=True)
