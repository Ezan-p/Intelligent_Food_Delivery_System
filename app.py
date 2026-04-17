import os
import sys
import json
import re
from urllib.parse import urlparse
from flask import Flask, jsonify, request, render_template
from datetime import datetime
import requests

app = Flask(__name__)

# 数据文件路径
DATA_DIR = 'data'
DATA_FILE = os.path.join(DATA_DIR, 'app_data.json')

# 创建 data 目录（如果不存在）
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 远程 AI API 配置
DEFAULT_REMOTE_AI_BASE_URL = "https://web-2042154320335900674-iada.ksai.scnet.cn:58043/"
DEFAULT_REMOTE_AI_MODEL = ""

def normalize_remote_ai_api_url(url):
    """支持填写基地址，自动补成 OpenAI 兼容聊天接口路径"""
    normalized = (url or "").strip()
    if not normalized:
        return ""

    parsed = urlparse(normalized)
    path = (parsed.path or "").strip()
    if not path or path == "/":
        return normalized.rstrip("/") + "/v1/chat/completions"
    return normalized

REMOTE_AI_API_URL = normalize_remote_ai_api_url(
    os.environ.get('REMOTE_AI_API_URL', DEFAULT_REMOTE_AI_BASE_URL)
)
REMOTE_AI_API_KEY = os.environ.get('REMOTE_AI_API_KEY', '').strip()
REMOTE_AI_MODEL = os.environ.get('REMOTE_AI_MODEL', DEFAULT_REMOTE_AI_MODEL).strip()
REMOTE_AI_TIMEOUT = float(os.environ.get('REMOTE_AI_TIMEOUT', '120'))
REMOTE_AI_CONNECT_TIMEOUT = float(os.environ.get('REMOTE_AI_CONNECT_TIMEOUT', '10'))
REMOTE_AI_MAX_TOKENS = int(os.environ.get('REMOTE_AI_MAX_TOKENS', '768'))
REMOTE_AI_CONTINUE_ROUNDS = int(os.environ.get('REMOTE_AI_CONTINUE_ROUNDS', '2'))
AI_CONTEXT_MAX_MESSAGES = int(os.environ.get('AI_CONTEXT_MAX_MESSAGES', '12'))
REMOTE_AI_SYSTEM_PROMPT = os.environ.get(
    'REMOTE_AI_SYSTEM_PROMPT',
    '你是智能外卖平台的AI客服助手。请用友好、专业、简洁的语气解答与菜品、下单、配送、退款、地址相关问题。'
    '不要输出你的思考过程、推理步骤或中间分析，只输出最终答复内容。'
).strip()
ACTIVE_REMOTE_AI_API_URL = REMOTE_AI_API_URL
USE_MODEL_FIELD = True
ai_conversation_store = {}

def looks_like_truncated_answer(text):
    if not isinstance(text, str):
        return False
    s = text.strip()
    if len(s) < 40:
        return False

    # 以完整句末符号结束时通常已完成
    end_ok = ("。", "！", "？", ".", "!", "?", "）", ")", "]", "】", "」", "\"")
    if s.endswith(end_ok):
        return False

    # 以连接性符号结尾通常是截断
    likely_cut = ("，", ",", "、", "：", ":", "；", ";", "（", "(", "-", "—", "…")
    if s.endswith(likely_cut):
        return True

    # 默认：较长但无正常句末，按疑似截断处理
    return True

def merge_ai_chunks(base_text, extra_text):
    base = (base_text or "").strip()
    extra = (extra_text or "").strip()
    if not base:
        return extra
    if not extra:
        return base
    if extra in base:
        return base

    # 简单重叠去重：匹配 base 后缀与 extra 前缀
    max_overlap = min(len(base), len(extra), 120)
    overlap = 0
    for i in range(max_overlap, 10, -1):
        if base[-i:] == extra[:i]:
            overlap = i
            break
    if overlap > 0:
        return (base + extra[overlap:]).strip()
    return (base + "\n" + extra).strip()

def generate_conversation_id():
    return f"conv_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"

def trim_conversation_history(history):
    if not isinstance(history, list):
        return []
    if AI_CONTEXT_MAX_MESSAGES <= 0:
        return history
    return history[-AI_CONTEXT_MAX_MESSAGES:]

def get_user_by_session(session_id):
    if not session_id or session_id not in user_sessions:
        return None
    user_id = user_sessions.get(session_id)
    return next((u for u in users if u.get('id') == user_id), None)

def build_business_context_text(session_id=None):
    menu_preview = menu[:8]
    combos_preview = combos[:5]
    orders_preview = orders[-5:]

    lines = [
        "你可参考以下平台业务上下文回答，信息不足时请明确说明并引导用户提供信息。"
    ]

    if menu_preview:
        menu_text = "；".join([f"{item.get('name')} ¥{item.get('price')}" for item in menu_preview])
        lines.append(f"当前在售菜品（部分）：{menu_text}")

    if combos_preview:
        combo_text = "；".join([f"{item.get('name')} ¥{item.get('price')}" for item in combos_preview])
        lines.append(f"当前套餐（部分）：{combo_text}")

    user = get_user_by_session(session_id)
    if user:
        user_orders = [o for o in orders if o.get("customer") == user.get("username")]
        recent = user_orders[-3:]
        if recent:
            recent_text = "；".join([
                f"订单#{o.get('id')} 状态:{o.get('status')} 金额:¥{o.get('total')}"
                for o in recent
            ])
            lines.append(f"当前登录用户：{user.get('username')}，最近订单：{recent_text}")
        else:
            lines.append(f"当前登录用户：{user.get('username')}，暂无订单记录。")
    elif orders_preview:
        recent_text = "；".join([
            f"订单#{o.get('id')} 用户:{o.get('customer')} 状态:{o.get('status')}"
            for o in orders_preview
        ])
        lines.append(f"平台最近订单（摘要）：{recent_text}")

    lines.append("如果用户询问订单状态，优先引导提供订单号或用户名。")
    return "\n".join(lines)

