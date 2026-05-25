import os
from functools import wraps
from datetime import date, datetime

import bcrypt
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

load_dotenv()

from database import db
from models import MenuItem, Restaurant, Review, User

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Secret key
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION")

# Database configuration
_db_url = os.environ.get("DATABASE_URL", "")
if _db_url:
    # Render provides postgres:// but SQLAlchemy 1.4+ requires postgresql://
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
else:
    _basedir = os.path.abspath(os.path.dirname(__file__))
    _instance_path = os.path.join(_basedir, "instance")
    os.makedirs(_instance_path, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{os.path.join(_instance_path, 'app.db')}"
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Auto-create tables on startup (safe: skips existing tables)
with app.app_context():
    db.create_all()


# ---------------------------------------------------------------------------
# Custom Jinja2 filter
# ---------------------------------------------------------------------------

@app.template_filter("format_price")
def format_price(price):
    if price is None:
        return "—"
    if price == int(price):
        return f"NT${int(price):,}"
    return f"NT${price:,.2f}"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("請先登入才能使用此功能。", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# ── 註冊 ──────────────────────────────────────────────────────────────────

@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []

        if not username:
            errors.append("使用者名稱不可空白。")
        if not email:
            errors.append("Email 不可空白。")
        elif "@" not in email or "." not in email.split("@")[-1]:
            errors.append("Email 格式不正確。")
        if not password:
            errors.append("密碼不可空白。")
        elif len(password) < 6:
            errors.append("密碼長度至少 6 碼。")
        if password != confirm_password:
            errors.append("密碼與確認密碼不一致。")

        if not errors:
            if User.query.filter_by(username=username).first():
                errors.append("此使用者名稱已被使用。")
            if User.query.filter_by(email=email).first():
                errors.append("此 Email 已被其他帳號使用。")

        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template("sign_up.html", username=username, email=email)

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()

        flash("註冊成功！請登入。", "success")
        return redirect(url_for("login"))

    return render_template("sign_up.html")


# ── 登入 ──────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("請輸入帳號與密碼。", "danger")
            return render_template("login.html", identifier=identifier)

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and bcrypt.checkpw(
            password.encode("utf-8"), user.password_hash.encode("utf-8")
        ):
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"歡迎回來，{user.username}！", "success")
            return redirect(url_for("dashboard"))

        flash("帳號或密碼錯誤，請重試。", "danger")
        return render_template("login.html", identifier=identifier)

    return render_template("login.html")


# ── 登出 ──────────────────────────────────────────────────────────────────

@app.route("/logout")
def logout():
    session.clear()
    flash("已成功登出，下次再來！", "info")
    return redirect(url_for("index"))


# ── 儀表板 ────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    review_count = Review.query.filter_by(user_id=session["user_id"]).count()
    return render_template("dashboard.html", review_count=review_count)


# ── 新增紀錄 ──────────────────────────────────────────────────────────────

MEAL_TYPES = ["早餐", "午餐", "晚餐", "點心"]
CATEGORIES = ["台式", "日式", "韓式", "美式", "義式", "甜點", "飲料", "其他"]


@app.route("/new_review", methods=["GET", "POST"])
@login_required
def new_review():
    if request.method == "POST":
        restaurant_name = request.form.get("restaurant_name", "").strip()
        visit_date_str = request.form.get("visit_date", "").strip()
        meal_type = request.form.get("meal_type", "").strip()
        category = request.form.get("category", "").strip()
        price_str    = request.form.get("price",    "").strip()
        rating_str   = request.form.get("rating",   "").strip()
        calories_str = request.form.get("calories", "").strip()
        protein_str  = request.form.get("protein",  "").strip()
        comment = request.form.get("comment", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        visit_date = None
        price = rating = calories = protein = None

        if not restaurant_name:
            errors.append("餐廳名稱為必填。")

        if not visit_date_str:
            errors.append("用餐日期為必填。")
        else:
            try:
                visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append("日期格式不正確，請使用 YYYY-MM-DD。")

        if price_str:
            try:
                price = float(price_str)
                if price < 0:
                    errors.append("價格不可為負數。")
            except ValueError:
                errors.append("價格必須為數字。")

        if rating_str:
            try:
                rating = int(rating_str)
                if not 1 <= rating <= 5:
                    errors.append("評分必須在 1 到 5 之間。")
            except ValueError:
                errors.append("評分必須為整數。")

        if calories_str:
            try:
                calories = float(calories_str)
                if calories < 0:
                    errors.append("熱量不可為負數。")
            except ValueError:
                errors.append("熱量必須為數字。")

        if protein_str:
            try:
                protein = float(protein_str)
                if protein < 0:
                    errors.append("蛋白質不可為負數。")
            except ValueError:
                errors.append("蛋白質必須為數字。")

        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template(
                "new_review.html",
                meal_types=MEAL_TYPES,
                categories=CATEGORIES,
                form=request.form,
            )

        review = Review(
            user_id=session["user_id"],
            restaurant_name=restaurant_name,
            visit_date=visit_date,
            meal_type=meal_type or None,
            category=category or None,
            price=price,
            rating=rating,
            comment=comment or None,
            address=address or None,
            calories=calories,
            protein=protein,
        )
        db.session.add(review)
        db.session.commit()

        flash("美食紀錄新增成功！", "success")
        return redirect(url_for("diary"))

    restaurant_names = [
        r.name for r in Restaurant.query.order_by(Restaurant.name).all()
    ]
    return render_template(
        "new_review.html",
        meal_types=MEAL_TYPES,
        categories=CATEGORIES,
        form={"visit_date": date.today().isoformat()},
        restaurant_names=restaurant_names,
    )


# ── 美食日記 ──────────────────────────────────────────────────────────────

@app.route("/diary")
@login_required
def diary():
    keyword = request.args.get("keyword", "").strip()
    filter_category = request.args.get("category", "").strip()
    filter_meal_type = request.args.get("meal_type", "").strip()

    query = Review.query.filter_by(user_id=session["user_id"])

    if keyword:
        query = query.filter(
            (Review.restaurant_name.ilike(f"%{keyword}%"))
            | (Review.comment.ilike(f"%{keyword}%"))
        )
    if filter_category:
        query = query.filter_by(category=filter_category)
    if filter_meal_type:
        query = query.filter_by(meal_type=filter_meal_type)

    reviews = query.order_by(
        Review.visit_date.desc(), Review.created_at.desc()
    ).all()

    # 依日期分組，計算每日總計
    from collections import OrderedDict
    grouped = OrderedDict()
    for r in reviews:
        grouped.setdefault(r.visit_date, []).append(r)

    grouped_days = []
    for d, day_reviews in grouped.items():
        total_cal = sum(r.calories for r in day_reviews if r.calories)
        total_pro = sum(r.protein  for r in day_reviews if r.protein)
        grouped_days.append({
            "date":           d,
            "reviews":        day_reviews,
            "total_calories": round(total_cal) if total_cal else None,
            "total_protein":  round(total_pro, 1) if total_pro else None,
        })

    return render_template(
        "diary.html",
        grouped_days=grouped_days,
        total_reviews=len(reviews),
        keyword=keyword,
        filter_category=filter_category,
        filter_meal_type=filter_meal_type,
        categories=CATEGORIES,
        meal_types=MEAL_TYPES,
    )


# ── 編輯紀錄 ──────────────────────────────────────────────────────────────

@app.route("/review/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_review(id):
    review = Review.query.get_or_404(id)

    if review.user_id != session["user_id"]:
        flash("您沒有權限編輯此紀錄。", "danger")
        return redirect(url_for("diary"))

    if request.method == "POST":
        restaurant_name = request.form.get("restaurant_name", "").strip()
        visit_date_str = request.form.get("visit_date", "").strip()
        meal_type = request.form.get("meal_type", "").strip()
        category = request.form.get("category", "").strip()
        price_str    = request.form.get("price",    "").strip()
        rating_str   = request.form.get("rating",   "").strip()
        calories_str = request.form.get("calories", "").strip()
        protein_str  = request.form.get("protein",  "").strip()
        comment = request.form.get("comment", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        visit_date = None
        price = rating = calories = protein = None

        if not restaurant_name:
            errors.append("餐廳名稱為必填。")

        if not visit_date_str:
            errors.append("用餐日期為必填。")
        else:
            try:
                visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append("日期格式不正確。")

        if price_str:
            try:
                price = float(price_str)
                if price < 0:
                    errors.append("價格不可為負數。")
            except ValueError:
                errors.append("價格必須為數字。")

        if rating_str:
            try:
                rating = int(rating_str)
                if not 1 <= rating <= 5:
                    errors.append("評分必須在 1 到 5 之間。")
            except ValueError:
                errors.append("評分必須為整數。")

        if calories_str:
            try:
                calories = float(calories_str)
                if calories < 0:
                    errors.append("熱量不可為負數。")
            except ValueError:
                errors.append("熱量必須為數字。")

        if protein_str:
            try:
                protein = float(protein_str)
                if protein < 0:
                    errors.append("蛋白質不可為負數。")
            except ValueError:
                errors.append("蛋白質必須為數字。")

        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template(
                "edit_review.html",
                review=review,
                meal_types=MEAL_TYPES,
                categories=CATEGORIES,
            )

        review.restaurant_name = restaurant_name
        review.visit_date = visit_date
        review.meal_type = meal_type or None
        review.category = category or None
        review.price = price
        review.rating = rating
        review.comment = comment or None
        review.address = address or None
        review.calories = calories
        review.protein = protein
        review.updated_at = datetime.utcnow()

        db.session.commit()

        flash("紀錄更新成功！", "success")
        return redirect(url_for("diary"))

    restaurant_names = [
        r.name for r in Restaurant.query.order_by(Restaurant.name).all()
    ]
    return render_template(
        "edit_review.html",
        review=review,
        meal_types=MEAL_TYPES,
        categories=CATEGORIES,
        restaurant_names=restaurant_names,
    )


# ── 刪除紀錄 ──────────────────────────────────────────────────────────────

@app.route("/review/<int:id>/delete", methods=["POST"])
@login_required
def delete_review(id):
    review = Review.query.get_or_404(id)

    if review.user_id != session["user_id"]:
        flash("您沒有權限刪除此紀錄。", "danger")
        return redirect(url_for("diary"))

    db.session.delete(review)
    db.session.commit()

    flash("紀錄已成功刪除。", "success")
    return redirect(url_for("diary"))


# ── 美食地圖 ──────────────────────────────────────────────────────────────

@app.route("/food_map")
@login_required
def food_map():
    reviews = (
        Review.query.filter(
            Review.user_id == session["user_id"],
            Review.address.isnot(None),
            Review.address != "",
        )
        .order_by(Review.visit_date.desc())
        .all()
    )
    return render_template("food_map.html", reviews=reviews)


# ---------------------------------------------------------------------------

# ── 餐廳資料庫 ────────────────────────────────────────────────────────────

@app.route("/restaurants")
def restaurants():
    all_restaurants = (
        Restaurant.query
        .order_by(Restaurant.area, Restaurant.name)
        .all()
    )
    return render_template("restaurants.html", restaurants=all_restaurants)


# ── API：菜單品項（供 new_review 的 JS 使用）────────────────────────────

@app.route("/api/menu")
def api_menu():
    name = request.args.get("restaurant", "").strip()
    if not name:
        return jsonify({"address": None, "items": []})
    restaurant = Restaurant.query.filter_by(name=name).first()
    if not restaurant:
        return jsonify({"address": None, "items": []})
    items = (
        MenuItem.query.filter_by(restaurant_id=restaurant.id)
        .order_by(MenuItem.item_name)
        .all()
    )
    def fmt_price(p):
        if p is None:
            return None
        return int(p) if p == int(p) else p
    return jsonify({
        "address": restaurant.address,
        "items": [
            {
                "item_name": item.item_name,
                "price": fmt_price(item.price),
                "calories": round(item.calories) if item.calories else None,
                "protein": round(item.protein, 1) if item.protein else None,
            }
            for item in items
        ],
    })


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
