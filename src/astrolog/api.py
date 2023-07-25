from datetime import date

import bcrypt

from astrolog.database import (
    Barlow,
    Binocular,
    Camera,
    EyePiece,
    Filter,
    FrontFilter,
    Location,
    Object,
    Observation,
    Session,
    Telescope,
    User,
)


def get_session(date: date) -> dict[str, list[Observation] | Session]:
    session = Session.get_or_none(date=date)
    if not session:
        return {"session": session, "observations": []}
    return {"session": session, "observations": list(session.observation_set)}


def get_sessions(date1: date, date2: date) -> dict[str, list[Session]]:
    sessions = Session.select().where((Session.date >= date1) & (Session.date <= date2))
    if not len(sessions):
        return {"sessions": []}
    return {"sessions": [session for session in sessions]}


def get_observations_of_object(object: Object) -> dict[str, list[Observation]]:
    observations = Observation.select().where(Observation.object == object)
    if not len(observations):
        return {"observations": []}
    return {"observations": list(observations)}


def create_observation(
    session: Session,
    object: Object,
    binocular: Binocular | None = None,
    telescope: Telescope | None = None,
    eyepiece: EyePiece | None = None,
    barlow: Barlow | None = None,
    camera: Camera | None = None,
    optic_filter: Filter | None = None,
    front_filter: FrontFilter | None = None,
    note: str | None = None,
) -> tuple[Observation, bool]:
    if binocular and telescope:
        raise ValueError(
            "Not possible to make observation with both telescope and binoculars"
        )
    if binocular and eyepiece:
        raise ValueError(
            "Not possible to make observation with an eyepiece in binoculars"
        )
    if binocular and optic_filter:
        raise ValueError(
            "Not possible to make observation with an optical filter in binoculars"
        )
    if telescope:
        if not camera and not eyepiece:
            raise ValueError("Telescope require an eyepiece or camera to function")

    # This object has now been observed
    object.to_be_watched = False
    object.save()

    return Observation.get_or_create(
        session=session,
        object=object,
        binocular=binocular,
        telescope=telescope,
        eyepiece=eyepiece,
        barlow=barlow,
        camera=camera,
        optic_filter=optic_filter,
        front_filter=front_filter,
        note=note,
    )


def delete_location(location: Location) -> bool:
    match len(location.session_set):
        case 0:
            location.delete_instance()
            return True
        case _:
            return False


def create_user(username: str, password: str) -> User:
    if not username or not password:
        raise ValueError("Username and password are both required")
    if len(password) < 8:
        raise ValueError("Too short password, minimum of 8 characters are required")
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return User.create(username=username, hashed_password=hashed_password)


def valid_login(username: str, password: str) -> bool:
    if (not username) or (not password):
        return False
    if (user := User.get_or_none(username=username)) is None:
        return False
    return bcrypt.checkpw(password.encode(), user.hashed_password)
