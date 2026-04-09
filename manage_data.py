#!/usr/bin/env python3
"""
数据持久化演示脚本
演示如何在应用运行时添加数据，然后重启应用后验证数据是否保留
"""
import json
import os
from pathlib import Path

def show_data_summary():
    """显示当前数据的摘要"""
    data_file = 'data/app_data.json'
    
    if not os.path.exists(data_file):
        print("❌ 数据文件不存在，请先运行应用 (python3 app.py 5001)")
        return
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n" + "=" * 60)
        print("📊 数据持久化状态")
        print("=" * 60)
        
        print(f"\n📁 数据文件: {data_file}")
        print(f"💾 文件大小: {os.path.getsize(data_file) / 1024:.2f} KB")
        
        categories = data.get('categories', [])
        menu = data.get('menu', [])
        combos = data.get('combos', [])
        orders = data.get('orders', [])
        users = data.get('users', [])
        counters = data.get('counters', {})
        
        print(f"\n📋 分类数量: {len(categories)}")
        if categories:
            for cat in categories:
                print(f"   • {cat['name']} (ID: {cat['id']})")
        
        print(f"\n🍽️  菜单项数量: {len(menu)}")
        if menu:
            for item in menu[:3]:  # 只显示前 3 个
                image_status = "✓ 有图片" if item.get('image') else "✗ 无图片"
                print(f"   • {item['name']} - ¥{item['price']} {image_status}")
            if len(menu) > 3:
                print(f"   ... 还有 {len(menu) - 3} 项")
        
        print(f"\n🛍️  套餐数量: {len(combos)}")
        if combos:
            for combo in combos:
                print(f"   • {combo['name']} - ¥{combo['price']} ({int(combo['discount']*100)}% 折扣)")
        
        print(f"\n📦 订单数量: {len(orders)}")
        if orders:
            for order in orders[:3]:  # 只显示前 3 个
                print(f"   • 订单 #{order['id']} - {order['customer']} ({order['status']})")
            if len(orders) > 3:
                print(f"   ... 还有 {len(orders) - 3} 个订单")
        
        print(f"\n👥 用户数量: {len(users)}")
        if users:
            for user in users[:3]:  # 只显示前 3 个
                print(f"   • {user['username']} (电话: {user['phone']})")
            if len(users) > 3:
                print(f"   ... 还有 {len(users) - 3} 个用户")
        
        print(f"\n🔢 ID 计数器:")
        print(f"   • next_menu_id: {counters.get('next_menu_id', 'N/A')}")
        print(f"   • next_category_id: {counters.get('next_category_id', 'N/A')}")
        print(f"   • next_combo_id: {counters.get('next_combo_id', 'N/A')}")
        print(f"   • next_order_id: {counters.get('next_order_id', 'N/A')}")
        print(f"   • next_user_id: {counters.get('next_user_id', 'N/A')}")
        
        print("\n" + "=" * 60)
        
    except json.JSONDecodeError:
        print("❌ 数据文件格式错误，请删除后重新启动应用")
    except Exception as e:
        print(f"❌ 读取数据文件失败: {e}")

def reset_data():
    """重置数据到初始状态"""
    data_file = 'data/app_data.json'
    backup_file = 'data/app_data_backup.json'
    
    if os.path.exists(data_file):
        if not os.path.exists(backup_file):
            # 创建备份
            import shutil
            shutil.copy(data_file, backup_file)
            print(f"✅ 已备份数据到 {backup_file}")
        
        os.remove(data_file)
        print(f"✅ 已删除 {data_file}")
        print("⏳ 重启应用后将生成新的数据文件: python3 app.py 5001")
    else:
        print("ℹ️  数据文件不存在，无需重置")

def main():
    import sys
    
    print("\n" + "=" * 60)
    print("🔐 数据持久化管理工具")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'show':
            show_data_summary()
        elif command == 'reset':
            print("\n⚠️  警告: 这将删除所有数据（会先创建备份）")
            confirm = input("确定要重置数据吗? (y/n): ")
            if confirm.lower() == 'y':
                reset_data()
        else:
            print(f"❌ 未知命令: {command}")
    else:
        show_data_summary()
    
    print()

if __name__ == '__main__':
    main()
