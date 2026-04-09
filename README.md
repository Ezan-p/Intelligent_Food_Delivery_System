# 智能外卖管理平台

这是一个基于 Python Flask 的外卖平台演示项目，包含前端页面和后端接口。

## 功能

### 商家端功能
- **工作台**：查看总订单数、总收入、待处理订单、已完成订单、今日统计等数据
- **商品分类管理**：增删改查商品分类
- **商品管理**：增删改查商品，支持按分类筛选
- **套餐管理**：创建和管理商品套餐，支持折扣设置
- **订单管理**：查看所有订单详情

### 客户端功能
- **商品浏览**：按分类筛选商品，支持套餐购买
- **购物车**：添加商品和套餐到购物车
- **订单提交**：提交包含商品和套餐的订单
- **历史订单查询**：按姓名查询历史订单记录
- **订单状态管理**：查看当前订单状态、取消订单、标记完成

## 运行方式

1. 进入项目目录：
```bash
cd /Users/ezan/Desktop/毕设/智能外卖管理平台
```
2. 安装依赖：
```bash
python3 -m pip install -r requirements.txt
```
3. 启动服务：
```bash
python3 app.py 5001
```

或者使用环境变量：
```bash
PORT=5001 python3 app.py
```

4. 打开浏览器访问：

`http://localhost:5001`

## 页面说明

- 客户端：`/`
- 商家端：`/merchant`

## API 接口

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
