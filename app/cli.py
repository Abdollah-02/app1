import click
from flask.cli import with_appcontext
from app import db
from app.models.user import User

@click.command('create-user')
@click.argument('username')
@click.argument('password')
@click.argument('role')
@with_appcontext
def create_user(username, password, role):
    """Create a new user."""
    if role not in ['HR', 'DG']:
        click.echo('Role must be either HR or DG')
        return
    
    user = User.query.filter_by(username=username).first()
    if user:
        click.echo(f'User {username} already exists')
        return
    
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Created user {username} with role {role}') 