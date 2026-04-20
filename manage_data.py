#!/usr/bin/env python3
"""
MySQL 数据管理工具
"""
from pprint import pprint
import sys

from mysql_storage import (
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PORT,
    get_storage_summary,
    init_mysql_database,
    load_data,
    reset_database,
)

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


def show_data_summary():
    init_mysql_database(DEFAULT_DATA)
    summary = get_storage_summary(DEFAULT_DATA)
    print("\n" + "=" * 60)
    print("MySQL 数据存储状态")
    print("=" * 60)
    print(f"数据库: {MYSQL_DATABASE}")
    print(f"地址: {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"店铺数量: {summary['stores']}")
    print(f"分类数量: {summary['categories']}")
    print(f"菜品数量: {summary['menu']}")
    print(f"套餐数量: {summary['combos']}")
    print(f"订单数量: {summary['orders']}")
    print(f"评价数量: {summary['reviews']}")
    print(f"用户数量: {summary['users']}")
    print("计数器:")
    pprint(summary["counters"])
    print("=" * 60)


def dump_data():
    init_mysql_database(DEFAULT_DATA)
    data = load_data(DEFAULT_DATA)
    pprint(data)


def reset_all_data():
    init_mysql_database(DEFAULT_DATA)
    confirm = input("确定要将 MySQL 数据重置为空吗? (y/n): ").strip().lower()
    if confirm != "y":
        print("已取消。")
        return
    reset_database(DEFAULT_DATA)
    print("已清空当前 MySQL 数据。")


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "show"
    if command == "show":
        show_data_summary()
    elif command == "dump":
        dump_data()
    elif command == "reset":
        reset_all_data()
    else:
        print(f"未知命令: {command}")
        print("可用命令: show / dump / reset")


if __name__ == "__main__":
    main()
