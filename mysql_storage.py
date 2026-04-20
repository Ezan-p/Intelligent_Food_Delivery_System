import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pymysql
from pymysql.cursors import DictCursor

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            os.environ.setdefault(key, value)


_load_env_file()
if load_dotenv is not None:
    load_dotenv(override=False)

MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', '3306'))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'intelligent_food_delivery')
MYSQL_CHARSET = os.environ.get('MYSQL_CHARSET', 'utf8mb4')

TABLE_CREATION_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT PRIMARY KEY,
        username VARCHAR(64) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        phone VARCHAR(32) NOT NULL DEFAULT '',
        role VARCHAR(16) NOT NULL,
        account_status VARCHAR(16) NOT NULL DEFAULT 'active',
        risk_status VARCHAR(16) NOT NULL DEFAULT 'normal',
        admin_note TEXT,
        store_id INT NULL,
        store_name VARCHAR(255) NOT NULL DEFAULT '',
        store_description TEXT,
        created_at VARCHAR(32) NOT NULL DEFAULT ''
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_addresses (
        user_id INT NOT NULL,
        address_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        address TEXT NOT NULL,
        phone VARCHAR(32) NOT NULL,
        is_default TINYINT(1) NOT NULL DEFAULT 0,
        created_at VARCHAR(32) NOT NULL DEFAULT '',
        PRIMARY KEY (user_id, address_id),
        KEY idx_user_addresses_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_favorite_stores (
        user_id INT NOT NULL,
        store_id INT NOT NULL,
        PRIMARY KEY (user_id, store_id),
        KEY idx_user_favorite_stores_store_id (store_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_favorite_menu (
        user_id INT NOT NULL,
        item_id INT NOT NULL,
        PRIMARY KEY (user_id, item_id),
        KEY idx_user_favorite_menu_item_id (item_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_recent_views (
        user_id INT NOT NULL,
        seq_no INT NOT NULL,
        view_type VARCHAR(16) NOT NULL,
        store_id INT NULL,
        item_id INT NULL,
        viewed_at VARCHAR(32) NOT NULL DEFAULT '',
        PRIMARY KEY (user_id, seq_no),
        KEY idx_user_recent_views_store_id (store_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS stores (
        id INT PRIMARY KEY,
        owner_user_id INT NULL,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        status VARCHAR(16) NOT NULL DEFAULT 'active',
        avatar_url LONGTEXT,
        cover_image_url LONGTEXT,
        business_status VARCHAR(32) NOT NULL DEFAULT '营业中',
        business_hours VARCHAR(64) NOT NULL DEFAULT '09:00-22:00',
        rating DECIMAL(3,1) NOT NULL DEFAULT 4.8,
        delivery_fee DECIMAL(10,2) NOT NULL DEFAULT 0,
        min_order_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
        announcement TEXT,
        created_at VARCHAR(32) NOT NULL DEFAULT '',
        KEY idx_stores_owner_user_id (owner_user_id),
        KEY idx_stores_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS categories (
        id INT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        store_id INT NOT NULL,
        status VARCHAR(16) NOT NULL DEFAULT 'active',
        KEY idx_categories_store_id (store_id),
        KEY idx_categories_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS menu_items (
        id INT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        price DECIMAL(10,2) NOT NULL,
        category_id INT NOT NULL,
        store_id INT NOT NULL,
        image LONGTEXT,
        status VARCHAR(16) NOT NULL DEFAULT 'active',
        KEY idx_menu_items_store_id (store_id),
        KEY idx_menu_items_category_id (category_id),
        KEY idx_menu_items_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS combos (
        id INT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        price DECIMAL(10,2) NOT NULL,
        discount DECIMAL(10,2) NOT NULL DEFAULT 1.0,
        store_id INT NOT NULL,
        status VARCHAR(16) NOT NULL DEFAULT 'active',
        KEY idx_combos_store_id (store_id),
        KEY idx_combos_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS combo_items (
        combo_id INT NOT NULL,
        item_id INT NOT NULL,
        seq_no INT NOT NULL,
        PRIMARY KEY (combo_id, item_id, seq_no),
        KEY idx_combo_items_item_id (item_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INT PRIMARY KEY,
        customer VARCHAR(64) NOT NULL,
        store_id INT NOT NULL,
        store_name VARCHAR(255) NOT NULL DEFAULT '',
        total DECIMAL(10,2) NOT NULL,
        status VARCHAR(16) NOT NULL,
        created_at VARCHAR(32) NOT NULL DEFAULT '',
        source_order_id INT NULL,
        KEY idx_orders_customer (customer),
        KEY idx_orders_store_id (store_id),
        KEY idx_orders_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
        order_id INT NOT NULL,
        seq_no INT NOT NULL,
        item_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        subtotal DECIMAL(10,2) NOT NULL,
        item_type VARCHAR(16) NOT NULL DEFAULT 'item',
        discount DECIMAL(10,2) NULL,
        PRIMARY KEY (order_id, seq_no),
        KEY idx_order_items_item_id (item_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS reviews (
        id INT PRIMARY KEY,
        order_id INT NOT NULL,
        customer VARCHAR(64) NOT NULL,
        store_id INT NOT NULL,
        store_name VARCHAR(255) NOT NULL DEFAULT '',
        rating DECIMAL(3,1) NOT NULL,
        delivery_rating DECIMAL(3,1) NOT NULL DEFAULT 0,
        packaging_rating DECIMAL(3,1) NOT NULL DEFAULT 0,
        taste_rating DECIMAL(3,1) NOT NULL DEFAULT 0,
        content TEXT,
        image LONGTEXT,
        created_at VARCHAR(32) NOT NULL DEFAULT '',
        KEY idx_reviews_order_id (order_id),
        KEY idx_reviews_store_id (store_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS counters (
        counter_key VARCHAR(64) PRIMARY KEY,
        counter_value INT NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS app_meta (
        meta_key VARCHAR(64) PRIMARY KEY,
        meta_value TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """
]

RESET_TABLES = [
    'user_recent_views',
    'user_favorite_menu',
    'user_favorite_stores',
    'user_addresses',
    'order_items',
    'orders',
    'combo_items',
    'combos',
    'menu_items',
    'categories',
    'reviews',
    'stores',
    'users',
    'counters'
]


def deep_copy_data(data: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(data)


def _server_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset=MYSQL_CHARSET,
        autocommit=True,
        cursorclass=DictCursor,
    )


def get_connection(autocommit: bool = False):
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset=MYSQL_CHARSET,
        autocommit=autocommit,
        cursorclass=DictCursor,
    )


def ensure_database_exists():
    connection = _server_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET {MYSQL_CHARSET} COLLATE utf8mb4_unicode_ci"
            )
    finally:
        connection.close()


def create_tables():
    connection = get_connection(autocommit=True)
    try:
        with connection.cursor() as cursor:
            for statement in TABLE_CREATION_SQL:
                cursor.execute(statement)
    finally:
        connection.close()


def _load_legacy_json(legacy_json_path: str, default_data: Dict[str, Any]) -> Dict[str, Any]:
    if legacy_json_path and os.path.exists(legacy_json_path):
        with open(legacy_json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return deep_copy_data(default_data)


def _database_has_seed_data() -> bool:
    connection = get_connection(autocommit=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM users")
            user_count = int(cursor.fetchone()['count'])
            cursor.execute("SELECT COUNT(*) AS count FROM stores")
            store_count = int(cursor.fetchone()['count'])
            return user_count > 0 or store_count > 0
    finally:
        connection.close()


def init_mysql_database(default_data: Dict[str, Any], legacy_json_path: str = None):
    ensure_database_exists()
    create_tables()
    if _database_has_seed_data():
        return
    seed_data = _load_legacy_json(legacy_json_path, default_data)
    save_data(seed_data)


def _fetch_all(cursor, sql: str, params=None) -> List[Dict[str, Any]]:
    cursor.execute(sql, params or ())
    return list(cursor.fetchall())


def load_data(default_data: Dict[str, Any]) -> Dict[str, Any]:
    data = {
        'stores': [],
        'categories': [],
        'menu': [],
        'combos': [],
        'orders': [],
        'reviews': [],
        'users': [],
        'counters': {}
    }
    try:
        connection = get_connection(autocommit=True)
    except Exception:
        return deep_copy_data(default_data)

    try:
        with connection.cursor() as cursor:
            data['stores'] = _fetch_all(cursor, "SELECT * FROM stores ORDER BY id")
            data['categories'] = _fetch_all(cursor, "SELECT * FROM categories ORDER BY id")
            data['menu'] = _fetch_all(cursor, "SELECT id, name, description, price + 0 AS price, category_id, store_id, image, status FROM menu_items ORDER BY id")

            combo_rows = _fetch_all(cursor, "SELECT id, name, description, price + 0 AS price, discount + 0 AS discount, store_id, status FROM combos ORDER BY id")
            combo_item_rows = _fetch_all(cursor, "SELECT combo_id, item_id, seq_no FROM combo_items ORDER BY combo_id, seq_no")
            combo_items_map = {}
            for row in combo_item_rows:
                combo_items_map.setdefault(row['combo_id'], []).append(row['item_id'])
            for combo in combo_rows:
                combo['items'] = combo_items_map.get(combo['id'], [])
            data['combos'] = combo_rows

            order_rows = _fetch_all(cursor, "SELECT id, customer, store_id, store_name, total + 0 AS total, status, created_at, source_order_id FROM orders ORDER BY id")
            order_item_rows = _fetch_all(cursor, "SELECT order_id, seq_no, item_id, name, price + 0 AS price, quantity, subtotal + 0 AS subtotal, item_type, discount + 0 AS discount FROM order_items ORDER BY order_id, seq_no")
            order_items_map = {}
            for row in order_item_rows:
                item = {
                    'id': row['item_id'],
                    'name': row['name'],
                    'price': float(row['price']),
                    'quantity': int(row['quantity']),
                    'subtotal': float(row['subtotal']),
                    'type': row['item_type'],
                }
                if row['discount'] is not None:
                    item['discount'] = float(row['discount'])
                order_items_map.setdefault(row['order_id'], []).append(item)
            for order in order_rows:
                order['total'] = float(order['total'])
                order['items'] = order_items_map.get(order['id'], [])
            data['orders'] = order_rows

            review_rows = _fetch_all(cursor, "SELECT id, order_id, customer, store_id, store_name, rating + 0 AS rating, delivery_rating + 0 AS delivery_rating, packaging_rating + 0 AS packaging_rating, taste_rating + 0 AS taste_rating, content, image, created_at FROM reviews ORDER BY id")
            for review in review_rows:
                review['rating'] = float(review['rating'])
                review['delivery_rating'] = float(review['delivery_rating'])
                review['packaging_rating'] = float(review['packaging_rating'])
                review['taste_rating'] = float(review['taste_rating'])
            data['reviews'] = review_rows

            user_rows = _fetch_all(cursor, "SELECT * FROM users ORDER BY id")
            address_rows = _fetch_all(cursor, "SELECT user_id, address_id, name, address, phone, is_default, created_at FROM user_addresses ORDER BY user_id, address_id")
            favorite_store_rows = _fetch_all(cursor, "SELECT user_id, store_id FROM user_favorite_stores ORDER BY user_id, store_id")
            favorite_menu_rows = _fetch_all(cursor, "SELECT user_id, item_id FROM user_favorite_menu ORDER BY user_id, item_id")
            recent_view_rows = _fetch_all(cursor, "SELECT user_id, seq_no, view_type, store_id, item_id, viewed_at FROM user_recent_views ORDER BY user_id, seq_no")

            address_map = {}
            for row in address_rows:
                address_map.setdefault(row['user_id'], []).append({
                    'id': row['address_id'],
                    'name': row['name'],
                    'address': row['address'],
                    'phone': row['phone'],
                    'is_default': bool(row['is_default']),
                    'created_at': row['created_at'],
                })

            favorite_store_map = {}
            for row in favorite_store_rows:
                favorite_store_map.setdefault(row['user_id'], []).append(row['store_id'])

            favorite_menu_map = {}
            for row in favorite_menu_rows:
                favorite_menu_map.setdefault(row['user_id'], []).append(row['item_id'])

            recent_view_map = {}
            for row in recent_view_rows:
                recent_view_map.setdefault(row['user_id'], []).append({
                    'type': row['view_type'],
                    'store_id': row['store_id'],
                    'item_id': row['item_id'],
                    'viewed_at': row['viewed_at'],
                })

            for user in user_rows:
                user['addresses'] = address_map.get(user['id'], [])
                user['favorite_store_ids'] = favorite_store_map.get(user['id'], [])
                user['favorite_menu_ids'] = favorite_menu_map.get(user['id'], [])
                user['recent_views'] = recent_view_map.get(user['id'], [])
            data['users'] = user_rows

            counter_rows = _fetch_all(cursor, "SELECT counter_key, counter_value FROM counters")
            data['counters'] = {row['counter_key']: int(row['counter_value']) for row in counter_rows}
    finally:
        connection.close()

    return data


def save_data(data: Dict[str, Any]):
    connection = get_connection(autocommit=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in RESET_TABLES:
                cursor.execute(f"DELETE FROM {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            for user in data.get('users', []):
                cursor.execute(
                    """
                    INSERT INTO users (
                        id, username, password, phone, role, account_status, risk_status, admin_note,
                        store_id, store_name, store_description, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user.get('id'),
                        user.get('username', ''),
                        user.get('password', ''),
                        user.get('phone', ''),
                        user.get('role', 'customer'),
                        user.get('account_status', 'active'),
                        user.get('risk_status', 'normal'),
                        user.get('admin_note', ''),
                        user.get('store_id'),
                        user.get('store_name', ''),
                        user.get('store_description', ''),
                        user.get('created_at', ''),
                    )
                )
                for address in user.get('addresses', []):
                    cursor.execute(
                        """
                        INSERT INTO user_addresses (user_id, address_id, name, address, phone, is_default, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user.get('id'),
                            address.get('id'),
                            address.get('name', ''),
                            address.get('address', ''),
                            address.get('phone', ''),
                            1 if address.get('is_default') else 0,
                            address.get('created_at', ''),
                        )
                    )
                for store_id in user.get('favorite_store_ids', []):
                    cursor.execute(
                        "INSERT INTO user_favorite_stores (user_id, store_id) VALUES (%s, %s)",
                        (user.get('id'), store_id)
                    )
                for item_id in user.get('favorite_menu_ids', []):
                    cursor.execute(
                        "INSERT INTO user_favorite_menu (user_id, item_id) VALUES (%s, %s)",
                        (user.get('id'), item_id)
                    )
                for seq_no, view in enumerate(user.get('recent_views', []), start=1):
                    cursor.execute(
                        """
                        INSERT INTO user_recent_views (user_id, seq_no, view_type, store_id, item_id, viewed_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user.get('id'),
                            seq_no,
                            view.get('type', ''),
                            view.get('store_id'),
                            view.get('item_id'),
                            view.get('viewed_at', ''),
                        )
                    )

            for store in data.get('stores', []):
                cursor.execute(
                    """
                    INSERT INTO stores (
                        id, owner_user_id, name, description, status, avatar_url, cover_image_url,
                        business_status, business_hours, rating, delivery_fee, min_order_amount,
                        announcement, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        store.get('id'),
                        store.get('owner_user_id'),
                        store.get('name', ''),
                        store.get('description', ''),
                        store.get('status', 'active'),
                        store.get('avatar_url'),
                        store.get('cover_image_url'),
                        store.get('business_status', '营业中'),
                        store.get('business_hours', '09:00-22:00'),
                        float(store.get('rating', 0)),
                        float(store.get('delivery_fee', 0)),
                        float(store.get('min_order_amount', 0)),
                        store.get('announcement', ''),
                        store.get('created_at', ''),
                    )
                )

            for category in data.get('categories', []):
                cursor.execute(
                    "INSERT INTO categories (id, name, store_id, status) VALUES (%s, %s, %s, %s)",
                    (category.get('id'), category.get('name', ''), category.get('store_id'), category.get('status', 'active'))
                )

            for item in data.get('menu', []):
                cursor.execute(
                    """
                    INSERT INTO menu_items (id, name, description, price, category_id, store_id, image, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        item.get('id'),
                        item.get('name', ''),
                        item.get('description', ''),
                        float(item.get('price', 0)),
                        item.get('category_id'),
                        item.get('store_id'),
                        item.get('image'),
                        item.get('status', 'active'),
                    )
                )

            for combo in data.get('combos', []):
                cursor.execute(
                    """
                    INSERT INTO combos (id, name, description, price, discount, store_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        combo.get('id'),
                        combo.get('name', ''),
                        combo.get('description', ''),
                        float(combo.get('price', 0)),
                        float(combo.get('discount', 1)),
                        combo.get('store_id'),
                        combo.get('status', 'active'),
                    )
                )
                for seq_no, item_id in enumerate(combo.get('items', []), start=1):
                    cursor.execute(
                        "INSERT INTO combo_items (combo_id, item_id, seq_no) VALUES (%s, %s, %s)",
                        (combo.get('id'), item_id, seq_no)
                    )

            for order in data.get('orders', []):
                cursor.execute(
                    """
                    INSERT INTO orders (id, customer, store_id, store_name, total, status, created_at, source_order_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order.get('id'),
                        order.get('customer', ''),
                        order.get('store_id'),
                        order.get('store_name', ''),
                        float(order.get('total', 0)),
                        order.get('status', '已接单'),
                        order.get('created_at', ''),
                        order.get('source_order_id'),
                    )
                )
                for seq_no, item in enumerate(order.get('items', []), start=1):
                    cursor.execute(
                        """
                        INSERT INTO order_items (order_id, seq_no, item_id, name, price, quantity, subtotal, item_type, discount)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            order.get('id'),
                            seq_no,
                            item.get('id'),
                            item.get('name', ''),
                            float(item.get('price', 0)),
                            int(item.get('quantity', 1)),
                            float(item.get('subtotal', 0)),
                            item.get('type', 'item'),
                            float(item.get('discount')) if item.get('discount') is not None else None,
                        )
                    )

            for review in data.get('reviews', []):
                cursor.execute(
                    """
                    INSERT INTO reviews (
                        id, order_id, customer, store_id, store_name, rating, delivery_rating,
                        packaging_rating, taste_rating, content, image, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        review.get('id'),
                        review.get('order_id'),
                        review.get('customer', ''),
                        review.get('store_id'),
                        review.get('store_name', ''),
                        float(review.get('rating', 0)),
                        float(review.get('delivery_rating', 0)),
                        float(review.get('packaging_rating', 0)),
                        float(review.get('taste_rating', 0)),
                        review.get('content', ''),
                        review.get('image'),
                        review.get('created_at', ''),
                    )
                )

            for key, value in (data.get('counters') or {}).items():
                cursor.execute(
                    "INSERT INTO counters (counter_key, counter_value) VALUES (%s, %s)",
                    (key, int(value))
                )

            cursor.execute(
                "REPLACE INTO app_meta (meta_key, meta_value) VALUES ('last_synced_at', NOW())"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def reset_database(default_data: Dict[str, Any]):
    save_data(default_data)


def get_storage_summary(default_data: Dict[str, Any]) -> Dict[str, Any]:
    data = load_data(default_data)
    return {
        'database': MYSQL_DATABASE,
        'host': MYSQL_HOST,
        'port': MYSQL_PORT,
        'stores': len(data.get('stores', [])),
        'categories': len(data.get('categories', [])),
        'menu': len(data.get('menu', [])),
        'combos': len(data.get('combos', [])),
        'orders': len(data.get('orders', [])),
        'reviews': len(data.get('reviews', [])),
        'users': len(data.get('users', [])),
        'counters': data.get('counters', {}),
    }
