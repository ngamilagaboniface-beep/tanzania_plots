from flask_sqlalchemy import SQLAlchemy
from flask import current_app

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Plot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    sqm_size = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Available', nullable=False) # Available or Sold
    images = db.relationship('PlotImage', backref='plot', lazy=True, cascade='all, delete-orphan')

class PlotImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    plot_id = db.Column(db.Integer, db.ForeignKey('plot.id'), nullable=False)

    @property
    def url(self):
        return f"/static/uploads/{self.filename}"
