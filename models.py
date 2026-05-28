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
    """使用者每日飲食控制設定。

    活動係數 (activity_coeff)：
        1.200 — 無活動：久坐
        1.375 — 輕量活動：每週 1–3 天
        1.550 — 中度活動量：每週 3–5 天
        1.725 — 高度活動量：每週 6–7 天
        1.900 — 非常高度活動量：勞力型工作

    BMR 公式：
        男：13.7 × 體重(kg) + 5.0 × 身高(cm) − 6.8 × 年齡 + 66
        女：9.6 × 體重(kg) + 1.8 × 身高(cm) − 4.7 × 年齡 + 655

    蛋白質建議：
        增肌：1.6 g/kg、減脂：2.0 g/kg、維持體重：1.2 g/kg
    """

    __tablename__ = "user_diets"

    username = db.Column(db.String(80), db.ForeignKey("users.username"), primary_key=True)
    diet_mode = db.Column(db.Boolean, default=False)
    height = db.Column(db.Float)         # 身高，單位公分
    weight = db.Column(db.Float)         # 體重，單位公斤
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)          # 年齡，單位歲
    activity_coeff = db.Column(db.Float) # 活動係數
    target_type = db.Column(db.String(20), default="維持體重")  # 增肌 / 減脂 / 維持體重
    TDEE = db.Column(db.Float)           # 總日常能量消耗
    protein_intake = db.Column(db.Float) # 建議蛋白質攝取量，單位克

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
