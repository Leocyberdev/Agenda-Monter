from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from src.database import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

    def get_reset_token(self, expires_sec=1800):
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app
        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"],
            salt=current_app.config.get("SECURITY_PASSWORD_SALT", "password-reset-salt")
        )
        return serializer.dumps({"user_id": self.id})

    @staticmethod
    def verify_reset_token(token, max_age=1800):
        from itsdangerous import URLSafeTimedSerializer, BadData
        from flask import current_app
        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"],
            salt=current_app.config.get("SECURITY_PASSWORD_SALT", "password-reset-salt")
        )
        try:
            data = serializer.loads(token, max_age=max_age)
        except BadData:
            return None
        return User.query.get(data["user_id"])

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    capacity = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'capacity': self.capacity,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<Room {self.name}>'
