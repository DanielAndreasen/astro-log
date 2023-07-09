import datetime
import os
from functools import wraps
from typing import Any

import astropy.units as u
import matplotlib.pyplot as plt
import mpld3
import numpy as np
from astropy.coordinates import AltAz, SkyCoord, get_body, get_sun
from astropy.coordinates.name_resolve import NameResolveError
from astropy.time import Time
from astropy.visualization import quantity_support
from flask import Flask, flash, redirect, render_template, request, session, url_for
from peewee import JOIN, IntegrityError, SqliteDatabase
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename

from astrolog.api import create_observation, create_user, delete_location, valid_login
from astrolog.database import (
    MODELS,
    AltName,
    Barlow,
    Binocular,
    EyePiece,
    Filter,
    FrontFilter,
    Image,
    Location,
    Object,
    Observation,
    Session,
    Structure,
    Telescope,
    User,
    database_proxy,
)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
app = Flask(__name__, template_folder="templates")
app.secret_key = os.urandom(24)
app.config["UPLOAD_FOLDER"] = os.path.join(app.static_folder, "uploads")


def login_required(f: Any) -> Any:
    @wraps(f)
    def wrap(*args: Any, **kwargs: Any) -> Any:
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("You need to login first", category="danger")
            return redirect(url_for("login"))

    return wrap


def allowed_file(fname: str) -> bool:
    return "." in fname and fname.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def main() -> str:
    if not User.select().count():
        return redirect(url_for("create_user_page"))
    return redirect(url_for("all_sessions"))


@app.route("/create_user", methods=["GET", "POST"])
def create_user_page() -> str:
    if request.method == "POST":
        try:
            create_user(
                username=request.form.get("username"),
                password=request.form.get("password"),
            )
            return redirect(url_for("login"))
        except ValueError:
            flash(
                "Both username and password are required. Password should be minimum 8 characters long",
                category="danger",
            )
            return redirect(url_for("create_user_page"))
    return render_template("create_user.html")


@app.route("/login", methods=["GET", "POST"])
def login() -> str:
    if request.method == "POST":
        form = request.form
        if "logout" in form.keys():
            del session["logged_in"]
            flash("You are now logged out", category="success")
            return redirect(url_for("main"))
        if valid_login(username=form.get("username"), password=form.get("password")):
            session["logged_in"] = True
            flash("You are now logged in", category="success")
            return redirect(url_for("main"))
        else:
            flash("Wrong username and/or password", category="danger")
    return render_template("login.html", logged_in=session.get("logged_in"))


@app.route("/search")
def search() -> str:
    text = request.values.get("search")
    expr = f"%{text}%"
    objects = (
        Object.select()
        .join(AltName, JOIN.LEFT_OUTER)
        .switch(Object)
        .join(Structure, JOIN.LEFT_OUTER)
        .where(
            (Object.name**expr) | (AltName.name**expr) | (Structure.name**expr)
        )
    )
    observations = Observation.select().where(
        (Observation.note**expr) | (Observation.object.in_(objects))
    )
    sessions = Session.select().where(Session.note**expr)
    return render_template(
        "search.html",
        text=text,
        objects=objects,
        observations=observations,
        sessions=sessions,
    )


# Sessions
@app.route("/session/new", methods=["GET", "POST"])
@login_required
def new_session() -> str:
    if request.method == "POST":
        location = Location.get_or_none(name=request.form.get("location"))
        date = datetime.datetime.strptime(request.form.get("date"), "%Y-%m-%d")
        note = request.form.get("note", None)
        session, created = Session.get_or_create(
            location=location, date=date, note=note
        )
        if created:
            flash("New session created!", category="success")
            return redirect(url_for("new_observation", session_id=session.id))
        flash("This session already exists!", category="warning")
        return redirect(url_for("new_observation", session_id=session.id))
    return render_template("session_new.html", locations=Location)


