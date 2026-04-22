#!/usr/bin/env python3
from copy import deepcopy
from datetime import datetime, timedelta

from mysql_storage import init_mysql_database, load_data, save_data

DEFAULT_DATA = {
    "stores": [],
    "categories": [],
    "menu": [],
    "combos": [],
    "orders": [],
    "reviews": [],
    "users": [],
    "ai_conversations": [],
    "counters": {},
}

DEFAULT_AVATAR = "/static/store-avatar-default.svg"
DEFAULT_COVER = "/static/store-cover-default.svg"
NOW = datetime.now()

MERCHANT_SEEDS = [
    {
        "username": "merchant",
        "password": "merchant123",
        "store": {
            "name": "川味小馆",
            "description": "主打川菜小炒、盖饭和家常套餐，口味浓郁、下饭扎实。",
            "business_hours": "10:00-22:30",
            "business_status": "营业中",
            "rating": 4.8,
            "delivery_fee": 4.0,
            "min_order_amount": 20.0,
            "announcement": "招牌麻辣香锅和宫保鸡丁现点现炒，晚高峰建议提前下单。",
            "categories": [
                {"name": "招牌川菜", "items": [
                    ("麻辣香锅", "香辣够味，荤素可选，适合重口味用户。", 36.0),
                    ("宫保鸡丁", "经典川味，鸡丁鲜嫩，微辣回甜。", 28.0),
                    ("水煮牛肉", "麻辣鲜香，肉片嫩滑，适合配米饭。", 39.0),
                ]},
                {"name": "盖饭主食", "items": [
                    ("红烧茄子盖饭", "酱香浓郁，茄子软糯，适合工作日快餐。", 22.0),
                    ("鱼香肉丝盖饭", "酸甜开胃，肉丝入味，经典稳妥选择。", 24.0),
                    ("番茄牛腩饭", "番茄汤汁浓郁，牛腩软烂，暖胃饱腹。", 32.0),
                ]},
                {"name": "饮品小食", "items": [
                    ("冰镇酸梅汤", "解腻清爽，适合搭配辣味主菜。", 8.0),
                    ("红糖糍粑", "外酥里糯，收尾很合适。", 12.0),
                ]},
            ],
            "combos": [
                {"name": "单人下饭套餐", "description": "宫保鸡丁+红烧茄子盖饭+酸梅汤，工作餐稳妥之选。", "price": 42.0, "discount": 0.9,
                 "item_names": ["宫保鸡丁", "红烧茄子盖饭", "冰镇酸梅汤"]},
                {"name": "双人川味分享餐", "description": "麻辣香锅+鱼香肉丝盖饭+红糖糍粑，适合两人拼单。", "price": 68.0, "discount": 0.88,
                 "item_names": ["麻辣香锅", "鱼香肉丝盖饭", "红糖糍粑"]},
            ],
        },
    },
    {
        "username": "merchant2",
        "password": "merchant123",
        "store": {
            "name": "轻食能量站",
            "description": "主打轻食沙拉、能量碗和低负担饮品，适合午餐与健身后补给。",
            "business_hours": "08:30-21:00",
            "business_status": "营业中",
            "rating": 4.7,
            "delivery_fee": 3.0,
            "min_order_amount": 18.0,
            "announcement": "所有沙拉默认酱汁分装，支持少油少盐备注。",
            "categories": [
                {"name": "轻食沙拉", "items": [
                    ("香煎鸡胸能量沙拉", "鸡胸肉低脂高蛋白，搭配羽衣甘蓝和玉米粒。", 29.0),
                    ("牛油果虾仁沙拉", "清爽虾仁搭配牛油果，口感层次丰富。", 33.0),
                    ("地中海金枪鱼沙拉", "酸香开胃，适合想吃清淡的人群。", 31.0),
                ]},
                {"name": "能量主食", "items": [
                    ("藜麦鸡肉能量碗", "藜麦、鸡肉与时蔬组合，饱腹感足。", 32.0),
                    ("牛肉糙米饭", "谷物感扎实，适合午餐补能量。", 34.0),
                    ("温泉蛋南瓜碗", "口味柔和，适合晚餐轻负担。", 27.0),
                ]},
                {"name": "轻负担饮品", "items": [
                    ("羽衣甘蓝苹果汁", "酸甜清爽，蔬果比例均衡。", 14.0),
                    ("柠檬气泡美式", "提神不腻，适合加班日。", 16.0),
                ]},
            ],
            "combos": [
                {"name": "健身补给双拼", "description": "鸡胸沙拉+藜麦能量碗，适合运动后补充蛋白与碳水。", "price": 56.0, "discount": 0.9,
                 "item_names": ["香煎鸡胸能量沙拉", "藜麦鸡肉能量碗"]},
                {"name": "清爽下午轻食餐", "description": "牛油果虾仁沙拉+羽衣甘蓝苹果汁，适合下午茶时段。", "price": 47.0, "discount": 0.92,
                 "item_names": ["牛油果虾仁沙拉", "羽衣甘蓝苹果汁"]},
            ],
        },
    },
    {
        "username": "merchant3",
        "password": "merchant123",
        "store": {
            "name": "粤式煲仔食堂",
            "description": "煲仔饭、炖汤与广式小食齐全，口味偏鲜香清润。",
            "business_hours": "09:30-21:30",
            "business_status": "营业中",
            "rating": 4.8,
            "delivery_fee": 4.5,
            "min_order_amount": 22.0,
            "announcement": "每日例汤现熬，煲仔饭现点现做，锅巴口感更香。",
            "categories": [
                {"name": "煲仔饭", "items": [
                    ("腊味双拼煲仔饭", "腊肠腊肉双拼，锅巴香气十足。", 28.0),
                    ("豉汁排骨煲仔饭", "排骨嫩滑，酱香浓郁，很适合晚餐。", 29.0),
                    ("香菇滑鸡煲仔饭", "鸡肉嫩滑，味道温和，接受度高。", 27.0),
                ]},
                {"name": "广式炖汤", "items": [
                    ("虫草花炖鸡汤", "汤头鲜甜，适合天气转凉时点。", 18.0),
                    ("玉米胡萝卜排骨汤", "清甜暖胃，适合搭配煲仔饭。", 16.0),
                ]},
                {"name": "粤式小点", "items": [
                    ("豉油皇炒面", "经典港风味道，镬气十足。", 24.0),
                    ("流沙奶黄包", "甜咸平衡，适合收尾。", 14.0),
                ]},
            ],
            "combos": [
                {"name": "招牌煲仔单人餐", "description": "腊味双拼煲仔饭+玉米排骨汤，经典稳妥。", "price": 42.0, "discount": 0.9,
                 "item_names": ["腊味双拼煲仔饭", "玉米胡萝卜排骨汤"]},
            ],
        },
    },
    {
        "username": "merchant4",
        "password": "merchant123",
        "store": {
            "name": "深夜烧烤局",
            "description": "夜宵聚会店，烧烤、小龙虾和主食都偏重口，适合晚间下单。",
            "business_hours": "17:30-02:00",
            "business_status": "营业中",
            "rating": 4.6,
            "delivery_fee": 5.0,
            "min_order_amount": 35.0,
            "announcement": "夜宵高峰时段订单较多，推荐提前下单锁定出餐时间。",
            "categories": [
                {"name": "烧烤串品", "items": [
                    ("羊肉串", "肥瘦相间，孜然香味足。", 4.0),
                    ("蜜汁鸡翅中", "外焦里嫩，带一点甜口。", 12.0),
                    ("烤掌中宝", "口感脆弹，适合搭配啤酒。", 14.0),
                ]},
                {"name": "夜宵主菜", "items": [
                    ("蒜蓉小龙虾", "蒜香浓郁，口感鲜甜，适合分享。", 88.0),
                    ("麻辣小龙虾", "重口夜宵人气款，麻辣过瘾。", 88.0),
                    ("锡纸花甲粉", "热乎鲜辣，夜宵感很足。", 26.0),
                ]},
                {"name": "主食饮品", "items": [
                    ("炒方便面", "重油香型，夜宵经典搭子。", 16.0),
                    ("冰峰汽水", "解辣解腻，适合烧烤搭配。", 6.0),
                ]},
            ],
            "combos": [
                {"name": "夜宵双人分享餐", "description": "麻辣小龙虾+羊肉串6串+冰峰汽水2瓶，适合两人夜宵。", "price": 128.0, "discount": 0.88,
                 "item_names": ["麻辣小龙虾", "羊肉串", "冰峰汽水"]},
            ],
        },
    },
    {
        "username": "merchant5",
        "password": "merchant123",
        "store": {
            "name": "海风寿司屋",
            "description": "寿司、丼饭与乌冬搭配齐全，风格偏清爽，适合双人餐与下午晚餐。",
            "business_hours": "10:30-21:30",
            "business_status": "营业中",
            "rating": 4.7,
            "delivery_fee": 4.0,
            "min_order_amount": 25.0,
            "announcement": "寿司类商品建议尽快食用，口感最佳。",
            "categories": [
                {"name": "寿司卷", "items": [
                    ("鳗鱼芝士卷", "鳗鱼咸甜适中，芝士增加顺滑口感。", 28.0),
                    ("三文鱼牛油果卷", "清爽油润，适合第一次点寿司的人。", 26.0),
                    ("炙烧蟹柳卷", "火炙香气明显，层次感足。", 24.0),
                ]},
                {"name": "日式主食", "items": [
                    ("照烧鸡腿丼", "鸡腿肉鲜嫩，酱汁浓郁。", 29.0),
                    ("肥牛温泉蛋丼", "肥牛咸香，温泉蛋拌饭口感柔和。", 32.0),
                    ("豚骨叉烧乌冬", "汤底浓郁，乌冬顺滑，适合冷天。", 31.0),
                ]},
                {"name": "小食饮品", "items": [
                    ("章鱼小丸子", "外酥内软，酱香浓郁。", 18.0),
                    ("抹茶牛乳", "甜度柔和，适合寿司后收尾。", 16.0),
                ]},
            ],
            "combos": [
                {"name": "日式双人精选", "description": "寿司卷+照烧鸡腿丼+章鱼小丸子，适合两人分享。", "price": 72.0, "discount": 0.9,
                 "item_names": ["三文鱼牛油果卷", "照烧鸡腿丼", "章鱼小丸子"]},
            ],
        },
    },
    {
        "username": "merchant6",
        "password": "merchant123",
        "store": {
            "name": "北方面馆",
            "description": "主打汤面、拌面和北方面点，适合午餐与加班晚餐。",
            "business_hours": "07:30-22:00",
            "business_status": "营业中",
            "rating": 4.7,
            "delivery_fee": 3.5,
            "min_order_amount": 16.0,
            "announcement": "汤面默认热汤出餐，支持备注不要香菜。",
            "categories": [
                {"name": "招牌汤面", "items": [
                    ("番茄牛腩面", "酸甜浓汤配软烂牛腩，饱腹感很强。", 28.0),
                    ("老北京炸酱面", "酱香浓郁，黄瓜丝提味解腻。", 22.0),
                    ("酸菜肥牛面", "微酸开胃，适合想吃热汤时点。", 29.0),
                ]},
                {"name": "面点小吃", "items": [
                    ("鲜肉锅贴", "底脆汁多，适合搭配汤面。", 16.0),
                    ("牛肉馅饼", "外皮酥香，内馅扎实。", 14.0),
                ]},
                {"name": "清爽配饮", "items": [
                    ("冰豆浆", "口感细腻，适合早餐和午餐。", 7.0),
                    ("酸梅汤", "解腻清爽。", 8.0),
                ]},
            ],
            "combos": [
                {"name": "暖胃工作餐", "description": "番茄牛腩面+鲜肉锅贴，适合加班日补能量。", "price": 40.0, "discount": 0.9,
                 "item_names": ["番茄牛腩面", "鲜肉锅贴"]},
            ],
        },
    },
    {
        "username": "merchant7",
        "password": "merchant123",
        "store": {
            "name": "甜心烘焙铺",
            "description": "甜品、面包和饮品齐全，适合早餐、下午茶和治愈时刻。",
            "business_hours": "08:00-20:30",
            "business_status": "营业中",
            "rating": 4.9,
            "delivery_fee": 2.5,
            "min_order_amount": 15.0,
            "announcement": "每日鲜烤面包与蛋糕数量有限，建议尽早下单。",
            "categories": [
                {"name": "招牌蛋糕", "items": [
                    ("海盐奶油小蛋糕", "奶油清甜不腻，适合想吃点治愈感时点。", 18.0),
                    ("草莓盒子蛋糕", "草莓酸甜，口感轻盈。", 22.0),
                    ("提拉米苏杯", "咖啡香浓郁，层次丰富。", 20.0),
                ]},
                {"name": "烘焙面包", "items": [
                    ("黄油牛角包", "外酥里柔，早餐人气款。", 10.0),
                    ("肉松小贝", "咸甜平衡，口感轻软。", 14.0),
                    ("芋泥麻薯包", "软糯有嚼劲，饱腹感不错。", 13.0),
                ]},
                {"name": "咖啡特饮", "items": [
                    ("焦糖拿铁", "甜香柔和，适合下午茶。", 18.0),
                    ("茉莉鲜奶茶", "花香清爽，甜度适中。", 16.0),
                ]},
            ],
            "combos": [
                {"name": "治愈下午茶双拼", "description": "海盐奶油小蛋糕+焦糖拿铁，适合想犒劳自己时点。", "price": 34.0, "discount": 0.92,
                 "item_names": ["海盐奶油小蛋糕", "焦糖拿铁"]},
            ],
        },
    },
    {
        "username": "merchant8",
        "password": "merchant123",
        "store": {
            "name": "泰想吃",
            "description": "泰式简餐与热带饮品结合，酸辣开胃，适合想换口味的时候。",
            "business_hours": "10:00-22:00",
            "business_status": "营业中",
            "rating": 4.6,
            "delivery_fee": 4.5,
            "min_order_amount": 22.0,
            "announcement": "泰式口味默认微辣，可备注少辣或不要香菜。",
            "categories": [
                {"name": "泰式主食", "items": [
                    ("冬阴功海鲜面", "酸辣鲜香，海鲜风味浓郁。", 34.0),
                    ("咖喱鸡腿饭", "咖喱香气浓厚，鸡腿肉软嫩。", 30.0),
                    ("菠萝海鲜炒饭", "酸甜开胃，颗粒分明。", 29.0),
                ]},
                {"name": "小食拼盘", "items": [
                    ("泰式鸡翅", "外皮焦香，甜辣平衡。", 18.0),
                    ("虾片拼盘", "适合多人分享的小食。", 12.0),
                ]},
                {"name": "热带饮品", "items": [
                    ("椰青冰饮", "清甜解辣，适合搭配重口主食。", 15.0),
                    ("泰式奶茶", "茶香浓郁，甜感明显。", 14.0),
                ]},
            ],
            "combos": [
                {"name": "泰式开胃双人餐", "description": "咖喱鸡腿饭+菠萝海鲜炒饭+椰青冰饮，适合双人换口味。", "price": 68.0, "discount": 0.9,
                 "item_names": ["咖喱鸡腿饭", "菠萝海鲜炒饭", "椰青冰饮"]},
            ],
        },
    },
]

