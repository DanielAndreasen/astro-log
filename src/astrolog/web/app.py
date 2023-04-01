import datetime
import os

from flask import Flask, flash, redirect, render_template, request, url_for
from peewee import SqliteDatabase

from astrolog.api import create_observation, delete_location
from astrolog.database import (MODELS, Binocular, EyePiece, Filter, Location,
                               Object, Session, Telescope, database_proxy)

app = Flask(__name__, template_folder='templates')
app.secret_key = os.urandom(24)


@app.route('/')
def main() -> str:
    return render_template('main.html')


# Sessions
@app.route('/session/new', methods=['GET', 'POST'])
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
        if not (magnitude := form.get('magnitude', None)):
            flash('Object magnitude must be provided', category='danger')
            return redirect(url_for('new_observation', session_id=session.id))
        obj, new_object = Object.get_or_create(name=obj, magnitude=magnitude)
        if new_object:
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
                           optical_filters=Filter)


@app.route('/session/all')
def all_sessions() -> str:
    return render_template('sessions.html', sessions=Session)


@app.route('/session/<int:session_id>')
def session(session_id: int) -> str:
    session = Session.get_or_none(session_id)
    if not session:
        flash(f'Session with id {session_id} was not found', category='warning')
        return redirect(url_for('main'))
    return render_template('session.html', session=session)


# Equipments
@app.route('/equipments')
def equipments() -> str:
    return render_template('equipments.html', telescopes=Telescope,
                           eyepieces=EyePiece, filters=Filter, binoculars=Binocular)


@app.route('/equipments/new/telescope', methods=['POST'])
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
def locations() -> str:
    return render_template('locations.html', locations=Location)


@app.route('/locations/alter', methods=['POST'])
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

    app.run(host='0.0.0.0', port=5000, debug=True)
