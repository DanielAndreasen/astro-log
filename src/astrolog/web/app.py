import datetime
import os

from flask import Flask, flash, redirect, render_template, request, url_for

from astrolog.database import Location, Session

app = Flask(__name__,
            template_folder='templates')
app.secret_key = os.urandom(24)


@app.route('/')
def main():
    return render_template('main.html')


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


@app.route('/session/<int:session_id>')
def session(session_id):
    session = Session.get_or_none(session_id)
    if not session:
        flash(f'Session with id {session_id} was not found', category='warning')
        return redirect(url_for('main'))
    return render_template('session.html', session=session)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # pragma: no cover
