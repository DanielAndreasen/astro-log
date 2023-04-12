import datetime
import os
from functools import wraps
from typing import Any

from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)
from peewee import IntegrityError, SqliteDatabase

from astrolog.api import (create_observation, create_user, delete_location,
                          valid_login)
from astrolog.database import (MODELS, AltName, Binocular, EyePiece, Filter,
                               Location, Object, Session, Telescope, User,
                               database_proxy)

app = Flask(__name__, template_folder='templates')
app.secret_key = os.urandom(24)


def login_required(f: Any) -> Any:
    @wraps(f)
    def wrap(*args: Any, **kwargs: Any) -> Any:
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("You need to login first", category='danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/')
def main() -> str:
    if not User.select().count():
        return redirect(url_for('create_user_page'))
    return render_template('main.html')


@app.route('/create_user', methods=['GET', 'POST'])
def create_user_page() -> str:
    if request.method == 'POST':
        try:
            create_user(username=request.form.get('username'),
                        password=request.form.get('password'))
            return redirect(url_for('login'))
        except ValueError:
            flash('Both username and password are required. Password should be minimum 8 characters long', category='danger')
            return redirect(url_for('create_user_page'))
    return render_template('create_user.html')


@app.route('/login', methods=['GET', 'POST'])
def login() -> str:
    if request.method == 'POST':
        form = request.form
        if 'logout' in form.keys():
            del session['logged_in']
            flash('You are now logged out', category='success')
            return redirect(url_for('main'))
        if valid_login(username=form.get('username'), password=form.get('password')):
            session['logged_in'] = True
            flash('You are now logged in', category='success')
            return redirect(url_for('main'))
        else:
            flash('Wrong username and/or password', category='danger')
    return render_template('login.html', logged_in=session.get('logged_in'))


# Sessions
@app.route('/session/new', methods=['GET', 'POST'])
@login_required
def new_session() -> str:
    if request.method == 'POST':
        location = Location.get_or_none(name=request.form.get('location'))
        date = datetime.datetime.strptime(request.form.get('date'), '%Y-%m-%d')
        session, created = Session.get_or_create(location=location, date=date)
        if created:
            flash('New session created!', category='success')
            return redirect(url_for('new_observation', session_id=session.id))
        flash('This session already exists!', category='warning')
        return redirect(url_for('new_observation', session_id=session.id))
    return render_template('session_new.html', locations=Location)


@app.route('/observation/new/session/<int:session_id>', methods=['GET', 'POST'])
@login_required
def new_observation(session_id: int) -> str:
    session = Session.get_or_none(session_id)
    if not session:
        flash(f'Session with id {session_id} was not found', category='warning')
        return redirect(url_for('main'))
    if request.method == 'POST':
        form = request.form
        if not (obj := form.get('object', None)):
            flash('Object name must be provided', category='danger')
            return redirect(url_for('new_observation', session_id=session.id))
        favourite = form.get('favourite') == ''
        obj, _ = Object.get_or_create(name=obj)
        obj.favourite = favourite
        obj.save()
        if obj.to_be_watched:
            flash(f'Congratulations! First time observing {obj.name}', category='success')
        telescope = Telescope.get_or_none(name=form.get('telescope'))
        eyepiece = EyePiece.get_or_none(type=form.get('eyepiece'))
        optic_filter = Filter.get_or_none(name=form.get('optic_filter'))
        binocular = Binocular.get_or_none(name=form.get('binocular'))
        try:
            create_observation(session=session, object=obj,
                               telescope=telescope, eyepiece=eyepiece, optic_filter=optic_filter,
                               binocular=binocular, note=form.get('note', None))
        except ValueError:
            flash('Unable to create observation. Do not mix things that are not supposed to be mixed and try again')
            return redirect(url_for('new_observation', session_id=session_id))
        flash('Observation created', category='success')

    return render_template('observation.html', session=session,
                           telescopes=Telescope, eyepieces=EyePiece,
                           optical_filters=Filter, binoculars=Binocular)


@app.route('/session/all')
@login_required
def all_sessions() -> str:
    return render_template('sessions.html', sessions=Session)


@app.route('/session/<int:session_id>')
@login_required
def session_page(session_id: int) -> str:
    session = Session.get_or_none(session_id)
    if not session:
        flash(f'Session with id {session_id} was not found', category='warning')
        return redirect(url_for('main'))
    return render_template('session.html', session=session)


# Objects
@app.route('/objects', methods=['GET', 'POST'])
@login_required
def objects() -> str:
    if request.method == 'POST':
        form = request.form
        match len(form):
            case 1:
                # Toggle favourite
                object = Object.get(int(form.get('toggle_favourite')))
                object.toggle_favourite()
            case _:
                # Adding a new object
                name = form.get('object')
                favourite = form.get('favourite') == ''
                if Object.get_or_none(name=name):
                    flash('Object has already been observed', category='warning')
                else:
                    Object.get_or_create(name=name, favourite=favourite, to_be_watched=True)
    return render_template('objects.html', objects=Object)


@app.route('/objects/alt_name', methods=['POST'])
@login_required
def add_alt_name() -> str:
    form = request.form
    object = Object.get(name=form.get('object'))
    if alt_name := form.get('alt-name'):
        try:
            AltName.create(object=object, name=alt_name)
        except IntegrityError:
            alt = AltName.get(name=alt_name)
            flash(f'"{alt.object.name}" already has this as an alternative name', category='danger')
            return redirect(url_for('objects'))
        flash(f'Successfully added alternative name: {alt_name} to {object.name}', category='success')
    else:
        flash('Cannot add empty alternative name', category='warning')
    return redirect(url_for('objects'))