@app.route("/observation/new/session/<int:session_id>", methods=["GET", "POST"])
@login_required
def new_observation(session_id: int) -> str:
    session = Session.get_or_none(session_id)
    if not session:
        flash(f"Session with id {session_id} was not found", category="warning")
        return redirect(url_for("main"))
    if request.method == "POST":
        form = request.form
        if not (obj := form.get("object", None)):
            flash("Object name must be provided", category="danger")
            return redirect(url_for("new_observation", session_id=session.id))
        favourite = form.get("favourite") == ""
        obj, _ = Object.get_or_create(name=obj)
        obj.favourite = favourite
        obj.save()
        if obj.to_be_watched:
            flash(
                f"Congratulations! First time observing {obj.name}", category="success"
            )
        telescope = eyepiece = optic_filter = front_filter = binocular = None
        match form.get("observation-type"):
            case "telescope":
                telescope = Telescope.get_or_none(name=form.get("telescope"))
                eyepiece = EyePiece.get_or_none(type=form.get("eyepiece"))
                barlow = Barlow.get_or_none(name=form.get("barlow"))
                optic_filter = Filter.get_or_none(name=form.get("optical_filter"))
                front_filter = FrontFilter.get_or_none(name=form.get("front_filter"))
            case "binocular":
                binocular = Binocular.get_or_none(name=form.get("binocular"))
            case "naked_eye":
                pass
        try:
            create_observation(
                session=session,
                object=obj,
                telescope=telescope,
                eyepiece=eyepiece,
                barlow=barlow,
                optic_filter=optic_filter,
                front_filter=front_filter,
                binocular=binocular,
                note=form.get("note", None),
            )
        except ValueError:
            flash(
                "Unable to create observation. Do not mix things that are not supposed to be mixed and try again"
            )
            return redirect(url_for("new_observation", session_id=session_id))
        flash("Observation created", category="success")

    return render_template(
        "observation.html",
        session=session,
        telescopes=Telescope,
        eyepieces=EyePiece,
        barlows=Barlow,
        optical_filters=Filter,
        front_filters=FrontFilter,
        binoculars=Binocular,
    )


@app.route("/observation/new/image/<int:observation_id>", methods=["POST"])
@login_required
def upload_image(observation_id: int) -> str:
    observation: Observation = Observation.get(observation_id)
    if (file := request.files.get("file", None)) is None:
        flash("No image selected", category="warning")
        return redirect(url_for("session_page", session_id=observation.session.id))
    if not allowed_file(file.filename):
        flash("Image extension not allowed", category="warning")
        return redirect(url_for("session_page", session_id=observation.session.id))
    fname_path = os.path.join(
        app.config["UPLOAD_FOLDER"], secure_filename(file.filename)
    )
    file.save(fname_path)
    observation.add_image(fname_path)
    flash("Image successfully saved", category="success")
    return redirect(url_for("session_page", session_id=observation.session.id))


@app.route("/session/all")
def all_sessions() -> str:
    return render_template(
        "sessions.html", sessions=Session.select().order_by(Session.date.desc())
    )


@app.route("/session/<int:session_id>")
def session_page(session_id: int) -> str:
    session = Session.get_or_none(session_id)
    if not session:
        flash(f"Session with id {session_id} was not found", category="warning")
        return redirect(url_for("main"))
    return render_template("session.html", session=session)


# Objects
@app.route("/structures", methods=["GET"])
def structures() -> str:
    return render_template("structures.html", structures=Structure, objects=Object)


@app.route("/structures/add", methods=["POST"])
@login_required
def add_structure() -> str:
    form = request.form
    if (name := form.get("structure", None)) is None:
        flash("Need to add a name before adding", category="danger")
    Structure.get_or_create(name=name)
    flash(
        f'Added the structure "{name}". Now it is time to add objects',
        category="success",
    )
    return redirect(url_for("structures"))


@app.route("/structures/add_object", methods=["POST"])
@login_required
def add_object_to_structure() -> str:
    form = request.form
    structure = Structure.get(int(form.get("structure")))
    if (object := Object.get_or_none(name=form.get("object"))) is None:
        flash("Please select an object before submitting", category="warning")
        return redirect(url_for("structures"))
    structure.add_object(object)
    return redirect(url_for("structures"))


@app.route("/objects", methods=["GET", "POST"])
@login_required
def objects() -> str:
    if request.method == "POST":
        form = request.form
        match len(form):
            case 1:
                # Toggle favourite
                object = Object.get(int(form.get("toggle_favourite")))
                object.toggle_favourite()
            case _:
                # Adding a new object
                name = form.get("object")
                favourite = form.get("favourite") == ""
                if object := Object.get_or_none(name=name):
                    flash("Object has already been observed", category="warning")
                else:
                    object, _ = Object.get_or_create(
                        name=name, favourite=favourite, to_be_watched=True
                    )
                if structure := Structure.get_or_none(name=form.get("structure")):
                    structure.add_object(object)
    return render_template("objects.html", objects=Object, structures=Structure)


@app.route("/objects/alt_name", methods=["POST"])
@login_required
def add_alt_name() -> str:
    form = request.form
    object = Object.get(name=form.get("object"))
    if alt_name := form.get("alt-name"):
        try:
            AltName.create(object=object, name=alt_name)
        except IntegrityError:
            alt = AltName.get(name=alt_name)
            flash(
                f'"{alt.object.name}" already has this as an alternative name',
                category="danger",
            )
            return redirect(url_for("objects"))
        flash(
            f"Successfully added alternative name: {alt_name} to {object.name}",
            category="success",
        )
    else:
        flash("Cannot add empty alternative name", category="warning")
    return redirect(url_for("objects"))


