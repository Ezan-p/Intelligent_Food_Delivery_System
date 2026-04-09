import os
import sys
import json
from flask import Flask, jsonify, request, render_template
from datetime import datetime

app = Flask(__name__)

# 数据文件路径
DATA_DIR = 'data'
DATA_FILE = os.path.join(DATA_DIR, 'app_data.json')

# 创建 data 目录（如果不存在）
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

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
