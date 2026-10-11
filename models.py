from extensions import db
from flask_login import UserMixin
from datetime import datetime, timedelta

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(25), unique=True)
    pwd = db.Column(db.String(150))
    role = db.Column(db.String(10), default='user')
    
    created_tasks = db.relationship('Task', backref='creator', foreign_keys='Task.created_by', lazy=True)
    shared_task = db.relationship('Task', backref='receiver', foreign_keys='Task.shared_with', lazy=True)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='suggested')
    tasks = db.relationship('Task', backref='tag', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True) 
    location = db.Column(db.String(150), nullable=False) 
    status = db.Column(db.String(20), default='active')
    
    startTime = db.Column(db.DateTime, nullable=False)
    max_attendees = db.Column(db.Integer, nullable=False)
    current_attendees = db.Column(db.Integer, default=1)
    
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shared_with = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    @property
    def isActive(self):
        if self.current_attendees >= self.max_attendees:
            return False
        cutoff = self.startTime - timedelta(minutes=1)
        if datetime.now() >= cutoff:
            return False
        return self.status == 'active'