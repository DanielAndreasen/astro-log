from typing import Dict, Optional

from astrolog.database import (Binocular, EyePiece, Filter, Object,
                               Observation, Session, Telescope)


def get_session(date) -> Dict[str, list[Observation] | Session]:
    session = Session.get_or_none(date=date)
    if not session:
        return {'session': session, 'observations': []}
    return {'session': session, 'observations': list(session.observation_set)}


def get_sessions(date1, date2) -> dict[str, list[Session]]:
    sessions = Session.select().where((Session.date >= date1) & (Session.date <= date2))
    if not len(sessions):
        return {'sessions': []}
    return {'sessions': [session for session in sessions]}


def get_observations_of_object(object) -> dict[str, list[Observation]]:
    observations = Observation.select().where(Observation.object == object)
    if not len(observations):
        return {'observations': []}
    return {'observations': list(observations)}


def create_observation(session: Session, object: Object,
                       binocular: Optional[Binocular] = None, telescope: Optional[Telescope] = None,
                       eyepiece: Optional[EyePiece] = None, optic_filter: Optional[Filter] = None,
                       note: Optional[str] = None) -> tuple[Observation, bool]:

    if binocular and telescope:
        raise ValueError('Not possible to make observation with both telescope and binoculars')
    if binocular and eyepiece:
        raise ValueError('Not possible to make observation with an eyepiece in binoculars')
    if binocular and optic_filter:
        raise ValueError('Not possible to make observation with an optical filter in binoculars')
    if telescope and not eyepiece:
        raise ValueError('Telescope require an eyepiece to function')

    return Observation.get_or_create(session=session, object=object, binocular=binocular,
                                     telescope=telescope, eyepiece=eyepiece, optic_filter=optic_filter,
                                     note=note)