# Equipments
@app.route("/equipments")
def equipments() -> str:
    return render_template(
        "equipments.html",
        telescopes=Telescope,
        eyepieces=EyePiece,
        barlows=Barlow,
        filters=Filter,
        front_filters=FrontFilter,
        binoculars=Binocular,
    )


@app.route("/equipments/new/telescope", methods=["POST"])
@login_required
def new_telescope() -> str:
    form = request.form
    if not (name := form.get("name", None)):
        flash("Telescope name must be provided", category="danger")
        return redirect(url_for("equipments"))
    if not (aperture := form.get("aperture", None)):
        flash("Telescope aperture must be provided", category="danger")
        return redirect(url_for("equipments"))
    if not (focal_length := form.get("focal_length", None)):
        flash("Telescope focal length must be provided", category="danger")
        return redirect(url_for("equipments"))
    telescope, created = Telescope.get_or_create(
        name=name, aperture=aperture, focal_length=focal_length
    )
    if created:
        flash(f'Telescope "{telescope.name}" was created', category="success")
    else:
        flash(f'Telescope "{telescope.name}" already exists', category="warning")
    return redirect(url_for("equipments"))


@app.route("/equipments/new/binocular", methods=["POST"])
@login_required
def new_binocular() -> str:
    form = request.form
    if not (name := form.get("name", None)):
        flash("Binocular name must be provided", category="danger")
        return redirect(url_for("equipments"))
    if not (aperture := form.get("aperture", None)):
        flash("Binocular aperture must be provided", category="danger")
        return redirect(url_for("equipments"))
    if not (magnification := form.get("magnification", None)):
        flash("Binocular magnification must be provided", category="danger")
        return redirect(url_for("equipments"))
    binocular, created = Binocular.get_or_create(
        name=name, aperture=aperture, magnification=magnification
    )
    if created:
        flash(f'Binocular "{binocular.name}" was created', category="success")
    else:
        flash(f'Binocular "{binocular.name}" already exists', category="warning")
    return redirect(url_for("equipments"))


@app.route("/equipments/new/eyepiece", methods=["POST"])
@login_required
def new_eyepiece() -> str:
    form = request.form
    if not (type_ := form.get("type", None)):
        flash("Eyepiece type must be provided", category="danger")
        return redirect(url_for("equipments"))
    if not (focal_length := form.get("focal_length", None)):
        flash("Eyepiece focal length must be provided", category="danger")
        return redirect(url_for("equipments"))
    if not (width := form.get("width", None)):
        flash("Eyepiece width must be provided", category="danger")
        return redirect(url_for("equipments"))
    eyepiece, created = EyePiece.get_or_create(
        type=type_, focal_length=focal_length, width=width
    )
    if created:
        flash(f'Eyepiece "{eyepiece.type}" was created', category="success")
    else:
        flash(f'Eyepiece "{eyepiece.type}" already exists', category="warning")
    return redirect(url_for("equipments"))


@app.route("/equipments/new/barlow", methods=["POST"])
@login_required
def new_barlow() -> str:
    form = request.form
    if not (name := form.get("name", None)):
        flash("Barlow name must be provided", category="danger")
        return redirect(url_for("equipments"))
    if not (multiplier := form.get("multiplier", None)):
        flash("Barlow multiplier must be provided", category="danger")
        return redirect(url_for("equipments"))
    barlow, created = Barlow.get_or_create(name=name, multiplier=multiplier)
    if created:
        flash(
            f'Barlow "{barlow.name} ({barlow.multiplier})" was created',
            category="success",
        )
    else:
        flash(
            f'Barlow "{barlow.name} ({barlow.multiplier})" already exists',
            category="success",
        )
    return redirect(url_for("equipments"))


@app.route("/equipments/new/filter", methods=["POST"])
@login_required
def new_filter() -> str:
    form = request.form
    if not (name := form.get("name", None)):
        flash("Filter name must be provided", category="danger")
        return redirect(url_for("equipments"))
    filter_, created = Filter.get_or_create(name=name)
    if created:
        flash(f'Filter "{filter_.name}" was created', category="success")
    else:
        flash(f'Filter "{filter_.name}" already exists', category="warning")
    return redirect(url_for("equipments"))


@app.route("/equipments/new/front_filter", methods=["POST"])
@login_required
def new_front_filter() -> str:
    form = request.form
    if not (name := form.get("name", None)):
        flash("Filter name must be provided", category="danger")
        return redirect(url_for("equipments"))
    filter_, created = FrontFilter.get_or_create(name=name)
    if created:
        flash(f'Front filter "{filter_.name}" was created', category="success")
    else:
        flash(f'Front filter "{filter_.name}" already exists', category="warning")
    return redirect(url_for("equipments"))


