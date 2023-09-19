from typing import cast

from flask import Blueprint, request

from astrolog.database import Kind, Object, Observation, Session

bp = Blueprint("ajax", __name__, url_prefix="/ajax")


@bp.route("/add/kind", methods=["POST"])
def add_kind() -> tuple[str, int]:
    form = request.form
    Kind.get_or_create(name=form.get("kind", None))
    return "", 204


@bp.route("/update/kind", methods=["POST"])
def update_kind() -> tuple[str, int]:
    form: dict[str, int] = cast(dict[str, int], request.json)
    kind = Kind.get_or_none(id=form["kind_id"] or None)
    object = Object.get_by_id(form["object_id"])
    object.kind = kind
    object.save()
    return "", 204


@bp.route("/update/observation/note", methods=["POST"])
def update_observation_note() -> tuple[str, int]:
    form: dict[str, int | str] = cast(dict[str, int | str], request.form)
    observation = Observation.get_by_id(form["observation-id"])
    observation.note = form["observation-note"]
    observation.save()
    return "", 204
