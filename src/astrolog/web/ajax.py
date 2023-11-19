from typing import cast

from flask import Blueprint, render_template, request

from astrolog.api import get_monthly_report, get_yearly_report
from astrolog.database import Kind, Object, Observation

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


@bp.route("/get_report", methods=["GET"])
def get_report() -> str:
    date_str = request.values.get("date", "")
    year, month = map(int, date_str.split("-")[0:2])
    report_monthly = get_monthly_report(year, month)
    report_yearly = get_yearly_report(year)
    return render_template("sub/report.html", year=report_yearly, month=report_monthly)
