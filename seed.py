"""
匯入餐廳與菜單資料到資料庫。

用法：
    python seed.py /path/to/餐廳資料資訊庫.xlsx
    python seed.py /path/to/餐廳資料資訊庫.xlsx --force   # 清除後重新匯入

需要額外套件（只在執行此腳本時需要，不用加入 requirements.txt）：
    pip install pandas openpyxl
"""
import re
import sys

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from app import app
from database import db
from models import MenuItem, Restaurant


def parse_price_level(value):
    if pd.isna(value):
        return None
    m = re.match(r"^(\d+)", str(value).strip())
    return int(m.group(1)) if m else None


def parse_number(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        m = re.match(r"^(\d+(?:\.\d+)?)", str(value).strip())
        return float(m.group(1)) if m else None


def seed(excel_path, force=False):
    with app.app_context():
        if force:
            MenuItem.query.delete()
            Restaurant.query.delete()
            db.session.commit()
            print("已清除舊資料。")
        elif Restaurant.query.count() > 0:
            print(f"資料庫已有 {Restaurant.query.count()} 間餐廳資料。")
            print("如需重新匯入，請加上 --force 參數。")
            return

        df_info = pd.read_excel(excel_path, sheet_name="餐廳資料")
        df_menu = pd.read_excel(excel_path, sheet_name="原表格")

        # ── 匯入餐廳詳細資料（21 間）──────────────────────────
        for _, row in df_info.iterrows():
            name = str(row["店名"]).strip() if pd.notna(row["店名"]) else None
            if not name:
                continue
            r = Restaurant(
                name=name,
                address=str(row["地址"]).strip() if pd.notna(row["地址"]) else None,
                area=str(row["區域"]).strip() if pd.notna(row["區域"]) else None,
                cuisine_style=str(row["餐點風格"]).strip() if pd.notna(row["餐點風格"]) else None,
                category=str(row["類型"]).strip() if pd.notna(row["類型"]) else None,
                is_healthy=bool(row["健康"] == 1.0) if pd.notna(row["健康"]) else False,
                price_level=parse_price_level(row["價位"]),
            )
            db.session.add(r)
            print(f"  餐廳：{name}")

        db.session.commit()

        # ── 匯入菜單品項（1258 道）────────────────────────────
        count = 0
        for _, row in df_menu.iterrows():
            r_name = str(row["餐廳名"]).strip() if pd.notna(row["餐廳名"]) else None
            item_name = str(row["商品"]).strip() if pd.notna(row["商品"]) else None
            if not r_name or not item_name:
                continue

            restaurant = Restaurant.query.filter_by(name=r_name).first()
            if not restaurant:
                restaurant = Restaurant(name=r_name)
                db.session.add(restaurant)
                db.session.flush()
                print(f"  新增餐廳（菜單用）：{r_name}")

            item = MenuItem(
                restaurant_id=restaurant.id,
                item_name=item_name,
                price=parse_number(row["價格(元)"]),
                calories=parse_number(row["熱量(kcal)"]),
                protein=parse_number(row["蛋白質(g)"]),
            )
            db.session.add(item)
            count += 1

        db.session.commit()

        print(f"\n✅ 匯入完成！")
        print(f"   餐廳：{Restaurant.query.count()} 間")
        print(f"   菜單：{MenuItem.query.count()} 道")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python seed.py /path/to/餐廳資料資訊庫.xlsx [--force]")
        sys.exit(1)
    excel_path = sys.argv[1]
    force = "--force" in sys.argv
    seed(excel_path, force=force)
