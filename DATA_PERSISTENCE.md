# 智能外卖管理平台 - MySQL 数据持久化说明

## 功能介绍

当前版本已将原有 JSON 文件持久化方案升级为 MySQL 持久化方案。系统中的店铺、分类、菜品、套餐、订单、评价、用户、地址、收藏和最近浏览记录等数据，都会存储在 MySQL 中。

## 当前存储方案

### 主存储
- MySQL
- 建表脚本：`mysql_schema.sql`
- 存储模块：`mysql_storage.py`

### 历史迁移来源
- `data/app_data.json`

说明：
- `data/app_data.json` 不再是主存储。
- 当 MySQL 中没有业务数据且本地存在旧 JSON 文件时，系统会在启动时自动执行一次 JSON -> MySQL 迁移。

## 环境变量

启动前请配置：

```bash
export MYSQL_HOST="127.0.0.1"
export MYSQL_PORT="3306"
export MYSQL_USER="root"
export MYSQL_PASSWORD="your_password"
export MYSQL_DATABASE="intelligent_food_delivery"
```

## 数据表设计

系统当前使用的核心表包括：

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
- `app_meta`

## 持久化时机

以下操作发生后，都会调用后端 `persist_data()`，并将当前内存中的业务数据整体同步到 MySQL：

- 用户注册
- 店铺信息修改
- 分类新增、编辑、删除
- 菜品新增、编辑、删除、上下架
- 套餐新增、编辑、删除、上下架
- 订单创建、取消、完成、状态推进
- 收藏店铺 / 收藏菜品
- 最近浏览记录写入
- 订单评价
- 地址新增、编辑、删除
- 管理员修改用户状态
- 管理员修改店铺状态

## 工作流程

```text
用户操作
    ↓
API 处理请求
    ↓
修改内存中的业务数据
    ↓
调用 persist_data()
    ↓
mysql_storage.save_data(...)
    ↓
整体写入 MySQL
    ↓
返回结果给前端
```

## 多端同步机制

由于项目通过 5001 / 5002 / 5003 三个端口启动三个 Flask 进程，系统在每次请求前都会重新从 MySQL 读取最新业务数据。

这样可以保证：

- 商家端修改商品或店铺信息后
- 用户端下一次自动请求接口时
- 可以直接看到 MySQL 中的最新结果

## 管理工具

### 查看摘要
```bash
python3 manage_data.py show
```

### 查看完整数据
```bash
python3 manage_data.py dump
```

### 重置为全空
```bash
python3 manage_data.py reset
```

## 手动初始化数据库

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS intelligent_food_delivery DEFAULT CHARACTER SET utf8mb4;"
mysql -u root -p intelligent_food_delivery < mysql_schema.sql
```

## 常见问题

### Q: 启动时报 `ModuleNotFoundError: pymysql`
**A**：说明依赖还未安装，请执行：

```bash
python3 -m pip install -r requirements.txt
```

### Q: 启动时报 MySQL 连接失败
**A**：请检查：
- MySQL 服务是否已启动
- `MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE` 是否配置正确
- 当前账号是否有建库建表权限

### Q: 旧数据为什么没显示出来？
**A**：
- 如果 MySQL 已经有数据，系统不会重复从 JSON 导入
- 若需要重新迁移，可先清空目标数据库，再保留 `data/app_data.json` 后重启系统

### Q: 为什么不再使用 JSON 文件？
**A**：
- MySQL 更适合多表关系建模
- 更适合后续扩展查询、统计与管理功能
- 能更好支持多门户共享同一份持久化数据

## 相关文件

- `app.py`
- `mysql_storage.py`
- `mysql_schema.sql`
- `manage_data.py`
- `test_persistence.py`

---

**最后更新**: 2026/4/20