CUSTOMER_SEEDS = [
    {"username": "alice", "password": "alice123", "display_name": "Alice", "phone": "13800000001", "addresses": [{"name": "Alice", "address": "软件园一期 2 栋 1203", "phone": "13800000001", "is_default": True}]},
    {"username": "bob", "password": "bob123", "display_name": "Bob", "phone": "13800000002", "addresses": [{"name": "Bob", "address": "大学城南路 18 号 3 舍", "phone": "13800000002", "is_default": True}]},
    {"username": "cici", "password": "cici123", "display_name": "Cici", "phone": "13800000003", "addresses": [{"name": "Cici", "address": "星河公寓 5 栋 602", "phone": "13800000003", "is_default": True}]},
]

ADMIN_SEED = {"username": "admin", "password": "admin123456", "display_name": "系统管理员", "phone": "13800009999"}

SAMPLE_ORDER_BLUEPRINTS = [
    {"customer": "alice", "store": "川味小馆", "items": [("麻辣香锅", 1), ("冰镇酸梅汤", 1)], "status": "已完成", "days_ago": 1},
    {"customer": "alice", "store": "轻食能量站", "items": [("香煎鸡胸能量沙拉", 1), ("羽衣甘蓝苹果汁", 1)], "status": "已完成", "days_ago": 3},
    {"customer": "bob", "store": "粤式煲仔食堂", "items": [("腊味双拼煲仔饭", 1), ("玉米胡萝卜排骨汤", 1)], "status": "已完成", "days_ago": 2},
    {"customer": "bob", "store": "北方面馆", "items": [("番茄牛腩面", 1), ("鲜肉锅贴", 1)], "status": "配送中", "days_ago": 0},
    {"customer": "cici", "store": "海风寿司屋", "items": [("三文鱼牛油果卷", 1), ("照烧鸡腿丼", 1)], "status": "已完成", "days_ago": 4},
    {"customer": "cici", "store": "甜心烘焙铺", "items": [("海盐奶油小蛋糕", 1), ("焦糖拿铁", 1)], "status": "已完成", "days_ago": 0},
    {"customer": "alice", "store": "泰想吃", "items": [("咖喱鸡腿饭", 1), ("椰青冰饮", 1)], "status": "已接单", "days_ago": 0},
    {"customer": "bob", "store": "深夜烧烤局", "items": [("麻辣小龙虾", 1), ("冰峰汽水", 2)], "status": "已完成", "days_ago": 5},
]

