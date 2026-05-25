from datetime import datetime
from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviews = db.relationship(
        "Review", backref="user", lazy=True, cascade="all, delete-orphan"
    )


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    restaurant_name = db.Column(db.String(200), nullable=False)
    visit_date = db.Column(db.Date, nullable=False)
    meal_type = db.Column(db.String(20))
    category = db.Column(db.String(50))
    price = db.Column(db.Float)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    address = db.Column(db.String(300))
    calories = db.Column(db.Float)
    protein = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Restaurant(db.Model):
    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    address = db.Column(db.String(300))
    area = db.Column(db.String(100))
    cuisine_style = db.Column(db.String(100))
    category = db.Column(db.String(200))
    is_healthy = db.Column(db.Boolean, default=False)
    price_level = db.Column(db.Integer)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_seeded  = db.Column(db.Boolean, default=False, nullable=False)

    menu_items = db.relationship(
        "MenuItem", backref="restaurant", lazy=True, cascade="all, delete-orphan"
    )


class MenuItem(db.Model):
    __tablename__ = "menu_items"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    item_name = db.Column(db.String(300), nullable=False)
    price = db.Column(db.Float)
    calories = db.Column(db.Float)
    protein = db.Column(db.Float)
