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
    is_guest = db.Column(db.Boolean, default=True)
    is_host = db.Column(db.Boolean, default=False) # ADDED: Required for Coach/Host accounts
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scores = db.relationship('Score', backref='user', lazy=True)

class Lobby(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pin = db.Column(db.String(4), unique=True, nullable=False)
    host_id = db.Column(db.Integer, nullable=False) # Link to the Coach's ID
    is_active = db.Column(db.Boolean, default=True)

class Score(db.Model):
    # FIXED: This block MUST be indented (4 spaces)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Integer, default=0)
    month_year = db.Column(db.String(7), nullable=False) # For monthly tracking
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)

    # Add this to the bottom of models.py

class QuestionSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # This links the set to its individual questions
    questions = db.relationship('Question', backref='set', lazy=True, cascade="all, delete-orphan")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    set_id = db.Column(db.Integer, db.ForeignKey('question_set.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_index = db.Column(db.Integer, nullable=False) # 0 to 3