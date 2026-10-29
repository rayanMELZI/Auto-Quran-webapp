from flask import Blueprint, jsonify, render_template

bp = Blueprint("main", __name__)


@bp.route("/")
def welcome():
    return render_template("main.html")


@bp.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})