def build_remote_ai_candidate_urls(url):
    """当返回404时，自动尝试常见接口路径"""
    if not url:
        return []

    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = (parsed.path or "").rstrip("/")

    candidates = []
    def add_candidate(candidate):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add_candidate(url)

    if not path or path == "":
        add_candidate(origin + "/v1/chat/completions")
        add_candidate(origin + "/chat/completions")
        add_candidate(origin + "/api/chat")
        add_candidate(origin + "/generate")
    elif path.endswith("/v1/chat/completions"):
        add_candidate(origin + "/chat/completions")
        add_candidate(origin + "/v1/completions")
        add_candidate(origin + "/api/chat")
    else:
        add_candidate(origin + "/v1/chat/completions")
        add_candidate(origin + "/chat/completions")
        add_candidate(origin + "/api/chat")

    return candidates

# 默认数据结构
DEFAULT_DATA = {
    "categories": [
        {"id": 1, "name": "主菜"},
        {"id": 2, "name": "面食"},
        {"id": 3, "name": "饮品"},
        {"id": 4, "name": "套餐"}
    ],
    "menu": [
        {"id": 1, "name": "麻辣香锅", "description": "香辣可口，大份足量。", "price": 36.0, "category_id": 1, "image": None},
        {"id": 2, "name": "宫保鸡丁", "description": "经典川菜，微辣下饭。", "price": 28.0, "category_id": 1, "image": None},
        {"id": 3, "name": "番茄牛腩面", "description": "汤浓味足，面条劲道。", "price": 32.0, "category_id": 2, "image": None},
        {"id": 4, "name": "红烧茄子盖饭", "description": "家常口味，茄子软糯。", "price": 22.0, "category_id": 1, "image": None},
        {"id": 5, "name": "小龙虾套餐", "description": "麻辣龙虾，赠送饮料。", "price": 88.0, "category_id": 4, "image": None}
    ],
    "combos": [
        {"id": 1, "name": "家庭套餐", "description": "适合家庭聚餐", "price": 128.0, "items": [1, 2, 3], "discount": 0.9}
    ],
    "orders": [],
    "users": [],
    "counters": {
        "next_order_id": 1,
        "next_menu_id": 6,
        "next_category_id": 5,
        "next_combo_id": 2,
        "next_user_id": 1
    }
}

# 数据加载和保存函数
def load_data():
    """从文件加载数据，如果文件不存在则使用默认数据"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return DEFAULT_DATA.copy()
    return DEFAULT_DATA.copy()

def save_data(data):
    """将数据保存到文件"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Error saving data: {e}")

def get_all_data():
    """获取当前所有数据"""
    try:
        return load_data()
    except:
        return DEFAULT_DATA.copy()

# 加载数据
app_data = load_data()
categories = app_data.get('categories', DEFAULT_DATA['categories'])
menu = app_data.get('menu', DEFAULT_DATA['menu'])
combos = app_data.get('combos', DEFAULT_DATA['combos'])
orders = app_data.get('orders', DEFAULT_DATA['orders'])
users = app_data.get('users', DEFAULT_DATA['users'])
counters = app_data.get('counters', DEFAULT_DATA['counters'])

next_order_id = counters.get('next_order_id', 1)
next_menu_id = counters.get('next_menu_id', 6)
next_category_id = counters.get('next_category_id', 5)
next_combo_id = counters.get('next_combo_id', 2)
next_user_id = counters.get('next_user_id', 1)

def update_counters():
    """更新计数器"""
    global next_order_id, next_menu_id, next_category_id, next_combo_id, next_user_id, counters
    counters = {
        'next_order_id': next_order_id,
        'next_menu_id': next_menu_id,
        'next_category_id': next_category_id,
        'next_combo_id': next_combo_id,
        'next_user_id': next_user_id
    }

def persist_data():
    """持久化所有数据到文件"""
    update_counters()
    data = {
        'categories': categories,
        'menu': menu,
        'combos': combos,
        'orders': orders,
        'users': users,
        'counters': counters
    }
    save_data(data)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/merchant')
