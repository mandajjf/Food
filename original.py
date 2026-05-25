import json
import calendar
import webbrowser

restaurants_file = "restaurants.json"
foodlog_file = "foodlog.json"


# ========================
# 讀取資料
# ========================
def load_data(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


# ========================
# 儲存資料
# ========================
def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


restaurants = load_data(restaurants_file)
food_log = load_data(foodlog_file)


# ========================
# 新增餐廳
# ========================
def add_restaurant():

    name = input("餐廳名稱: ")
    city = input("地區: ")

    print("\n餐點類型選擇")
    print("1 中餐")
    print("2 西餐")
    print("3 日式")
    print("4 韓式")
    print("5 甜點")
    print("6 其他")

    type_choice = input("請輸入編號: ")

    type_dict = {
        "1": "中餐",
        "2": "西餐",
        "3": "日式",
        "4": "韓式",
        "5": "甜點",
        "6": "其他"
    }

    food_type = type_dict.get(type_choice, "其他")

    rating = input("評分 (1-5): ")

    print("\n餐廳分類")
    print("1 ❤️ 喜愛餐廳")
    print("2 ⭐ 想去餐廳")
    print("3 👥 別人推薦")

    category_choice = input("請輸入編號: ")

    category_dict = {
        "1": "favorite",
        "2": "want_to_go",
        "3": "recommended"
    }

    category = category_dict.get(category_choice, "recommended")

    restaurants[name] = {
        "city": city,
        "type": food_type,
        "rating": rating,
        "category": category
    }

    save_data(restaurants_file, restaurants)

    print("✅ 餐廳已新增\n")


# ========================
# 查看餐廳
# ========================
def view_restaurants():

    if not restaurants:
        print("目前沒有餐廳資料\n")
        return

    print("\n=== 餐廳列表 ===")

    for name, info in restaurants.items():

        category_name = {
            "favorite": "❤️ 喜愛",
            "want_to_go": "⭐ 想去",
            "recommended": "👥 推薦"
        }.get(info["category"], "")

        print(f"{name} | {info['city']} | {info['type']} | ⭐{info['rating']} | {category_name}")

    print()


# ========================
# 刪除餐廳
# ========================
def delete_restaurant():

    name = input("請輸入要刪除的餐廳名稱: ")

    if name in restaurants:

        del restaurants[name]

        save_data(restaurants_file, restaurants)

        print("✅ 餐廳已刪除\n")

    else:
        print("❌ 找不到此餐廳\n")


# ========================
# Google Map 搜尋
# ========================
def map_search():

    name = input("輸入餐廳名稱: ")

    url = f"https://www.google.com/maps/search/{name}"

    webbrowser.open(url)


# ========================
# 紀錄吃了什麼
# ========================
def log_food():

    date = input("日期 (YYYY-MM-DD): ")

    restaurant = input("餐廳名稱: ")

    food_log[date] = restaurant

    save_data(foodlog_file, food_log)

    print("✅ 紀錄成功\n")


# ========================
# 顯示表格式月曆
# ========================
def show_calendar():

    year = int(input("年份: "))
    month = int(input("月份: "))

    cal = calendar.monthcalendar(year, month)

    print()
    print(calendar.month_name[month], year)
    print("-" * 64)

    headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for h in headers:
        print(f"| {h:^7}", end="")
    print("|")

    print("-" * 64)

    for week in cal:

        # 日期列
        for day in week:

            if day == 0:
                print("|       ", end="")
            else:
                print(f"| {day:^7}", end="")

        print("|")

        # 餐廳名稱列
        for day in week:

            if day == 0:
                print("|       ", end="")

            else:

                date = f"{year}-{month:02}-{day:02}"

                if date in food_log:

                    name = food_log[date][:7]

                    print(f"| {name:^7}", end="")

                else:
                    print("|       ", end="")

        print("|")

        print("-" * 64)


# ========================
# 主程式
# ========================
def main():

    while True:

        print("=== 個人美食地圖系統 ===")

        print("1 新增餐廳")
        print("2 查看餐廳")
        print("3 刪除餐廳")
        print("4 Google Map 搜尋")
        print("5 記錄今天吃什麼")
        print("6 查看飲食月曆")
        print("0 離開程式")

        print("\n👉 請輸入對應數字並按 Enter")

        choice = input("選擇功能: ")

        print()

        if choice == "1":
            add_restaurant()

        elif choice == "2":
            view_restaurants()

        elif choice == "3":
            delete_restaurant()

        elif choice == "4":
            map_search()

        elif choice == "5":
            log_food()

        elif choice == "6":
            show_calendar()

        elif choice == "0":
            print("程式已結束 👋")
            break

        else:
            print("❌ 輸入錯誤，請重新輸入\n")


main()