SAMPLE_REVIEWS = [
    {"customer": "alice", "store": "川味小馆", "rating": 5, "delivery_rating": 4, "packaging_rating": 5, "taste_rating": 5, "content": "香锅很入味，酸梅汤解辣，整体很适合工作日晚餐。"},
    {"customer": "bob", "store": "粤式煲仔食堂", "rating": 4, "delivery_rating": 5, "packaging_rating": 4, "taste_rating": 4, "content": "锅巴很香，汤也很清甜，适合想吃热乎饭的时候点。"},
    {"customer": "cici", "store": "海风寿司屋", "rating": 5, "delivery_rating": 5, "packaging_rating": 5, "taste_rating": 4, "content": "寿司很新鲜，照烧鸡腿丼分量也不错，双人晚餐很稳。"},
    {"customer": "cici", "store": "甜心烘焙铺", "rating": 5, "delivery_rating": 5, "packaging_rating": 5, "taste_rating": 5, "content": "蛋糕真的很治愈，咖啡也顺口，下午茶心情直接拉满。"},
]


def make_timestamp(days_ago=0, hour=12):
    moment = NOW - timedelta(days=days_ago)
    return moment.replace(hour=hour, minute=15, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def next_id(records, start=1):
    if not records:
        return start
    return max(int(record.get("id", 0)) for record in records) + 1


def ensure_counter(data, key, value):
    current = int((data.get("counters") or {}).get(key, 0))
    data.setdefault("counters", {})[key] = max(current, value)


def build_user(username, password, role, user_id, **extra):
    raw_addresses = deepcopy(extra.get("addresses", []))
    normalized_addresses = []
    for index, address in enumerate(raw_addresses, start=1):
        normalized_addresses.append({
            "id": address.get("id", index),
            "name": address.get("name", username),
            "address": address.get("address", ""),
            "phone": address.get("phone", extra.get("phone", "")),
            "is_default": bool(address.get("is_default", index == 1)),
            "created_at": address.get("created_at", make_timestamp(10, 9)),
        })
    return {
        "id": user_id,
        "username": username,
        "password": password,
        "phone": extra.get("phone", ""),
        "display_name": extra.get("display_name", ""),
        "email": extra.get("email", ""),
        "gender": extra.get("gender", ""),
        "birthday": extra.get("birthday", ""),
        "bio": extra.get("bio", ""),
        "role": role,
        "account_status": "active",
        "risk_status": "normal",
        "admin_note": "",
        "store_id": extra.get("store_id"),
        "store_name": extra.get("store_name", ""),
        "store_description": extra.get("store_description", ""),
        "addresses": normalized_addresses,
        "favorite_store_ids": deepcopy(extra.get("favorite_store_ids", [])),
        "favorite_menu_ids": deepcopy(extra.get("favorite_menu_ids", [])),
        "recent_views": deepcopy(extra.get("recent_views", [])),
        "created_at": extra.get("created_at", make_timestamp(12, 9)),
    }


def without_keys(source, *keys):
    return {key: value for key, value in source.items() if key not in keys}


def main():
    init_mysql_database(DEFAULT_DATA)
    data = load_data(DEFAULT_DATA)

    users = data.setdefault("users", [])
    stores = data.setdefault("stores", [])
    categories = data.setdefault("categories", [])
    menu = data.setdefault("menu", [])
    combos = data.setdefault("combos", [])
    orders = data.setdefault("orders", [])
    reviews = data.setdefault("reviews", [])
    data.setdefault("ai_conversations", [])
    data.setdefault("counters", {})

    user_by_username = {user["username"]: user for user in users}
    store_by_name = {store["name"]: store for store in stores}

    next_user = next_id(users)
    next_store = next_id(stores)
    next_category = next_id(categories)
    next_menu = next_id(menu)
    next_combo = next_id(combos)
    next_order = next_id(orders)
    next_review = next_id(reviews)

    if ADMIN_SEED["username"] not in user_by_username:
        admin = build_user(
            ADMIN_SEED["username"],
            ADMIN_SEED["password"],
            "admin",
            next_user,
            **without_keys(ADMIN_SEED, "username", "password"),
        )
        users.append(admin)
        user_by_username[admin["username"]] = admin
        next_user += 1

    for seed in CUSTOMER_SEEDS:
        if seed["username"] in user_by_username:
            continue
        customer = build_user(
            seed["username"],
            seed["password"],
            "customer",
            next_user,
            **without_keys(seed, "username", "password"),
        )
        users.append(customer)
        user_by_username[customer["username"]] = customer
        next_user += 1

    for merchant_seed in MERCHANT_SEEDS:
        username = merchant_seed["username"]
        store_seed = merchant_seed["store"]
        user = user_by_username.get(username)
        if not user:
            user = build_user(
                username,
                merchant_seed["password"],
                "merchant",
                next_user,
                display_name=store_seed["name"],
                phone=f"1390000{next_user:04d}"[-11:],
                store_name=store_seed["name"],
                store_description=store_seed["description"],
                addresses=[],
            )
            users.append(user)
            user_by_username[username] = user
            next_user += 1

        store = store_by_name.get(store_seed["name"])
        if not store:
            store = {
                "id": next_store,
                "owner_user_id": user["id"],
                "name": store_seed["name"],
                "description": store_seed["description"],
                "status": "active",
                "avatar_url": DEFAULT_AVATAR,
                "cover_image_url": DEFAULT_COVER,
                "business_status": store_seed["business_status"],
                "business_hours": store_seed["business_hours"],
                "rating": store_seed["rating"],
                "delivery_fee": store_seed["delivery_fee"],
                "min_order_amount": store_seed["min_order_amount"],
                "announcement": store_seed["announcement"],
                "created_at": make_timestamp(15, 10),
            }
            stores.append(store)
            store_by_name[store["name"]] = store
            next_store += 1

        user["store_id"] = store["id"]
        user["store_name"] = store["name"]
        user["store_description"] = store["description"]

        category_ids_by_name = {cat["name"]: cat["id"] for cat in categories if cat.get("store_id") == store["id"]}
        item_ids_by_name = {item["name"]: item["id"] for item in menu if item.get("store_id") == store["id"]}

        for category_seed in store_seed["categories"]:
            category_id = category_ids_by_name.get(category_seed["name"])
            if not category_id:
                category_id = next_category
                categories.append({
                    "id": category_id,
                    "name": category_seed["name"],
                    "store_id": store["id"],
                    "status": "active",
                })
                category_ids_by_name[category_seed["name"]] = category_id
                next_category += 1

            for item_name, item_desc, item_price in category_seed["items"]:
                if item_name in item_ids_by_name:
                    continue
                menu.append({
                    "id": next_menu,
                    "name": item_name,
                    "description": item_desc,
                    "price": float(item_price),
                    "category_id": category_id,
                    "store_id": store["id"],
                    "image": None,
                    "status": "active",
                })
                item_ids_by_name[item_name] = next_menu
                next_menu += 1

        combo_names_existing = {combo["name"] for combo in combos if combo.get("store_id") == store["id"]}
        for combo_seed in store_seed["combos"]:
            if combo_seed["name"] in combo_names_existing:
                continue
            combo_item_ids = [item_ids_by_name[name] for name in combo_seed["item_names"] if name in item_ids_by_name]
            if not combo_item_ids:
                continue
            combos.append({
                "id": next_combo,
                "name": combo_seed["name"],
                "description": combo_seed["description"],
                "price": float(combo_seed["price"]),
                "discount": float(combo_seed["discount"]),
                "store_id": store["id"],
                "status": "active",
                "items": combo_item_ids,
            })
            next_combo += 1

    if not orders:
        menu_index = {(item["store_id"], item["name"]): item for item in menu}
        store_name_index = {store["name"]: store for store in stores}
        for blueprint in SAMPLE_ORDER_BLUEPRINTS:
            store = store_name_index[blueprint["store"]]
            order_items = []
            total = 0.0
            for item_name, quantity in blueprint["items"]:
                item = menu_index.get((store["id"], item_name))
                if not item:
                    continue
                subtotal = round(float(item["price"]) * int(quantity), 2)
                order_items.append({
                    "id": item["id"],
                    "name": item["name"],
                    "price": float(item["price"]),
                    "quantity": int(quantity),
                    "subtotal": subtotal,
                    "type": "item",
                })
                total += subtotal
            orders.append({
                "id": next_order,
                "customer": blueprint["customer"],
                "store_id": store["id"],
                "store_name": store["name"],
                "items": order_items,
                "total": round(total, 2),
                "status": blueprint["status"],
                "created_at": make_timestamp(blueprint["days_ago"], 12 + (next_order % 6)),
                "source_order_id": None,
            })
            next_order += 1

    if not reviews:
        completed_orders = [order for order in orders if order.get("status") == "已完成"]
        for seed in SAMPLE_REVIEWS:
            matching_order = next(
                (order for order in completed_orders if order.get("customer") == seed["customer"] and order.get("store_name") == seed["store"]),
                None,
            )
            if not matching_order:
                continue
            reviews.append({
                "id": next_review,
                "order_id": matching_order["id"],
                "customer": seed["customer"],
                "store_id": matching_order["store_id"],
                "store_name": matching_order["store_name"],
                "rating": float(seed["rating"]),
                "delivery_rating": float(seed["delivery_rating"]),
                "packaging_rating": float(seed["packaging_rating"]),
                "taste_rating": float(seed["taste_rating"]),
                "content": seed["content"],
                "image": None,
                "created_at": make_timestamp(0, 19),
            })
            next_review += 1

    # 补一些收藏和最近浏览，便于前台演示个性化推荐
    favorite_store_map = {
        "alice": [store_by_name["川味小馆"]["id"], store_by_name["甜心烘焙铺"]["id"]],
        "bob": [store_by_name["北方面馆"]["id"], store_by_name["粤式煲仔食堂"]["id"]],
        "cici": [store_by_name["海风寿司屋"]["id"], store_by_name["轻食能量站"]["id"]],
    }
    favorite_item_name_map = {
        "alice": ["麻辣香锅", "海盐奶油小蛋糕"],
        "bob": ["番茄牛腩面", "腊味双拼煲仔饭"],
        "cici": ["三文鱼牛油果卷", "牛油果虾仁沙拉"],
    }
    item_lookup_by_name = {item["name"]: item for item in menu}
    for username, store_ids in favorite_store_map.items():
        user = user_by_username.get(username)
        if not user:
            continue
        user["favorite_store_ids"] = store_ids
        user["favorite_menu_ids"] = [item_lookup_by_name[name]["id"] for name in favorite_item_name_map.get(username, []) if name in item_lookup_by_name]
        user["recent_views"] = [
            {"type": "store", "store_id": store_ids[0], "item_id": None, "viewed_at": make_timestamp(0, 11)},
            {"type": "item", "store_id": item_lookup_by_name[favorite_item_name_map[username][0]]["store_id"], "item_id": item_lookup_by_name[favorite_item_name_map[username][0]]["id"], "viewed_at": make_timestamp(0, 12)},
        ]

    ensure_counter(data, "next_user_id", next_user)
    ensure_counter(data, "next_store_id", next_store)
    ensure_counter(data, "next_category_id", next_category)
    ensure_counter(data, "next_menu_id", next_menu)
    ensure_counter(data, "next_combo_id", next_combo)
    ensure_counter(data, "next_order_id", next_order)
    ensure_counter(data, "next_review_id", next_review)

    save_data(data)
    print("示例店铺、分类、菜品、套餐、订单与评价数据已写入 MySQL。")
    print(f"店铺: {len(stores)} | 分类: {len(categories)} | 菜品: {len(menu)} | 套餐: {len(combos)} | 订单: {len(orders)} | 评价: {len(reviews)} | 用户: {len(users)}")


if __name__ == "__main__":
    main()
