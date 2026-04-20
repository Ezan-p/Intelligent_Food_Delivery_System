#!/usr/bin/env python3
"""
测试 MySQL 数据持久化功能
"""
from mysql_storage import MYSQL_DATABASE, MYSQL_HOST, MYSQL_PORT, get_storage_summary, init_mysql_database

DEFAULT_DATA = {
    "stores": [],
    "categories": [],
    "menu": [],
    "combos": [],
    "orders": [],
    "reviews": [],
    "users": [],
    "counters": {}
}


def test_data_persistence():
    init_mysql_database(DEFAULT_DATA)
    summary = get_storage_summary(DEFAULT_DATA)
    print("=" * 50)
    print("开始测试 MySQL 数据持久化")
    print("=" * 50)
    print(f"数据库: {MYSQL_DATABASE}")
    print(f"地址: {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"店铺数量: {summary['stores']}")
    print(f"分类数量: {summary['categories']}")
    print(f"菜单项数量: {summary['menu']}")
    print(f"套餐数量: {summary['combos']}")
    print(f"订单数量: {summary['orders']}")
    print(f"评价数量: {summary['reviews']}")
    print(f"用户数量: {summary['users']}")
    print(f"计数器: {summary['counters']}")
    print("=" * 50)
    print("手动测试建议:")
    print("  1. 确保 MySQL 已启动并完成环境变量配置")
    print("  2. 启动应用: python3 run_portals.py")
    print("  3. 在商家端新增或修改商品、分类、套餐、店铺信息")
    print("  4. 重启应用后确认数据仍然存在")
    print("=" * 50)


if __name__ == '__main__':
    test_data_persistence()
