# 智能外卖管理平台

这是一个基于 Python Flask 的外卖平台演示项目，包含前端页面、后端接口，以及基于 MySQL 的持久化存储。

## 功能

### 商家端功能
- **店铺绑定**：每个商家账号对应一个独立店铺
- **工作台**：查看本店总订单数、总收入、待处理订单、已完成订单、今日统计等数据
- **商品分类管理**：增删改查商品分类
- **商品管理**：增删改查商品，支持按分类筛选
- **套餐管理**：创建和管理商品套餐，支持折扣设置
- **订单管理**：查看所有订单详情

### 客户端功能
- **店铺浏览**：查看多个商家店铺并进入指定店铺
- **店铺卡片信息**：展示头像/封面、营业状态、营业时间、评分、月售、配送费、起送价、公告
- **商品浏览**：进入店铺后按分类筛选商品，支持套餐购买
- **购物车**：添加商品和套餐到购物车
- **订单提交**：提交包含商品和套餐的订单
- **历史订单查询**：按姓名查询历史订单记录
- **订单状态管理**：查看当前订单状态、取消订单、标记完成

### AI客服功能
- **智能对话**：通过 Flask 后端代理调用远程模型 HTTP API
- **文本对话**：支持自然语言问答
- **图片问答**：支持上传图片（由远程模型服务决定是否启用多模态）
- **外卖咨询**：专门针对外卖业务的智能客服
- **聊天入口**：用户端提供顶部导航 + 悬浮“AI客服”入口
- **上下文记忆**：支持多轮会话记忆与业务背景注入（菜单/套餐/订单摘要）

### 智能服务功能
- **AI客服**：给用户端使用，处理订单、配送、退款和平台咨询
- **智能点餐助手**：给用户端使用，根据人数、预算和偏好推荐菜品与套餐
- **数据智能分析**：给商家端使用，输出订单、营收、热销商品、经营建议

## 运行方式

1. 进入项目目录：
```bash
cd /Users/ezan/Desktop/毕设/智能外卖管理平台
```
2. 安装依赖：
```bash
python3 -m pip install -r requirements.txt
```
3. 配置 MySQL：
```bash
export MYSQL_HOST="127.0.0.1"
export MYSQL_PORT="3306"
export MYSQL_USER="root"
export MYSQL_PASSWORD="your_password"
export MYSQL_DATABASE="intelligent_food_delivery"
```

也可以直接在项目根目录创建 `.env`，内容可参考 [`.env.example`](/Users/ezan/Desktop/毕设/Intelligent Food Delivery System/.env.example)。

如需手动初始化数据库，可执行：
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS intelligent_food_delivery DEFAULT CHARACTER SET utf8mb4;"
mysql -u root -p intelligent_food_delivery < mysql_schema.sql
```

4. 启动服务：
```bash
python3 run_portals.py
```

或者使用环境变量：
```bash
python3 run_portals.py
```

5. 打开浏览器访问：

`http://localhost:5001`、`http://localhost:5002`、`http://localhost:5003`

说明：
- 当前版本主存储为 MySQL。
- 启动时如果 MySQL 为空且本地存在旧的 `data/app_data.json`，系统会自动把旧 JSON 数据迁移到 MySQL。
- `data/app_data.json` 仅保留为历史迁移来源，不再作为主存储。

## 远程AI配置（HTTP API）

项目通过 Flask 后端代理远程模型 API。请在启动前配置以下环境变量：

```bash
export REMOTE_AI_API_URL="https://public-2042136076861014018-iaaa.ksai.scnet.cn:58043/"
export REMOTE_AI_MODEL="Qwen3-30B-A3B"
export REMOTE_AI_API_KEY="your_api_key" # 可选
export REMOTE_AI_TIMEOUT="30"           # 可选，默认30秒
```

启动示例：
```bash
python3 run_portals.py
```

说明：
- 若 `REMOTE_AI_API_URL` 只填了基地址（如上面示例），后端会自动补全为 `/v1/chat/completions`。
- 若远程 AI 服务不可用，后端会自动回退模拟回复，保证聊天页可用。
- `/api/chat` 保留兼容，建议新调用统一使用 `/api/ai-agent`。

## 页面说明

- 用户端：`http://localhost:5001/`
- 商家端：`http://localhost:5002/`
- 管理端：`http://localhost:5003/`
- 每个端口未登录时会先进入 `/login`
- 用户端智能服务：`/chat`、`/smart-order`
- 商家端智能服务：`/data-analysis`

## 数据存储

- 主存储：MySQL
- 建表脚本：`mysql_schema.sql`
- 存储模块：`mysql_storage.py`

核心表：
- `users`
- `user_addresses`
- `user_favorite_stores`
- `user_favorite_menu`
- `user_recent_views`
- `stores`
- `categories`
- `menu_items`
- `combos`
- `combo_items`
- `orders`
- `order_items`
- `reviews`
- `counters`

## API 接口

### 店铺相关
- `GET /api/stores` - 获取可见店铺列表

### 商品相关
- `GET /api/menu` - 获取所有商品
- `POST /api/menu` - 添加商品
- `PUT /api/menu/<id>` - 更新商品
- `DELETE /api/menu/<id>` - 删除商品

### 分类相关
- `GET /api/categories` - 获取所有分类
- `POST /api/categories` - 添加分类
- `PUT /api/categories/<id>` - 更新分类
- `DELETE /api/categories/<id>` - 删除分类

### 套餐相关
- `GET /api/combos` - 获取所有套餐
- `POST /api/combos` - 添加套餐
- `PUT /api/combos/<id>` - 更新套餐
- `DELETE /api/combos/<id>` - 删除套餐

### 订单相关
- `GET /api/orders` - 获取所有订单
- `GET /api/orders?customer=姓名` - 按姓名查询历史订单
- `POST /api/order` - 提交订单
- `POST /api/order/<id>/cancel` - 取消订单
- `POST /api/order/<id>/complete` - 标记订单完成

### 统计相关
- `GET /api/dashboard` - 获取工作台统计数据

### AI 相关
- `POST /api/ai-agent` - AI 代理接口（转发到远程模型 HTTP API）
- `POST /api/chat` - 兼容旧接口（与 `/api/ai-agent` 等价）
