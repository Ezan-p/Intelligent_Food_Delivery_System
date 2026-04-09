#!/usr/bin/env python3
"""
测试数据持久化功能
"""
import os
import sys
import json
import time
import subprocess

def test_data_persistence():
    """测试数据是否正确保存和恢复"""
    
    data_file = 'data/app_data.json'
    
    print("=" * 50)
    print("开始测试数据持久化功能")
    print("=" * 50)
    
    # 1. 检查数据文件是否存在并显示内容
    if os.path.exists(data_file):
        print(f"\n✓ 数据文件存在: {data_file}")
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✓ 数据文件有效")
                print(f"  - 分类数量: {len(data.get('categories', []))}")
                print(f"  - 菜单项数量: {len(data.get('menu', []))}")
                print(f"  - 套餐数量: {len(data.get('combos', []))}")
                print(f"  - 订单数量: {len(data.get('orders', []))}")
                print(f"  - 用户数量: {len(data.get('users', []))}")
                print(f"  - 下一个菜单ID: {data.get('counters', {}).get('next_menu_id', 'N/A')}")
        except json.JSONDecodeError:
            print("✗ 数据文件格式错误")
    else:
        print(f"\n✗ 数据文件不存在: {data_file}")
    
    print("\n" + "=" * 50)
    print("数据持久化测试完成")
    print("=" * 50)
    print("\n启动服务器进行手动测试:")
    print("  1. 启动应用: python3 app.py 5001")
    print("  2. 访问商家端: http://localhost:5001/merchant")
    print("  3. 添加/编辑/删除商品或分类")
    print("  4. 关闭服务器 (Ctrl+C)")
    print("  5. 重新启动应用，验证数据是否保留")
    print("=" * 50)

if __name__ == '__main__':
    test_data_persistence()