# Equipments
@app.route('/equipments')
@login_required
def equipments() -> str:
    return render_template('equipments.html', telescopes=Telescope,
                           eyepieces=EyePiece, filters=Filter, binoculars=Binocular)


@app.route('/equipments/new/telescope', methods=['POST'])
@login_required
def new_telescope() -> str:
    if request.method == 'POST':
        form = request.form
        if not (name := form.get('name', None)):
            flash('Telescope name must be provided', category='danger')
            return redirect(url_for('equipments'))
        if not (aperture := form.get('aperture', None)):
            flash('Telescope aperture must be provided', category='danger')
            return redirect(url_for('equipments'))
        if not (focal_length := form.get('focal_length', None)):
            flash('Telescope focal length must be provided', category='danger')
            return redirect(url_for('equipments'))
        telescope, created = Telescope.get_or_create(name=name, aperture=aperture, focal_length=focal_length)
        if created:
            flash(f'Telescope "{telescope.name}" was created', category='success')
        else:
            flash(f'Telescope "{telescope.name}" already exists', category='warning')
    return redirect(url_for('equipments'))


@app.route('/equipments/new/binocular', methods=['POST'])
@login_required
def new_binocular() -> str:
    if request.method == 'POST':
        form = request.form
        if not (name := form.get('name', None)):
            flash('Binocular name must be provided', category='danger')
            return redirect(url_for('equipments'))
        if not (aperture := form.get('aperture', None)):
            flash('Binocular aperture must be provided', category='danger')
            return redirect(url_for('equipments'))
        if not (magnification := form.get('magnification', None)):
            flash('Binocular magnification must be provided', category='danger')
            return redirect(url_for('equipments'))
        binocular, created = Binocular.get_or_create(name=name, aperture=aperture, magnification=magnification)
        if created:
            flash(f'Binocular "{binocular.name}" was created', category='success')
        else:
            flash(f'Binocular "{binocular.name}" already exists', category='warning')
    return redirect(url_for('equipments'))


@app.route('/equipments/new/eyepiece', methods=['POST'])
@login_required
def new_eyepiece() -> str:
    if request.method == 'POST':
        form = request.form
        if not (type_ := form.get('type', None)):
            flash('Eyepiece type must be provided', category='danger')
            return redirect(url_for('equipments'))
        if not (focal_length := form.get('focal_length', None)):
            flash('Eyepiece focal length must be provided', category='danger')
            return redirect(url_for('equipments'))
        if not (width := form.get('width', None)):
            flash('Eyepiece width must be provided', category='danger')
            return redirect(url_for('equipments'))
        eyepiece, created = EyePiece.get_or_create(type=type_, focal_length=focal_length, width=width)
        if created:
            flash(f'Eyepiece "{eyepiece.type}" was created', category='success')
        else:
            flash(f'Eyepiece "{eyepiece.type}" already exists', category='warning')
    return redirect(url_for('equipments'))


@app.route('/equipments/new/filter', methods=['POST'])
@login_required
def new_filter() -> str:
    if request.method == 'POST':
        form = request.form
        if not (name := form.get('name', None)):
            flash('Filter name must be provided', category='danger')
            return redirect(url_for('equipments'))
        filter_, created = Filter.get_or_create(name=name)
        if created:
            flash(f'Eyepiece "{filter_.name}" was created', category='success')
        else:
            flash(f'Eyepiece "{filter_.name}" already exists', category='warning')
    return redirect(url_for('equipments'))


# Locations
@app.route('/locations')
@login_required
def locations() -> str:
    return render_template('locations.html', locations=Location)


@app.route('/locations/alter', methods=['POST'])
@login_required
def alter_location() -> str:
    form = request.form
    for action, location_id in form.items():
        location = Location.get(int(location_id))
        match action:
            case 'delete':
                if delete_location(location):
                    flash(f'Successfully deleted: {location.name} ({location.country})', category='success')
                else:
                    flash(f'Could not delete because of observation there: {location.name} ({location.country})', category='warning')
    return redirect(url_for('locations'))


@app.route('/locations/new', methods=['POST'])
@login_required
def new_location() -> str:
    form = request.form
    if not (name := form.get('name', None)):
        flash('Name must be provided', category='danger')
        return redirect(url_for('locations'))
    if not (country := form.get('country', None)):
        flash('Cuntry must be provided', category='danger')
        return redirect(url_for('locations'))
    if not (latitude := form.get('latitude', None)):
        flash('Latitude must be provided', category='danger')
        return redirect(url_for('locations'))
    if not (longitude := form.get('longitude', None)):
        flash('Longitude must be provided', category='danger')
        return redirect(url_for('locations'))
    if not (altitude := form.get('altitude', None)):
        flash('Altitude must be provided', category='danger')
        return redirect(url_for('locations'))
    location, created = Location.get_or_create(name=name, country=country,
                                               latitude=latitude, longitude=longitude, altitude=altitude)
    if created:
        flash(f'Location "{location.name}" was created', category='success')
    else:
        flash(f'Location "{location.name}" already exists', category='warning')
    return redirect(url_for('locations'))


if __name__ == '__main__':  # pragma: no cover
    # Setup DB
    DEFAULT_DB = os.path.join(os.path.abspath('.'), 'AstroLog.db')
    ASTRO_LOG_DB = os.getenv('ASTRO_LOG_DB', DEFAULT_DB)
    db = SqliteDatabase(ASTRO_LOG_DB)
    database_proxy.initialize(db)
    db.create_tables(MODELS)

    app.run(host='0.0.0.0', port=5065, debug=True)
