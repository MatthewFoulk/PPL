import base64
from datetime import datetime, timedelta
import os

from flask import current_app
from flask_login import UserMixin
import jwt
from sqlalchemy import false
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login
from app.search import add_to_index, remove_from_index, query_index

class SearchableMixin():
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        
        # No matching entries found
        if total == 0:
            return cls.query.filter_by(id=0), 0

        # Constructing the 'when' part of a SQL case statement
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))

        # Uses a case statement to preserve the order
        # returned from the full-text search 
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    
    @classmethod
    def before_commit(cls, session):

        # Saving the information regarding database changes
        # prior to commmitting
        # Write to _changes because it will survive the commit
        session._changes = {
            'add': list(session.new), # objects to add
            'update': list(session.dirty), # objects to modify
            'delete': list(session.deleted) # objects to delete
        }
    

    @classmethod
    def after_commit(cls, session):
        # Modify full-text search indexing after commit
        # to database

        # Add a new obj
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        
        # Modify an older one, by overwriting it
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        
        # Remove an obj from the index
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        
        # Clear the _changes dict
        session._changes = None

    
    @classmethod
    def reindex(cls):
        # Helper method, used to refresh an index with
        # all the data from the relational side
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)

    workouts = db.relationship("Workout", backref="creator", lazy="dynamic")

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)
    
    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token
    
    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None
        return user

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Workout(db.Model):
    __tablename__ = "workout"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __repr__(self):
        return '<Workout {}>'.format(self.name)


class Exercise(db.Model):
    __tablename__ = "exercise"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    def __repr__(self):
        return '<Exercise {}>'.format(self.name)

# Workouts with Exercises Table (many-to-many)
class WorkoutExercises(db.Model):
    __tablename__ = "workout_exercises"

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    sets = db.Column(db.Integer)
    reps_min = db.Column(db.Integer)
    reps_max = db.Column(db.Integer)
    superset = db.Column(db.Integer, db.ForeignKey('exercise.id'))
    exercise_num = db.Column(db.Integer)
    warmup = db.Column(db.Boolean, default=False)
    rest =db.Column(db.Integer)

    exercise = db.relationship(Exercise, backref="workouts")
    workout = db.relationship(Workout, backref="exercises")
    superset = db.relationship(Exercise, backref="supersets")

    def __repr__(self):
        return '<Workout {} Exercise {}>'.format(
            Workout.query.get(self.workout_id), 
            Exercise.query.get(self.exercise_id))
