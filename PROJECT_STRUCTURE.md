# 项目结构说明

## 项目目录
```
智能外卖管理平台/
├── .venv/                      # Python 虚拟环境目录（可选）
├── app.py                      # 主应用程序（Flask 后端）
├── requirements.txt            # Python 依赖文件
├── README.md                   # 项目说明文档
├── PROJECT_STRUCTURE.md        # 项目结构说明文档
├── DATA_PERSISTENCE.md         # 数据持久化说明文档
├── test_persistence.py         # 数据持久化测试脚本
├── manage_data.py              # 数据管理工具脚本
├── data/                       # 数据存储目录（运行时生成）
│   └── app_data.json           # 应用数据文件（JSON格式，运行时创建）
├── image/                      # 图片资源目录
│   └── 936ce3dc871111e6b87c0242ac110003_500w_667h.jpg
├── templates/                  # HTML 模板
│   ├── index.html              # 客户端页面（带侧边菜单）
│   ├── merchant.html           # 商家端页面（带侧边菜单）
│   └── login.html              # 登录/注册页面
└── static/                     # 前端静态资源
    ├── app.js                 # 客户端 JavaScript（页面切换、订单、地址管理）
    ├── merchant.js            # 商家端 JavaScript（商品、分类、套餐、订单管理）
    └── style.css             # 全局样式与响应式布局
```

## 核心功能模块

### 后端：`app.py`
- 使用 Flask 构建 RESTful API
- 提供数据接口：
  - 分类管理：`/api/categories`
  - 菜单管理：`/api/menu`
  - 套餐管理：`/api/combos`
  - 订单管理：`/api/order`
  - 用户管理：`/api/users`
  - 地址管理：`/api/addresses`
  - 仪表板统计：`/api/dashboard`
- 数据持久化：
  - `load_data()`：从 `data/app_data.json` 读取数据
  - `save_data()`：将数据写入文件
  - `persist_data()`：每次数据修改后保存
- 用户认证与会话：
  - 登录、注册、退出
  - 会话 ID 管理
  - 用户地址加载和修改

### 前端：`templates/` + `static/`
- `templates/index.html`
  - 客户端主页面
  - 菜单浏览、套餐推荐、购物车、订单查询、历史订单、地址管理
- `templates/merchant.html`
  - 商家端管理页面
  - 分类、菜单、套餐、图片上传、订单、统计
- `templates/login.html`
  - 用户登录与注册

- `static/app.js`
  - 客户端逻辑
  - 页面切换、过滤、购物车、订单提交、地址管理、登录状态
- `static/merchant.js`
  - 商家端逻辑
  - 商品管理、分类管理、套餐管理、图片上传、订单处理
- `static/style.css`
  - 全局样式
  - 侧边菜单布局
  - 响应式设计

## 数据存储结构

### 运行时目录
- `data/app_data.json`：运行时自动创建
- `image/`：静态图片资源目录

### JSON 数据结构
```json
{
  "categories": [],
  "menu": [],
  "combos": [],
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
```

## 模块说明

### `manage_data.py`
- 提供数据查看和重置功能
- 支持命令：
  - `python3 manage_data.py show`
  - `python3 manage_data.py reset`
- 会在重置前备份现有数据

### `test_persistence.py`
- 检查 `data/app_data.json` 是否存在
- 读取并显示持久化数据摘要
- 提供重启验证说明

### `DATA_PERSISTENCE.md`
- 详细说明持久化机制
- 记录数据读写流程和常见问题

## 使用说明

### 启动应用
```bash
python3 app.py 5001
```

### 访问入口
- 客户端：`http://localhost:5001/`
- 商家端：`http://localhost:5001/merchant`
- 登录页：`http://localhost:5001/login`

### 验证数据持久化
1. 启动应用并进入商家端
2. 操作商品/分类/套餐/订单/地址
3. 关闭应用（Ctrl+C）
4. 重新启动应用
5. 验证数据是否保留

## 项目亮点

- ✅ 侧边菜单页面导航
- ✅ 商品图片上传与持久化
- ✅ 用户登录与地址管理
- ✅ 完整的 CRUD 功能
- ✅ JSON 数据持久化
- ✅ 响应式界面

## 说明

本说明文档梳理了当前项目结构、关键文件与功能点。若需扩展，可继续补充：
- API 文档
- 前端交互流程
- 部署说明

---
**项目类型**: 毕业设计
**技术栈**: Python + Flask + JavaScript + HTML + CSS
**最后更新**: 2026/4/8