def merchant():
    return render_template('merchant.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

# 分类管理API
@app.route('/api/categories', methods=['GET'])
def get_categories():
    return jsonify({"categories": categories})

@app.route('/api/categories', methods=['POST'])
def add_category():
    global next_category_id
    data = request.get_json() or {}
    name = data.get('name', '').strip()

    if not name:
        return jsonify({"error": "分类名称不能为空。"}), 400

    category = {
        "id": next_category_id,
        "name": name
    }
    categories.append(category)
    next_category_id += 1
    persist_data()
    return jsonify({"category": category}), 201

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    data = request.get_json() or {}
    category = next((c for c in categories if c['id'] == category_id), None)
    if not category:
        return jsonify({"error": "未找到该分类。"}), 404

    name = data.get('name', '').strip()
    if not name:
        return jsonify({"error": "分类名称不能为空。"}), 400

    category['name'] = name
    persist_data()
    return jsonify({"category": category})

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    global categories, menu
    category = next((c for c in categories if c['id'] == category_id), None)
    if not category:
        return jsonify({"error": "未找到该分类。"}), 404

    # 检查是否有商品使用此分类
    if any(item['category_id'] == category_id for item in menu):
        return jsonify({"error": "该分类下有商品，无法删除。"}), 400

    categories = [c for c in categories if c['id'] != category_id]
    persist_data()
    return jsonify({"success": True})

# 商品管理API
@app.route('/api/menu', methods=['GET'])
def get_menu():
    category_id = request.args.get('category_id', type=int)
    if category_id:
        filtered_menu = [item for item in menu if item['category_id'] == category_id]
        return jsonify({"menu": filtered_menu})
    return jsonify({"menu": menu})

@app.route('/api/menu', methods=['POST'])
def add_menu_item():
    global next_menu_id
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    category_id = data.get('category_id')
    image = data.get('image')

    if not name:
        return jsonify({"error": "商品名称不能为空。"}), 400
    if price is None:
        return jsonify({"error": "价格不能为空。"}), 400
    if category_id is None:
        return jsonify({"error": "请选择分类。"}), 400

    try:
        price = float(price)
        category_id = int(category_id)
    except (TypeError, ValueError):
        return jsonify({"error": "请输入合法的价格和分类。"}), 400

    if not any(cat['id'] == category_id for cat in categories):
        return jsonify({"error": "选择的分类不存在。"}), 400

    item = {
        "id": next_menu_id,
        "name": name,
        "description": description,
        "price": round(price, 2),
        "category_id": category_id,
        "image": image
    }
    menu.append(item)
    next_menu_id += 1
    persist_data()
    return jsonify({"item": item}), 201

@app.route('/api/menu/<int:item_id>', methods=['PUT'])
def update_menu_item(item_id):
    data = request.get_json() or {}
    item = next((m for m in menu if m['id'] == item_id), None)
    if not item:
        return jsonify({"error": "未找到该商品。"}), 404

    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    category_id = data.get('category_id')
    image = data.get('image')

    if not name:
        return jsonify({"error": "商品名称不能为空。"}), 400
    if price is None:
        return jsonify({"error": "价格不能为空。"}), 400
    if category_id is None:
        return jsonify({"error": "请选择分类。"}), 400

    try:
        price = float(price)
        category_id = int(category_id)
    except (TypeError, ValueError):
        return jsonify({"error": "请输入合法的价格和分类。"}), 400

    if not any(cat['id'] == category_id for cat in categories):
        return jsonify({"error": "选择的分类不存在。"}), 400

    item['name'] = name
    item['description'] = description
    item['price'] = round(price, 2)
    item['category_id'] = category_id
    if image:
        item['image'] = image
    item['price'] = round(price, 2)
    item['category_id'] = category_id
    persist_data()
    return jsonify({"item": item})

@app.route('/api/menu/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    global menu
    item = next((m for m in menu if m['id'] == item_id), None)
    if not item:
        return jsonify({"error": "未找到该商品。"}), 404
    menu = [m for m in menu if m['id'] != item_id]
    persist_data()
    return jsonify({"success": True})

# 套餐管理API
@app.route('/api/combos', methods=['GET'])
def get_combos():
    return jsonify({"combos": combos})

@app.route('/api/combos', methods=['POST'])
def add_combo():
    global next_combo_id
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    items = data.get('items', [])
    discount = data.get('discount', 1.0)

    if not name:
        return jsonify({"error": "套餐名称不能为空。"}), 400
    if price is None:
        return jsonify({"error": "价格不能为空。"}), 400
    if not items:
        return jsonify({"error": "请选择套餐商品。"}), 400

    try:
        price = float(price)
        discount = float(discount)
        items = [int(item) for item in items]
    except (TypeError, ValueError):
        return jsonify({"error": "请输入合法的价格和商品ID。"}), 400

    # 验证商品存在
    for item_id in items:
        if not any(m['id'] == item_id for m in menu):
            return jsonify({"error": f"商品ID {item_id} 不存在。"}), 400

    combo = {
        "id": next_combo_id,
        "name": name,
        "description": description,
        "price": round(price, 2),
        "items": items,
        "discount": discount
    }
    combos.append(combo)
    next_combo_id += 1
    persist_data()
    return jsonify({"combo": combo}), 201

@app.route('/api/combos/<int:combo_id>', methods=['PUT'])
def update_combo(combo_id):
    data = request.get_json() or {}
    combo = next((c for c in combos if c['id'] == combo_id), None)
    if not combo:
        return jsonify({"error": "未找到该套餐。"}), 404

    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    items = data.get('items', [])
    discount = data.get('discount', 1.0)

    if not name:
        return jsonify({"error": "套餐名称不能为空。"}), 400
    if price is None:
        return jsonify({"error": "价格不能为空。"}), 400
    if not items:
        return jsonify({"error": "请选择套餐商品。"}), 400

    try:
        price = float(price)
        discount = float(discount)
        items = [int(item) for item in items]
    except (TypeError, ValueError):
        return jsonify({"error": "请输入合法的价格和商品ID。"}), 400

    # 验证商品存在
    for item_id in items:
        if not any(m['id'] == item_id for m in menu):
            return jsonify({"error": f"商品ID {item_id} 不存在。"}), 400

    combo['name'] = name
    combo['description'] = description
    combo['price'] = round(price, 2)
    combo['items'] = items
    combo['discount'] = discount
    persist_data()
    return jsonify({"combo": combo})

@app.route('/api/combos/<int:combo_id>', methods=['DELETE'])
def delete_combo(combo_id):
    global combos
    combo = next((c for c in combos if c['id'] == combo_id), None)
    if not combo:
        return jsonify({"error": "未找到该套餐。"}), 404
    combos = [c for c in combos if c['id'] != combo_id]
    persist_data()
    return jsonify({"success": True})

# 工作台统计API
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    total_orders = len(orders)
    total_revenue = sum(order['total'] for order in orders if order['status'] == '已完成')
    pending_orders = len([o for o in orders if o['status'] == '已接单'])
    completed_orders = len([o for o in orders if o['status'] == '已完成'])
    cancelled_orders = len([o for o in orders if o['status'] == '已取消'])

    # 今日统计
    today = datetime.now().date()
    today_orders = [o for o in orders if datetime.strptime(o['created_at'], "%Y-%m-%d %H:%M:%S").date() == today]
    today_revenue = sum(o['total'] for o in today_orders if o['status'] == '已完成')

    return jsonify({
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "today_orders": len(today_orders),
        "today_revenue": round(today_revenue, 2),
        "menu_count": len(menu),
        "combo_count": len(combo)
    })

# 订单管理API
@app.route('/api/orders', methods=['GET'])
def get_orders():
    customer = request.args.get('customer', '').strip()
    if customer:
        filtered_orders = [o for o in orders if o['customer'] == customer]
        return jsonify({"orders": filtered_orders})
    return jsonify({"orders": orders})

@app.route('/api/order', methods=['POST'])
def create_order():
    global next_order_id
    data = request.get_json() or {}
    customer = data.get('customer', '').strip()
    items = data.get('items', [])
    combo_id = data.get('combo_id')

    if not customer:
        return jsonify({"error": "请输入姓名。"}), 400
    if not items and not combo_id:
        return jsonify({"error": "请选择至少一个商品或套餐。"}), 400

    order_items = []
    total = 0.0

    # 处理普通商品
    for item in items:
        menu_item = next((m for m in menu if m['id'] == item.get('id')), None)
        if not menu_item:
            continue
        quantity = max(1, int(item.get('quantity', 1)))
        subtotal = menu_item['price'] * quantity
        order_items.append({
            "id": menu_item['id'],
            "name": menu_item['name'],
            "price": menu_item['price'],
            "quantity": quantity,
            "subtotal": round(subtotal, 2),
            "type": "item"
        })
        total += subtotal

    # 处理套餐
    if combo_id:
        combo = next((c for c in combos if c['id'] == combo_id), None)
        if combo:
            combo_total = combo['price'] * combo['discount']
            order_items.append({
                "id": combo['id'],
                "name": combo['name'],
                "price": combo['price'],
                "quantity": 1,
                "subtotal": round(combo_total, 2),
                "type": "combo",
                "discount": combo['discount']
            })
            total += combo_total

    if not order_items:
        return jsonify({"error": "订单中没有有效商品。"}), 400

    order = {
        "id": next_order_id,
        "customer": customer,
        "items": order_items,
        "total": round(total, 2),
        "status": "已接单",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    orders.append(order)
    next_order_id += 1
    persist_data()

    return jsonify({"order": order}), 201

@app.route('/api/order/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    order = next((o for o in orders if o['id'] == order_id), None)
    if not order:
        return jsonify({"error": "未找到该订单。"}), 404
    if order['status'] == '已取消':
        return jsonify({"error": "订单已取消。"}), 400
    if order['status'] == '已完成':
        return jsonify({"error": "订单已完成，无法取消。"}), 400

    order['status'] = '已取消'
    persist_data()
    return jsonify({"order": order})

@app.route('/api/order/<int:order_id>/complete', methods=['POST'])
def complete_order(order_id):
    order = next((o for o in orders if o['id'] == order_id), None)
    if not order:
        return jsonify({"error": "未找到该订单。"}), 404
    if order['status'] != '已接单':
        return jsonify({"error": "该订单无法标记为已完成。"}), 400

    order['status'] = '已完成'
    persist_data()
    return jsonify({"order": order})

# 用户管理
users = []
next_user_id = 1
user_sessions = {}  # 简单的 session 管理

@app.route('/api/users/register', methods=['POST'])
def register_user():
    global next_user_id
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    phone = data.get('phone', '').strip()

    if not username:
        return jsonify({"error": "用户名不能为空。"}), 400
    if not password:
        return jsonify({"error": "密码不能为空。"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少6个字符。"}), 400

    # 检查用户名是否已存在
    if any(u['username'] == username for u in users):
        return jsonify({"error": "用户名已存在。"}), 400

    user = {
        "id": next_user_id,
        "username": username,
        "password": password,
        "phone": phone,
        "addresses": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    users.append(user)
    next_user_id += 1
    persist_data()

    # 创建 session
    session_id = f"session_{user['id']}_{datetime.now().timestamp()}"
    user_sessions[session_id] = user['id']

    return jsonify({
        "user": {
            "id": user['id'],
            "username": user['username'],
            "phone": user['phone'],
            "addresses": user['addresses']
        },
        "session_id": session_id
    }), 201

@app.route('/api/users/login', methods=['POST'])
def login_user():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空。"}), 400

    user = next((u for u in users if u['username'] == username and u['password'] == password), None)
    if not user:
        return jsonify({"error": "用户名或密码错误。"}), 401

    # 创建 session
    session_id = f"session_{user['id']}_{datetime.now().timestamp()}"
    user_sessions[session_id] = user['id']

    return jsonify({
        "user": {
            "id": user['id'],
            "username": user['username'],
            "phone": user['phone'],
            "addresses": user['addresses']
        },
        "session_id": session_id
    }), 200

@app.route('/api/users/logout', methods=['POST'])
def logout_user():
    data = request.get_json() or {}
    session_id = data.get('session_id')

    if session_id and session_id in user_sessions:
        del user_sessions[session_id]

    return jsonify({"success": True})

@app.route('/api/users/session', methods=['GET'])
def get_user_session():
    session_id = request.headers.get('X-Session-ID')
    
    if not session_id or session_id not in user_sessions:
        return jsonify({"error": "未登录。"}), 401

    user_id = user_sessions[session_id]
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        return jsonify({"error": "用户不存在。"}), 404

    return jsonify({
        "user": {
            "id": user['id'],
            "username": user['username'],
            "phone": user['phone'],
            "addresses": user['addresses']
        },
        "session_id": session_id
    }), 200

# 地址管理
@app.route('/api/addresses', methods=['GET'])
def get_addresses():
    session_id = request.headers.get('X-Session-ID')
    
    if not session_id or session_id not in user_sessions:
        return jsonify({"error": "未登录。"}), 401

    user_id = user_sessions[session_id]
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        return jsonify({"error": "用户不存在。"}), 404

    return jsonify({"addresses": user['addresses']}), 200

@app.route('/api/addresses', methods=['POST'])
def add_address():
    session_id = request.headers.get('X-Session-ID')
    
    if not session_id or session_id not in user_sessions:
        return jsonify({"error": "未登录。"}), 401

    user_id = user_sessions[session_id]
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        return jsonify({"error": "用户不存在。"}), 404

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    address = data.get('address', '').strip()
    phone = data.get('phone', '').strip()
    is_default = data.get('is_default', False)

    if not name:
        return jsonify({"error": "收货人名称不能为空。"}), 400
    if not address:
        return jsonify({"error": "地址不能为空。"}), 400
    if not phone:
        return jsonify({"error": "电话不能为空。"}), 400

    # 如果设为默认，取消其他默认地址
    if is_default:
        for addr in user['addresses']:
            addr['is_default'] = False

    next_address_id = max((addr['id'] for addr in user['addresses']), default=0) + 1
    new_address = {
        "id": next_address_id,
        "name": name,
        "address": address,
        "phone": phone,
        "is_default": is_default,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    user['addresses'].append(new_address)
    persist_data()

    return jsonify({"address": new_address}), 201

@app.route('/api/addresses/<int:address_id>', methods=['PUT'])
def update_address(address_id):
    session_id = request.headers.get('X-Session-ID')
    
    if not session_id or session_id not in user_sessions:
        return jsonify({"error": "未登录。"}), 401

    user_id = user_sessions[session_id]
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        return jsonify({"error": "用户不存在。"}), 404

    address = next((a for a in user['addresses'] if a['id'] == address_id), None)
    if not address:
        return jsonify({"error": "地址不存在。"}), 404

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    addr = data.get('address', '').strip()
    phone = data.get('phone', '').strip()
    is_default = data.get('is_default', address['is_default'])

    if not name:
        return jsonify({"error": "收货人名称不能为空。"}), 400
    if not addr:
        return jsonify({"error": "地址不能为空。"}), 400
    if not phone:
        return jsonify({"error": "电话不能为空。"}), 400

    # 如果设为默认，取消其他默认地址
    if is_default and not address['is_default']:
        for a in user['addresses']:
            a['is_default'] = False

    address['name'] = name
    address['address'] = addr
    address['phone'] = phone
    address['is_default'] = is_default
    persist_data()

    return jsonify({"address": address}), 200

@app.route('/api/addresses/<int:address_id>', methods=['DELETE'])
def delete_address(address_id):
    session_id = request.headers.get('X-Session-ID')
    
    if not session_id or session_id not in user_sessions:
        return jsonify({"error": "未登录。"}), 401

    user_id = user_sessions[session_id]
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        return jsonify({"error": "用户不存在。"}), 404

    address = next((a for a in user['addresses'] if a['id'] == address_id), None)
    if not address:
        return jsonify({"error": "地址不存在。"}), 404

    user['addresses'] = [a for a in user['addresses'] if a['id'] != address_id]
    persist_data()

    return jsonify({"success": True}), 200

# AI 客服对话（代理远程模型 HTTP API）
def build_ai_payload(message, image_url=None, history=None, include_model=True):
    messages = [{"role": "system", "content": REMOTE_AI_SYSTEM_PROMPT}]

    # 可选历史上下文（前端可传 role/content 结构）
    if isinstance(history, list):
        for msg in history:
            role = (msg or {}).get("role")
            content = (msg or {}).get("content")
            if role in ("user", "assistant", "system") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content.strip()})

    if image_url:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": message},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        })
    else:
        messages.append({"role": "user", "content": message})

    payload = {
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
        "max_tokens": REMOTE_AI_MAX_TOKENS,
        "max_new_tokens": REMOTE_AI_MAX_TOKENS
    }
    if include_model and REMOTE_AI_MODEL:
        payload["model"] = REMOTE_AI_MODEL
    return payload

def build_prompt_payload(message, image_url=None, history=None, include_model=True):
    """兼容仅支持 prompt 字段的推理服务"""
    prompt_parts = []
    if isinstance(history, list):
        for msg in history:
            role = (msg or {}).get("role", "user")
            content = (msg or {}).get("content", "")
            if isinstance(content, str) and content.strip():
                prompt_parts.append(f"{role}: {content.strip()}")

    prompt_parts.append(f"user: {message}")
    if image_url:
        prompt_parts.append(f"image_url: {image_url}")
    prompt_parts.append("assistant:")
    prompt_text = "\n".join(prompt_parts)

    payload = {"prompt": prompt_text}
    payload["max_tokens"] = REMOTE_AI_MAX_TOKENS
    payload["max_new_tokens"] = REMOTE_AI_MAX_TOKENS
    if include_model and REMOTE_AI_MODEL:
        payload["model"] = REMOTE_AI_MODEL
    return payload

def build_prompt_payload_variants(message, image_url=None, history=None, include_model=True):
    """不同服务对 prompt 协议字段要求不同，按常见组合自动重试"""
    base_payload = build_prompt_payload(
        message,
        image_url=image_url,
        history=history,
        include_model=include_model
    )

    variants = []
    def add_variant(v):
        if v not in variants:
            variants.append(v)

    # 1) 极简 prompt（很多 FastAPI 封装只接受这个）
    add_variant(dict(base_payload))

    # 2) 常见推理参数
    with_sampling = dict(base_payload)
    with_sampling["temperature"] = 0.7
    with_sampling["stream"] = False
    add_variant(with_sampling)

    # 3) 补充 max_tokens（部分服务要求）
    with_tokens = dict(base_payload)
    with_tokens["max_tokens"] = max(REMOTE_AI_MAX_TOKENS, 1024)
    with_tokens["max_new_tokens"] = max(REMOTE_AI_MAX_TOKENS, 1024)
    add_variant(with_tokens)

    return variants

def is_model_not_found_error(error_text):
    lower = (error_text or "").lower()
    return "model" in lower and ("does not exist" in lower or "not found" in lower)

def sanitize_ai_answer(text):
    if not isinstance(text, str):
        return text

    cleaned = text

    # 去掉常见思考标签块
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)

    # 如果包含“最终回答/回答”，优先截取该段后的内容
    final_markers = [
        "最终回答：", "最终回答:", "最终答案：", "最终答案:",
        "回答：", "回答:"
    ]
    for marker in final_markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[1]
            break

    # 清理“思考过程”标题行
    cleaned = re.sub(r"^\s*(思考过程|推理过程|分析过程)\s*[:：]\s*$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

    # 规范空行
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or text.strip()

def extract_ai_text(response_json):
    if not isinstance(response_json, dict):
        return None

    # OpenAI 风格: {"choices":[{"message":{"content":"..."}}]}
    choices = response_json.get("choices")
    if isinstance(choices, list) and choices:
        message = (choices[0] or {}).get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return sanitize_ai_answer(content.strip())
        if isinstance(content, list):
            text_parts = []
            for part in content:
                text = (part or {}).get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
            if text_parts:
                return sanitize_ai_answer("\n".join(text_parts))

    # 兼容一些常见自定义字段
    for key in ("response", "answer", "text", "output_text", "content"):
        value = response_json.get(key)
        if isinstance(value, str) and value.strip():
            return sanitize_ai_answer(value.strip())

    return None

def call_remote_ai_api(message, image_url=None, history=None):
    global ACTIVE_REMOTE_AI_API_URL, USE_MODEL_FIELD

    if not REMOTE_AI_API_URL:
        return None, "REMOTE_AI_API_URL 未配置。"

    headers = {"Content-Type": "application/json"}
    if REMOTE_AI_API_KEY:
        headers["Authorization"] = f"Bearer {REMOTE_AI_API_KEY}"

    payload = build_ai_payload(message, image_url=image_url, history=history, include_model=USE_MODEL_FIELD)
    payload_without_model = build_ai_payload(message, image_url=image_url, history=history, include_model=False)
    prompt_payload_variants = build_prompt_payload_variants(
        message,
        image_url=image_url,
        history=history,
        include_model=USE_MODEL_FIELD
    )
    prompt_payload_variants_without_model = build_prompt_payload_variants(
        message,
        image_url=image_url,
        history=history,
        include_model=False
    )

    candidate_urls = build_remote_ai_candidate_urls(ACTIVE_REMOTE_AI_API_URL or REMOTE_AI_API_URL)
    last_error = "远程AI服务调用失败。"

    try:
        for api_url in candidate_urls:
            resp = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=(REMOTE_AI_CONNECT_TIMEOUT, REMOTE_AI_TIMEOUT)
            )

            if resp.status_code == 404:
                last_error = f"远程AI服务调用失败，状态码 404，路径不存在: {api_url}"
                continue

            if not resp.ok:
                raw_error_text = (resp.text or "")
                # 部分单模型服务不接受 model 字段，自动去掉 model 重试
                if resp.status_code in (400, 404) and is_model_not_found_error(raw_error_text):
                    no_model_resp = requests.post(
                        api_url,
                        headers=headers,
                        json=payload_without_model,
                        timeout=(REMOTE_AI_CONNECT_TIMEOUT, REMOTE_AI_TIMEOUT)
                    )
                    if no_model_resp.ok:
                        no_model_body = no_model_resp.json()
                        no_model_text = extract_ai_text(no_model_body)
                        if no_model_text:
                            if USE_MODEL_FIELD:
                                USE_MODEL_FIELD = False
                                print("AI代理检测到模型名不可用，后续请求将不再携带 model 字段。")
                            if ACTIVE_REMOTE_AI_API_URL != api_url:
                                ACTIVE_REMOTE_AI_API_URL = api_url
                                print(f"AI代理已命中可用接口(不带model字段): {ACTIVE_REMOTE_AI_API_URL}")
                            return no_model_text, None
                        return None, "远程AI(不带model字段)返回格式无法识别。"

                # 部分服务只接受 prompt 字段，自动降级重试
                if resp.status_code == 400:
                    try:
                        err_json = resp.json()
                    except ValueError:
                        err_json = None

                    err_text = json.dumps(err_json, ensure_ascii=False) if isinstance(err_json, dict) else (resp.text or "")
                    if "prompt" in err_text and ("Field required" in err_text or "missing" in err_text):
                        prompt_last_error = ""
                        for idx, prompt_payload in enumerate(prompt_payload_variants, start=1):
                            prompt_resp = requests.post(
                                api_url,
                                headers=headers,
                                json=prompt_payload,
                                timeout=(REMOTE_AI_CONNECT_TIMEOUT, REMOTE_AI_TIMEOUT)
                            )
                            if prompt_resp.ok:
                                prompt_body = prompt_resp.json()
                                prompt_text = extract_ai_text(prompt_body)
                                if prompt_text:
                                    if ACTIVE_REMOTE_AI_API_URL != api_url:
                                        ACTIVE_REMOTE_AI_API_URL = api_url
                                        print(f"AI代理已命中可用接口(prompt协议): {ACTIVE_REMOTE_AI_API_URL}")
                                    return prompt_text, None
                                return None, "远程AI(prompt协议)返回格式无法识别。"

                            prompt_preview = (prompt_resp.text or "").strip().replace("\n", " ")
                            prompt_preview = prompt_preview[:220] if prompt_preview else ""
                            prompt_last_error = (
                                f"prompt协议重试失败(变体{idx})，状态码 {prompt_resp.status_code}"
                                + (f"，响应: {prompt_preview}" if prompt_preview else "")
                            )

                            # prompt 协议也可能不接受 model 字段
                            if prompt_resp.status_code in (400, 404) and is_model_not_found_error(prompt_resp.text or ""):
                                for jdx, prompt_payload_no_model in enumerate(prompt_payload_variants_without_model, start=1):
                                    prompt_no_model_resp = requests.post(
                                        api_url,
                                        headers=headers,
                                        json=prompt_payload_no_model,
                                        timeout=(REMOTE_AI_CONNECT_TIMEOUT, REMOTE_AI_TIMEOUT)
                                    )
                                    if prompt_no_model_resp.ok:
                                        prompt_no_model_body = prompt_no_model_resp.json()
                                        prompt_no_model_text = extract_ai_text(prompt_no_model_body)
                                        if prompt_no_model_text:
                                            if USE_MODEL_FIELD:
                                                USE_MODEL_FIELD = False
                                                print("AI代理检测到模型名不可用，后续请求将不再携带 model 字段。")
                                            if ACTIVE_REMOTE_AI_API_URL != api_url:
                                                ACTIVE_REMOTE_AI_API_URL = api_url
                                                print(f"AI代理已命中可用接口(prompt+不带model): {ACTIVE_REMOTE_AI_API_URL}")
                                            return prompt_no_model_text, None
                                        return None, "远程AI(prompt+不带model)返回格式无法识别。"

                                    prompt_no_model_preview = (prompt_no_model_resp.text or "").strip().replace("\n", " ")
                                    prompt_no_model_preview = prompt_no_model_preview[:220] if prompt_no_model_preview else ""
                                    prompt_last_error = (
                                        f"prompt协议(不带model)重试失败(变体{jdx})，状态码 {prompt_no_model_resp.status_code}"
                                        + (f"，响应: {prompt_no_model_preview}" if prompt_no_model_preview else "")
                                    )

                        if prompt_last_error:
                            return None, prompt_last_error

                text_preview = (resp.text or "").strip().replace("\n", " ")
                text_preview = text_preview[:180] if text_preview else ""
                if text_preview:
                    return None, f"远程AI服务调用失败，状态码 {resp.status_code}，响应: {text_preview}"
                return None, f"远程AI服务调用失败，状态码 {resp.status_code}"

            body = resp.json()
            text = extract_ai_text(body)
            if not text:
                return None, "远程AI返回格式无法识别，请检查模型服务响应格式。"

            if ACTIVE_REMOTE_AI_API_URL != api_url:
                ACTIVE_REMOTE_AI_API_URL = api_url
                print(f"AI代理已命中可用接口: {ACTIVE_REMOTE_AI_API_URL}")
            return text, None

        return None, last_error
    except requests.Timeout:
        return None, f"远程AI服务超时（读取超时 {REMOTE_AI_TIMEOUT:.0f}s），请稍后重试。"
    except requests.RequestException as e:
        return None, f"远程AI服务请求异常: {e}"
    except ValueError:
        return None, "远程AI返回的不是合法JSON。"

def generate_mock_response(message):
    """模拟AI回复（当远程AI不可用时使用）"""
    message_lower = message.lower()
    
    if "菜单" in message_lower or "菜" in message_lower:
        return "您好！我们有各种美味的菜品，包括主菜、面食、饮品和套餐。您可以在菜单页面浏览所有商品。"
    elif "订单" in message_lower:
        return "关于订单问题，您可以在订单查询页面查看订单状态，或联系客服热线400-123-4567。"
    elif "配送" in message_lower or "送餐" in message_lower:
        return "我们的配送时间通常在30-60分钟，具体时间根据距离和订单量而定。您可以在订单详情中查看预计送达时间。"
    elif "退款" in message_lower or "取消" in message_lower:
        return "如果需要取消订单或申请退款，请在订单页面操作，或联系我们的客服团队。"
    elif "地址" in message_lower:
        return "您可以在个人中心管理收货地址，确保配送信息准确无误。"
    else:
        return "您好！我是智能外卖平台的AI助手。如有任何问题，请详细描述，我会尽力帮助您！"

@app.route('/api/ai-agent', methods=['POST'])
@app.route('/api/chat', methods=['POST'])  # 兼容旧前端
def ai_agent():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    image_url = data.get('image_url')
    history = data.get('history')
    conversation_id = (data.get('conversation_id') or '').strip()
    reset_context = bool(data.get('reset_context', False))
    session_id = request.headers.get('X-Session-ID') or (data.get('session_id') or '').strip()

    if not message and not image_url:
        return jsonify({"error": "消息不能为空。"}), 400

    if not message:
        message = "请识别这张图片并给出外卖相关建议。"

    if not conversation_id:
        conversation_id = generate_conversation_id()

    if reset_context:
        ai_conversation_store.pop(conversation_id, None)

    stored_history = ai_conversation_store.get(conversation_id, [])
    business_context = build_business_context_text(session_id=session_id)
    effective_history = [{"role": "system", "content": business_context}]

    # 客户端显式 history 优先，其次用服务端缓存 history
    if isinstance(history, list) and history:
        effective_history.extend(trim_conversation_history(history))
    else:
        effective_history.extend(trim_conversation_history(stored_history))

    response_text, err = call_remote_ai_api(message, image_url=image_url, history=effective_history)
    if response_text:
        final_response = response_text

        # 自动续写：当回答疑似被截断时，补 1~N 轮续写
        if REMOTE_AI_CONTINUE_ROUNDS > 0 and looks_like_truncated_answer(final_response):
            base_history = list(effective_history)
            continuation_prompt = "请紧接上一条回答继续完成，不要重复前文，不要输出思考过程。"

            for _ in range(REMOTE_AI_CONTINUE_ROUNDS):
                continuation_history = list(base_history)
                continuation_history.append({"role": "user", "content": message})
                continuation_history.append({"role": "assistant", "content": final_response})

                next_chunk, next_err = call_remote_ai_api(
                    continuation_prompt,
                    image_url=None,
                    history=continuation_history
                )
                if not next_chunk:
                    if next_err:
                        print(f"AI续写失败: {next_err}")
                    break

                final_response = sanitize_ai_answer(merge_ai_chunks(final_response, next_chunk))
                if not looks_like_truncated_answer(final_response):
                    break

        stored_history.append({"role": "user", "content": message})
        stored_history.append({"role": "assistant", "content": final_response})
        ai_conversation_store[conversation_id] = trim_conversation_history(stored_history)

        return jsonify({
            "response": final_response,
            "source": "remote_api",
            "conversation_id": conversation_id
        }), 200

    # 失败时回退到模拟回复，保证页面可用
    print(f"AI代理回退到模拟回复: {err}")
    fallback = generate_mock_response(message)
    stored_history.append({"role": "user", "content": message})
    stored_history.append({"role": "assistant", "content": fallback})
    ai_conversation_store[conversation_id] = trim_conversation_history(stored_history)
    return jsonify({
        "response": fallback,
        "source": "mock",
        "warning": err or "远程AI服务不可用，已回退模拟回复。",
        "conversation_id": conversation_id
    }), 200

if __name__ == '__main__':
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    else:
        port = int(os.environ.get('PORT', port))

    app.run(debug=True, host='0.0.0.0', port=port)
