from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import inspect, text

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
    price_paid = db.Column(db.Numeric(10, 2), nullable=True)
    purchase_location = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    tasting_notes = db.Column(db.Text, nullable=True)
    experience_notes = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Numeric(2, 1), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def safe_quantity(self) -> int:
        return max(self.quantity or 0, 0)

    def status_label(self) -> str:
        return "In Cellar" if self.status == "cellar" else "Enjoyed"


class Consumption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wine_id = db.Column(db.Integer, db.ForeignKey("wine.id", ondelete="SET NULL"), nullable=True)
    wine_name = db.Column(db.String(120), nullable=False)
    consumed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    rating = db.Column(db.Numeric(2, 1), nullable=True)
    tasting_notes = db.Column(db.Text, nullable=True)
    experience_notes = db.Column(db.Text, nullable=True)

    wine = db.relationship("Wine", backref="consumptions")


@app.route("/")
def index():
    search_term = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "")
    view_mode = request.args.get("view", "cards")

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


@app.route("/consumptions")
def consumption_history():
    consumptions = Consumption.query.order_by(Consumption.consumed_at.desc()).all()
    return render_template("consumptions.html", consumptions=consumptions)


@app.route("/consumptions/<int:consumption_id>/edit", methods=["POST"])
def edit_consumption(consumption_id: int):
    consumption = Consumption.query.get_or_404(consumption_id)

    consumption.tasting_notes = request.form.get("tasting_notes", "").strip() or None
    consumption.experience_notes = request.form.get("experience_notes", "").strip() or None
    consumption.rating = _parse_rating(request.form.get("rating"))

    db.session.commit()
    flash(f"Updated notes for {consumption.wine_name}.", "success")
    return redirect(url_for("consumption_history"))


@app.route("/consumptions/<int:consumption_id>/delete", methods=["POST"])
def delete_consumption(consumption_id: int):
    consumption = Consumption.query.get_or_404(consumption_id)

    should_restock = request.form.get("restock") == "1"
    restocked = False

    if should_restock and consumption.wine:
        consumption.wine.quantity += consumption.quantity or 1
        if consumption.wine.quantity > 0 and consumption.wine.status == "enjoyed":
            consumption.wine.status = "cellar"
        restocked = True

    db.session.delete(consumption)
    db.session.commit()

    if should_restock and not consumption.wine:
        flash(
            "Consumption removed, but the linked cellar entry was missing so inventory was unchanged.",
            "info",
        )
    elif restocked:
        flash(
            f"Removed consumption entry for {consumption.wine_name} and restored inventory.",
            "success",
        )
    else:
        flash(f"Removed consumption entry for {consumption.wine_name}.", "success")

    return redirect(url_for("consumption_history"))


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


def _parse_rating(value: Optional[str]) -> Optional[Decimal]:
    if value is None or value.strip() == "":
        return None
    try:
        rating = Decimal(value).quantize(Decimal("0.1"))
    except (InvalidOperation, ValueError):
        return None

    if rating < 0:
        return Decimal("0.0")
    if rating > 5:
        return Decimal("5.0")
    return rating


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
        price_paid=_parse_decimal(request.form.get("price_paid")),
        purchase_location=request.form.get("purchase_location", "").strip() or None,
        notes=request.form.get("notes", "").strip() or None,
        tasting_notes=None,
        experience_notes=None,
        rating=None,
    )

    db.session.add(wine)
    db.session.commit()
    flash("Wine added to your cellar.", "success")
    return redirect(url_for("index"))


@app.route("/wines/<int:wine_id>/consume", methods=["POST"])
def consume_wine(wine_id: int):
    wine = Wine.query.get_or_404(wine_id)

    tasting_notes = request.form.get("tasting_notes", "").strip() or None
    experience_notes = request.form.get("experience_notes", "").strip() or None
    rating = _parse_rating(request.form.get("rating"))

    if tasting_notes:
        wine.tasting_notes = tasting_notes
    if experience_notes:
        wine.experience_notes = experience_notes
    if rating is not None:
        wine.rating = rating

    if wine.quantity > 0:
        wine.quantity -= 1
    if wine.quantity <= 0:
        wine.status = "enjoyed"
        wine.quantity = 0

    consumption = Consumption(
        wine_id=wine.id,
        wine_name=wine.name,
        quantity=1,
        rating=rating,
        tasting_notes=tasting_notes,
        experience_notes=experience_notes,
    )
    db.session.add(consumption)

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


@app.route("/wines/<int:wine_id>/edit", methods=["POST"])
def edit_wine(wine_id: int):
    wine = Wine.query.get_or_404(wine_id)

    name = request.form.get("name", "").strip()
    if not name:
        flash("Wine name is required to edit.", "error")
        return redirect(url_for("index"))

    wine.name = name
    wine.varietal = request.form.get("varietal", "").strip() or None
    wine.region = request.form.get("region", "").strip() or None
    wine.vintage = _parse_int(request.form.get("vintage"))
    wine.quantity = max(_parse_int(request.form.get("quantity")) or 0, 0)
    wine.price_paid = _parse_decimal(request.form.get("price_paid"))
    wine.purchase_location = request.form.get("purchase_location", "").strip() or None
    wine.notes = request.form.get("notes", "").strip() or None
    wine.tasting_notes = request.form.get("tasting_notes", "").strip() or None
    wine.experience_notes = request.form.get("experience_notes", "").strip() or None
    wine.rating = _parse_rating(request.form.get("rating"))

    if wine.quantity == 0:
        wine.status = "enjoyed"
    elif wine.status == "enjoyed":
        wine.status = "cellar"

    db.session.commit()
    flash(f"Updated {wine.name}.", "success")
    return redirect(url_for("index"))


def _ensure_schema_updates() -> None:
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()

    if "wine" in table_names:
        column_names = {col["name"] for col in inspector.get_columns("wine")}
        if "price_paid" not in column_names:
            db.session.execute(text("ALTER TABLE wine ADD COLUMN price_paid NUMERIC(10, 2)"))
        if "purchase_location" not in column_names:
            db.session.execute(text("ALTER TABLE wine ADD COLUMN purchase_location VARCHAR(120)"))
        if "tasting_notes" not in column_names:
            db.session.execute(text("ALTER TABLE wine ADD COLUMN tasting_notes TEXT"))
        if "experience_notes" not in column_names:
            db.session.execute(text("ALTER TABLE wine ADD COLUMN experience_notes TEXT"))
        if "rating" not in column_names:
            db.session.execute(text("ALTER TABLE wine ADD COLUMN rating NUMERIC(2, 1)"))
        db.session.commit()


with app.app_context():
    _ensure_schema_updates()
    db.create_all()


if __name__ == "__main__":
    # Disable the auto-reloader to avoid a SystemExit on some environments (e.g.,
    # Windows/IDE runners) when the reloader spins up and terminates the parent
    # process. Enable it manually with use_reloader=True if desired.
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
