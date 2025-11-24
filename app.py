from datetime import datetime
from typing import Optional

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cellar.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev-secret-key"

db = SQLAlchemy(app)


class Wine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    varietal = db.Column(db.String(80), nullable=True)
    region = db.Column(db.String(120), nullable=True)
    vintage = db.Column(db.Integer, nullable=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default="cellar", nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def safe_quantity(self) -> int:
        return max(self.quantity or 0, 0)

    def status_label(self) -> str:
        return "In Cellar" if self.status == "cellar" else "Enjoyed"


@app.route("/")
def index():
    search_term = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "")

    wines_query = Wine.query
    if search_term:
        like_term = f"%{search_term}%"
        wines_query = wines_query.filter(
            db.or_(
                Wine.name.ilike(like_term),
                Wine.varietal.ilike(like_term),
                Wine.region.ilike(like_term),
                Wine.purchase_location.ilike(like_term),
                Wine.notes.ilike(like_term),
            )
        )
    if status_filter in {"cellar", "enjoyed"}:
        wines_query = wines_query.filter_by(status=status_filter)

    wines = wines_query.order_by(Wine.created_at.desc()).all()

    stats = {
        "total": Wine.query.count(),
        "cellar": Wine.query.filter_by(status="cellar").count(),
        "enjoyed": Wine.query.filter_by(status="enjoyed").count(),
    }

    return render_template(
        "index.html",
        wines=wines,
        search_term=search_term,
        status_filter=status_filter,
        stats=stats,
        view_mode="table" if view_mode == "table" else "cards",
    )


def _parse_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _parse_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value is None or value.strip() == "":
        return None
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


@app.route("/wines", methods=["POST"])
def add_wine():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Wine name is required.", "error")
        return redirect(url_for("index"))

    wine = Wine(
        name=name,
        varietal=request.form.get("varietal", "").strip() or None,
        region=request.form.get("region", "").strip() or None,
        vintage=_parse_int(request.form.get("vintage")),
        quantity=max(_parse_int(request.form.get("quantity")) or 1, 0),
        status="cellar",
        notes=request.form.get("notes", "").strip() or None,
    )

    db.session.add(wine)
    db.session.commit()
    flash("Wine added to your cellar.", "success")
    return redirect(url_for("index"))


@app.route("/wines/<int:wine_id>/consume", methods=["POST"])
def consume_wine(wine_id: int):
    wine = Wine.query.get_or_404(wine_id)
    if wine.quantity > 0:
        wine.quantity -= 1
    if wine.quantity <= 0:
        wine.status = "enjoyed"
        wine.quantity = 0

    db.session.commit()
    flash(f"Marked a bottle of {wine.name} as enjoyed.", "success")
    return redirect(url_for("index"))


@app.route("/wines/<int:wine_id>/restock", methods=["POST"])
def restock_wine(wine_id: int):
    wine = Wine.query.get_or_404(wine_id)
    wine.quantity += 1
    if wine.status == "enjoyed":
        wine.status = "cellar"

    db.session.commit()
    flash(f"Restocked {wine.name}.", "success")
    return redirect(url_for("index"))


@app.route("/wines/<int:wine_id>/delete", methods=["POST"])
def delete_wine(wine_id: int):
    wine = Wine.query.get_or_404(wine_id)
    db.session.delete(wine)
    db.session.commit()
    flash(f"Removed {wine.name} from your cellar.", "info")
    return redirect(url_for("index"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    # Disable the auto-reloader to avoid a SystemExit on some environments (e.g.,
    # Windows/IDE runners) when the reloader spins up and terminates the parent
    # process. Enable it manually with use_reloader=True if desired.
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
    app.run(debug=True, host="0.0.0.0", port=5000)
