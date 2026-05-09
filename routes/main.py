from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.route("/")
def welcome():
    return render_template("main.html")
