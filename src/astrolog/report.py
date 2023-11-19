from dataclasses import dataclass

from peewee import ModelSelect, fn

from astrolog.database import Object, Observation, Session


def get_most_observed_objects(query: ModelSelect) -> set[Object]:
    object_observations = (
        Object.select(Object, fn.Count(Object.id).alias("st_count"))
        .join(Observation)
        .join(Session)
        .where(Session.id.in_(query))
        .group_by(Object.name)
    )
    max_obs = 0
    most_observed_objects: set[Object] = set()
    for row in object_observations:
        current_count = row.st_count
        if current_count > max_obs:
            max_obs = current_count
            most_observed_objects.clear()
            most_observed_objects.add(row)
        elif current_count == max_obs:
            most_observed_objects.add(row)

    return most_observed_objects


@dataclass
class Report:
    n_sessions: int
    n_observations: int
    unique_objects: set[Object]
    most_observed_objects: set[Object]

    @classmethod
    def from_query(cls, query: ModelSelect) -> "Report":
        n_sessions = query.count()
        n_observations = 0
        unique_objects = set()
        session: Session
        for session in query:
            for observation in session.observations:
                n_observations += 1
                obj = observation.object
                unique_objects.add(obj)

        most_observed_objects = get_most_observed_objects(query)
        return cls(
            n_sessions=n_sessions,
            n_observations=n_observations,
            unique_objects=sorted(unique_objects, key=lambda x: x.name),
            most_observed_objects=sorted(most_observed_objects, key=lambda x: x.name),
        )
