from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# We initialize the db object here, but we don't link it to the app yet
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True) # Mandatory for records
    phone = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(100), nullable=True)
    is_host = db.Column(db.Boolean, default=False) # NEW: Distinguishes Coaches from Students
    is_guest = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scores = db.relationship('Score', backref='user', lazy=True)

class Lobby(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pin = db.Column(db.String(4), unique=True, nullable=False)
    host_id = db.Column(db.Integer, nullable=False) # Link to the Coach's ID
    is_active = db.Column(db.Boolean, default=True)

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Integer, default=0)
    month_year = db.Column(db.String(7), nullable=False) # For monthly "Price" tracking
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)