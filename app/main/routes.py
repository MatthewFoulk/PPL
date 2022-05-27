
from flask import Blueprint, current_app, redirect, render_template, request
from flask_login import current_user, login_required

from app.main import bp
from app.models import User

@bp.route('/')
@bp.route('/index')
@bp.route('/home')
def index():
    return render_template('index.html')


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)


