import datetime
import os

from flask import Flask, flash, redirect, render_template, request, url_for

from astrolog.database import (EyePiece, Filter, Location, Object, Observation,
                               Session, Telescope)

app = Flask(__name__,
            template_folder='templates')
app.secret_key = os.urandom(24)


@app.route('/')
def main():
    return render_template('main.html')


# Sessions
@app.route('/session/new', methods=['GET', 'POST'])
def new_session():
    if request.method == 'POST':
        location = Location.get_or_none(name=request.form.get('location'))
        date = datetime.datetime.strptime(request.form.get('date'), '%Y-%m-%d')
        session, created = Session.get_or_create(location=location, date=date)
        if created:
            flash(f'New session created! {session.id}', category='success')
            return redirect(url_for('new_observation', session_id=session.id))
        flash(f'This session already exists! {session.id}', category='warning')
        return redirect(url_for('new_observation', session_id=session.id))
    return render_template('session_new.html', locations=Location)


@app.route('/observation/new/session/<int:session_id>', methods=['GET', 'POST'])
def new_observation(session_id):
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
        if telescope is None:
            flash(f'Telescope {form.get("telescope")} was not found', category='danger')
            return redirect(url_for('new_observation', session_id=session.id))
        eyepiece = EyePiece.get_or_none(type=form.get('eyepiece'))
        if eyepiece is None:
            flash(f'Eyepiece {form.get("eyepiece")} was not found', category='danger')
            return redirect(url_for('new_observation', session_id=session.id))
        optical_filter = Filter.get_or_none(name=form.get('optic_filter'))
        Observation.create(session=session, object=obj, telescope=telescope,
                           eyepiece=eyepiece, optical_filter=optical_filter,
                           note=form.get('note', None))
        flash('Observation created', category='success')

    return render_template('observation.html', session=session,
                           telescopes=Telescope, eyepieces=EyePiece,
                           optical_filters=Filter)


@app.route('/session/all')
def all_sessions():
    return render_template('sessions.html', sessions=Session)


@app.route('/session/<int:session_id>')
def session(session_id):
    session = Session.get_or_none(session_id)
    if not session:
        flash(f'Session with id {session_id} was not found', category='warning')
        return redirect(url_for('main'))
    return render_template('session.html', session=session)


# Equipments
@app.route('/equipments')
def equipments():
    return render_template('equipments.html', telescopes=Telescope,
                           eyepieces=EyePiece, filters=Filter)


@app.route('/equipments/new/telescope', methods=['POST'])
def new_telescope():
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


@app.route('/equipments/new/eyepiece', methods=['POST'])
def new_eyepiece():
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
def new_filter():
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
def locations():
    return render_template('locations.html', locations=Location)


@app.route('/locations/new', methods=['POST'])
def new_location():
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # pragma: no cover