# Locations
@app.route("/locations")
@login_required
def locations() -> str:
    return render_template("locations.html", locations=Location)


@app.route("/locations/alter", methods=["POST"])
@login_required
def alter_location() -> str:
    form = request.form
    for action, location_id in form.items():
        location = Location.get(int(location_id))
        match action:
            case "delete":
                if delete_location(location):
                    flash(
                        f"Successfully deleted: {location.name} ({location.country})",
                        category="success",
                    )
                else:
                    flash(
                        f"Could not delete because of observation there: {location.name} ({location.country})",
                        category="warning",
                    )
    return redirect(url_for("locations"))


@app.route("/locations/new", methods=["POST"])
@login_required
def new_location() -> str:
    form = request.form
    if not (name := form.get("name", None)):
        flash("Name must be provided", category="danger")
        return redirect(url_for("locations"))
    if not (country := form.get("country", None)):
        flash("Cuntry must be provided", category="danger")
        return redirect(url_for("locations"))
    if not (latitude := form.get("latitude", None)):
        flash("Latitude must be provided", category="danger")
        return redirect(url_for("locations"))
    if not (longitude := form.get("longitude", None)):
        flash("Longitude must be provided", category="danger")
        return redirect(url_for("locations"))
    if not (altitude := form.get("altitude", None)):
        flash("Altitude must be provided", category="danger")
        return redirect(url_for("locations"))
    location, created = Location.get_or_create(
        name=name,
        country=country,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
    )
    if created:
        flash(f'Location "{location.name}" was created', category="success")
    else:
        flash(f'Location "{location.name}" already exists', category="warning")
    return redirect(url_for("locations"))


# Planning
@app.route("/visibility", methods=["GET", "POST"])
def visibility() -> str:
    if request.method == "POST":
        fig = visibility_plot(request.form)
        return render_template(
            "visibility_curve.html",
            locations=Location,
            fig=fig,
            date=request.form.get("date"),
            name=request.form.get("name"),
        )
    today = datetime.datetime.today().date()
    return render_template(
        "visibility_curve.html", locations=Location, fig=None, date=today, name=None
    )


def visibility_plot(form: ImmutableMultiDict[str, str]) -> str | None:
    quantity_support()
    location = Location.get_by_id(int(form.get("location")))
    midnight = Time(form.get("date"))
    delta_midnight = np.linspace(-12, 12, 1000) * u.hour
    times = midnight + delta_midnight
    frames = AltAz(obstime=times, location=location.earth_location)
    sun_pos = get_sun(times).transform_to(frames)
    moon_pos = get_body("moon", times).transform_to(frames)
    fig = plt.figure()
    plt.plot(delta_midnight, sun_pos.alt, "--y", label="Sun")
    plt.plot(delta_midnight, moon_pos.alt, "--r", label="Moon")
    for name in form.get("name").split(","):
        try:
            obj = SkyCoord.from_name(name)
        except NameResolveError:
            flash(f"Could not find object: {name}", category="danger")
            continue
        obj_pos = obj.transform_to(frames)

        plt.plot(delta_midnight, obj_pos.alt, label=name, lw=5)
    plt.fill_between(
        delta_midnight,
        0 * u.deg,
        90 * u.deg,
        where=sun_pos.alt < -0 * u.deg,
        color="0.5",
        zorder=0,
    )
    plt.fill_between(
        delta_midnight,
        0 * u.deg,
        90 * u.deg,
        where=sun_pos.alt < -18 * u.deg,
        color="k",
        zorder=0,
    )

    plt.legend(loc="upper left")
    plt.xlim(-12, 12)
    plt.xticks((np.arange(13) * 2 - 12))
    plt.ylim(0, 90)
    plt.xlabel("Hours from midnight")
    plt.ylabel("Altitude [deg]")
    return mpld3.fig_to_html(fig)


@app.route("/gallery", methods=["GET"])
def gallery() -> str:
    return render_template("gallery.html", images=Image, enumerate=enumerate)


if __name__ == "__main__":  # pragma: no cover
    # Setup DB
    DEFAULT_DB = os.path.join(os.path.abspath("."), "AstroLog.db")
    ASTRO_LOG_DB = os.getenv("ASTRO_LOG_DB", DEFAULT_DB)
    db = SqliteDatabase(ASTRO_LOG_DB)
    database_proxy.initialize(db)
    db.create_tables(MODELS)

    app.run(host="0.0.0.0", port=5065, debug=True)
