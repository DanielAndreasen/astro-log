from typing import Dict, List, Union

from astrolog.database import Observation, Session


def get_session(date) -> Dict[str, Union[List[Observation], Session]]:
    session = Session.get_or_none(date=date)
    if not session:
        return {'session': session, 'observations': []}
    return {'session': session, 'observations': list(session.observation_set)}


def get_sessions(date1, date2) -> Dict[str, List[Session]]:
    sessions = Session.select().where((Session.date >= date1) & (Session.date <= date2))
    if not len(sessions):
        return {'sessions': []}
    return {'sessions': [session for session in sessions]}


def get_observations_of_object(object) -> Dict[str, List[Observation]]:
    observations = Observation.select().where(Observation.object == object)
    if not len(observations):
        return {'observations': []}
    return {'observations': list(observations)}
