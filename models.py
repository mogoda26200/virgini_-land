from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
db = SQLAlchemy()
now = datetime.utcnow
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now)
class GoldPrice(db.Model):  # every fetch is stored: doubles as history
    id = db.Column(db.Integer, primary_key=True)
    karat = db.Column(db.Integer, index=True)
    price_per_gram = db.Column(db.Float)
    source = db.Column(db.String(20), default="api")
    updated_at = db.Column(db.DateTime, default=now, index=True)
class Holding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    karat = db.Column(db.Integer)
    weight = db.Column(db.Float)
    purchase_price = db.Column(db.Float)  # per gram
    purchase_date = db.Column(db.Date)
    fees = db.Column(db.Float, default=0)
class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    karat = db.Column(db.Integer)
    target_price = db.Column(db.Float)
    condition = db.Column(db.String(10))  # above | below
    status = db.Column(db.String(10), default="active")  # active|triggered|disabled
    created_at = db.Column(db.DateTime, default=now)
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    title = db.Column(db.String(120))
    message = db.Column(db.String(300))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now)
