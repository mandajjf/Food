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

class UserDiet(db.Model):
    __tablename__ = "user_diets"

    username = db.Column(db.String(80), db.ForeignKey("users.username"), primary_key=True)
    diet_mode = db.Column(db.Boolean, default=False)  # True for diet mode, False for normal mode
    height = db.Column(db.Float)  # 身高，單位為公分
    weight = db.Column(db.Float)  # 體重，單位為公斤
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)  # 年齡，單位為歲
    acticity_coeff = db.Column(db.Float)  # 活動係數
    target_type = db.Column(db.String(20),default="維持體重")  # "減重", "增肌", "維持體重"
    TDEE = db.Column(db.Float)  # 總日常能量消耗
    protein_intake = db.Column(db.Float)  # 蛋白質攝取量，單位為克
'''
activity_coeff
無活動：久坐，TDEE = 1.2x BMR
輕量活動：每周運動1-3天(輕鬆)，TDEE = 1.375 x BMR
中度活動量：站走稍多、每周運動3-5天（中強度），TDEE = 1.55 x BMR
高度活動量：站走為主、每周運動6-7天（高強度），TDEE = 1.725 x BMR
非常高度活動量：勞力型的工作、幾乎整天都做高強度的運動，TDEE = 1.9 x BMR)、

BMR(男)=(13.7×體重(公斤))+(5.0×身高(公分))-(6.8×年齡)+66
BMR(女)=(9.6×體重(公斤))+(1.8×身高(公分))-(4.7×年齡)+655"

增肌：1.6g/每公斤體重、減脂：2g/每公斤體重、維持體重：1.2g/每公斤體重計算並顯示建議蛋白質攝取量
'''

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
