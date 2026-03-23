import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'TZ_PLOTS_MASTER_PRO_2026')

# Cloudinary Setup
cloudinary.config(
  cloud_name = os.environ.get('CLOUDINARY_NAME'),
  api_key = os.environ.get('CLOUDINARY_API_KEY'),
  api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

# Database Setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'tanzania_plots.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(50)) 
    title = db.Column(db.String(100))
    price = db.Column(db.Float)
    features = db.Column(db.Text)
    image_url = db.Column(db.String(500))

class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_phone = db.Column(db.String(20))
    property_name = db.Column(db.String(100))
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(id): return User.query.get(int(id))

# --- INITIALIZATION ---
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password='tz plots'))
        db.session.commit()

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    loc = request.args.get('location')
    prop_query = Property.query
    if loc: prop_query = prop_query.filter_by(location=loc)
    locations = [l[0] for l in db.session.query(Property.location).distinct().all() if l[0]]
    return render_template('index.html', properties=prop_query.all(), locations=locations)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Namba au Nywila sio sahihi')
    return render_template('login.html')

# --- ADMIN ROUTES ---
@app.route('/admin')
@login_required
def admin_dashboard():
    properties = Property.query.order_by(Property.id.desc()).all()
    inquiries = Inquiry.query.order_by(Inquiry.date_created.desc()).all()
    return render_template('admin.html', properties=properties, inquiries=inquiries)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    upload_result = cloudinary.uploader.upload(file)
    new_item = Property(location=request.form.get('loc'), title=request.form.get('name'), 
                        price=float(request.form.get('price')), features=request.form.get('desc'), 
                        image_url=upload_result['secure_url'])
    db.session.add(new_item)
    db.session.commit()
    flash('Kiwanja kimewekwa hewani!')
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_property/<int:id>', methods=['POST'])
@login_required
def delete_property(id):
    prop = Property.query.get_or_404(id)
    db.session.delete(prop)
    db.session.commit()
    flash('Kiwanja kimeondolewa kikamilifu.')
    return redirect(url_for('admin_dashboard'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    old_pw = request.form.get('old_password')
    new_pw = request.form.get('new_password')
    if current_user.password == old_pw:
        current_user.password = new_pw
        db.session.commit()
        flash('Nywila imebadilishwa!')
    else:
        flash('Nywila ya zamani si sahihi!')
    return redirect(url_for('admin_dashboard'))

@app.route('/inquire/<int:id>', methods=['POST'])
def inquire(id):
    item = Property.query.get(id)
    new_inq = Inquiry(client_phone=request.form.get('phone'), property_name=item.title)
    db.session.add(new_inq)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
