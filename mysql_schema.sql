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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_favorite_stores (
    user_id INT NOT NULL,
    store_id INT NOT NULL,
    PRIMARY KEY (user_id, store_id),
    KEY idx_user_favorite_stores_store_id (store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_favorite_menu (
    user_id INT NOT NULL,
    item_id INT NOT NULL,
    PRIMARY KEY (user_id, item_id),
    KEY idx_user_favorite_menu_item_id (item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_recent_views (
    user_id INT NOT NULL,
    seq_no INT NOT NULL,
    view_type VARCHAR(16) NOT NULL,
    store_id INT NULL,
    item_id INT NULL,
    viewed_at VARCHAR(32) NOT NULL DEFAULT '',
    PRIMARY KEY (user_id, seq_no),
    KEY idx_user_recent_views_store_id (store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS categories (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    store_id INT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    KEY idx_categories_store_id (store_id),
    KEY idx_categories_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS combo_items (
    combo_id INT NOT NULL,
    item_id INT NOT NULL,
    seq_no INT NOT NULL,
    PRIMARY KEY (combo_id, item_id, seq_no),
    KEY idx_combo_items_item_id (item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS counters (
    counter_key VARCHAR(64) PRIMARY KEY,
    counter_value INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS app_meta (
    meta_key VARCHAR(64) PRIMARY KEY,
    meta_value TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
