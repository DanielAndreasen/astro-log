import os

from flask import Flask, flash, redirect, render_template, url_for

from astrolog.database import Session

app = Flask(__name__,
            template_folder='templates')
app.secret_key = os.urandom(24)


@app.route('/')
def main():
    return render_template('main.html')


@app.route('/session/<int:session_id>')
def session(session_id):
    session = Session.get_or_none(session_id)
    if not session:
        flash(f'Session with id {session_id} was not found', category='warning')
        return redirect(url_for('main'))
    return render_template('session.html', session=session)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # pragma: no cover
