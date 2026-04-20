# 项目结构说明

## 项目目录
```
智能外卖管理平台/
├── .venv/                      # Python 虚拟环境目录（可选）
├── app.py                      # 主应用程序（Flask 后端）
├── mysql_storage.py            # MySQL 存储层（建库、建表、读写、迁移）
├── mysql_schema.sql            # MySQL 建表脚本
├── requirements.txt            # Python 依赖文件
├── README.md                   # 项目说明文档
├── PROJECT_STRUCTURE.md        # 项目结构说明文档
├── DATA_PERSISTENCE.md         # 数据持久化说明文档
├── test_persistence.py         # 数据持久化测试脚本
├── manage_data.py              # 数据管理工具脚本
├── run_portals.py              # 一键同时启动用户端、商家端、管理端
├── data/                       # 历史数据目录（用于 JSON -> MySQL 首次迁移）
│   └── app_data.json           # 旧 JSON 数据文件（不再作为主存储）
├── image/                      # 图片资源目录
│   └── 936ce3dc871111e6b87c0242ac110003_500w_667h.jpg
├── templates/                  # HTML 模板
│   ├── index.html              # 客户端页面（带侧边菜单）
│   ├── merchant.html           # 商家端页面（带侧边菜单）
│   ├── admin.html              # 后台管理端页面
│   ├── login.html              # 分角色登录/注册页面
│   ├── smart_order.html        # 用户端智能点餐助手页面
│   ├── data_analysis.html      # 商家端数据智能分析页面
│   └── chat.html               # AI客服对话页面
└── static/                     # 前端静态资源
    ├── app.js                 # 客户端 JavaScript（页面切换、订单、地址管理）
    ├── merchant.js            # 商家端 JavaScript（店铺、商品、分类、套餐、订单管理）
    ├── admin.js               # 后台管理端 JavaScript（侧边栏导航、店铺、用户、订单总览）
    ├── smart_order.js         # 智能点餐助手交互逻辑
    ├── data_analysis.js       # 数据智能分析交互逻辑
    └── style.css             # 全局样式与响应式布局
```

## 核心功能模块

### 后端：`app.py`
- 使用 Flask 构建 RESTful API
- 提供数据接口：
  - 店铺管理：`/api/stores`
  - 店铺编辑：`PUT /api/stores/<store_id>`
  - 分类管理：`/api/categories`
  - 菜单管理：`/api/menu`
  - 套餐管理：`/api/combos`
  - 订单管理：`/api/order`
  - 用户管理：`/api/users`
  - 地址管理：`/api/addresses`
  - 仪表板统计：`/api/dashboard`
  - AI客服对话代理：`/api/ai-agent`（兼容 `/api/chat`）
- AI 模型集成：
  - 通过 HTTP API 调用远程模型服务
  - 文本对话和图片问答功能（由远程服务能力决定）
  - 远程服务异常时自动回退模拟回复
- 数据持久化：
  - 通过 `mysql_storage.py` 读写 MySQL
  - `load_data()`：从 MySQL 加载数据
  - `save_data()`：将业务数据整体写入 MySQL
  - `persist_data()`：每次数据修改后保存到 MySQL
- 用户认证与会话：
  - 登录、注册、退出
  - 会话 ID 管理
  - 按端口区分用户端、商家端、管理端
  - 页面级访问控制：未登录直接跳转登录页
  - 商家账号与店铺一一对应
  - 用户地址加载和修改

### 前端：`templates/` + `static/`
- `templates/index.html`
  - 客户端主页面
  - 店铺列表浏览、店铺内菜品/套餐浏览、购物车、订单查询、历史订单、地址管理
- `templates/merchant.html`
  - 商家端管理页面
  - 侧边栏切换工作台、店铺管理、分类、菜单、套餐、订单、智能服务
  - 店铺管理支持编辑店铺卡片信息：头像/封面、营业状态、营业时间、评分、月售展示、配送费、起送价、公告
- `templates/admin.html`
  - 后台管理端页面
  - 侧边栏切换平台总览、智能服务监控、店铺经营管理、商家管理、用户管理、最近订单
  - 支持用户账户状态维护、异常用户标记、商家与店铺经营管理、智能服务监控
- `templates/login.html`
  - 按角色区分客户端、商家端、后台管理端登录入口
  - 客户端和商家端支持注册，后台管理端仅管理员登录
- `templates/smart_order.html`
  - 用户端智能点餐助手页面
  - 按人数、预算、偏好生成点餐建议
- `templates/data_analysis.html`
  - 商家端数据智能分析页面
  - 输出经营指标、热销商品、洞察和建议
- `templates/chat.html`
  - AI客服对话界面
  - 支持文本对话和图片上传问答
- `templates/index.html`
  - 新增悬浮“AI客服”聊天入口（直达 `/chat`）

- `static/app.js`
  - 客户端逻辑
  - 页面切换、过滤、购物车、订单提交、地址管理、登录状态
- `static/merchant.js`
  - 商家端逻辑
  - 店铺资料管理、商品管理、分类管理、套餐管理、图片上传、订单处理、侧边栏页面切换
- `static/admin.js`
  - 后台管理端逻辑
  - 平台统计、用户状态管理、商家管理、店铺经营管理、智能服务监控、最近订单、侧边栏页面切换
- `static/smart_order.js`
  - 智能点餐助手逻辑
  - 调用智能推荐接口并渲染推荐结果
- `static/data_analysis.js`
  - 数据智能分析逻辑
  - 调用分析接口并渲染统计、洞察与建议
- `static/style.css`
  - 全局样式
  - 侧边菜单布局
  - 响应式设计

## 数据存储结构

### 主存储
- MySQL
- 建表脚本：`mysql_schema.sql`
- 存储模块：`mysql_storage.py`

### 核心数据表
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

## 模块说明

### `manage_data.py`
- 提供 MySQL 数据查看和重置功能
- 支持命令：
  - `python3 manage_data.py show`
  - `python3 manage_data.py reset`
- 会在重置前备份现有数据

### `test_persistence.py`
- 检查 MySQL 连接配置和持久化数据摘要
- 提供重启验证说明

### `DATA_PERSISTENCE.md`
- 详细说明持久化机制
- 记录数据读写流程和常见问题

## 使用说明

### 启动应用
```bash
python3 run_portals.py
```

### 访问入口
- 客户端：`http://localhost:5001/`
- 商家端：`http://localhost:5002/`
- 后台管理端：`http://localhost:5003/`
- 三个端口未登录时都会先跳转到各自的 `/login`

### 验证数据持久化
1. 启动应用并进入任一端口
2. 操作商品/分类/套餐/订单/地址
3. 关闭应用（Ctrl+C）
4. 重新启动应用
5. 验证数据是否保留

## 项目亮点

- ✅ 侧边菜单页面导航
- ✅ 商品图片上传与持久化
- ✅ 用户登录与地址管理
- ✅ 完整的 CRUD 功能
- ✅ MySQL 数据持久化
- ✅ 响应式界面

## 说明

本说明文档梳理了当前项目结构、关键文件与功能点。若需扩展，可继续补充：
- API 文档
- 前端交互流程
- 部署说明

---
**项目类型**: 毕业设计
**技术栈**: Python + Flask + JavaScript + HTML + CSS
**最后更新**: 2026/4/9
