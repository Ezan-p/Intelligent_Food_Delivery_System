import os
import sys
import json
import re
import base64
from urllib.parse import urlparse
from flask import Flask, jsonify, request, render_template, redirect, make_response
from datetime import datetime
import requests
from mysql_storage import (
    format_mysql_error,
    init_mysql_database,
    load_data as load_mysql_data,
    save_data as save_mysql_data,
)

app = Flask(__name__)

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# 旧 JSON 数据文件路径，仅用于首次迁移到 MySQL
DATA_DIR = 'data'
DATA_FILE = os.path.join(DATA_DIR, 'app_data.json')

# 创建 data 目录（如果不存在）
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 远程 AI API 配置
DEFAULT_REMOTE_AI_BASE_URL = "http://127.0.0.1:7860"
DEFAULT_REMOTE_AI_MODEL = ""

def normalize_remote_ai_api_url(url):
    """统一保留服务基地址，不在这里拼接具体 API 路径。"""
    normalized = (url or "").strip()
    if not normalized:
        return ""
    return normalized.rstrip("/")

REMOTE_AI_API_URL = normalize_remote_ai_api_url(
    os.environ.get('REMOTE_AI_API_URL', DEFAULT_REMOTE_AI_BASE_URL)
)
REMOTE_AI_API_KEY = os.environ.get('REMOTE_AI_API_KEY', '').strip()
REMOTE_AI_MODEL = os.environ.get('REMOTE_AI_MODEL', DEFAULT_REMOTE_AI_MODEL).strip()
REMOTE_AI_TIMEOUT = float(os.environ.get('REMOTE_AI_TIMEOUT', '120'))
REMOTE_AI_CONNECT_TIMEOUT = float(os.environ.get('REMOTE_AI_CONNECT_TIMEOUT', '10'))
REMOTE_AI_MAX_TOKENS = int(os.environ.get('REMOTE_AI_MAX_TOKENS', '768'))
REMOTE_AI_CONTINUE_ROUNDS = int(os.environ.get('REMOTE_AI_CONTINUE_ROUNDS', '2'))
AI_CONTEXT_MAX_MESSAGES = int(os.environ.get('AI_CONTEXT_MAX_MESSAGES', '12'))
REMOTE_AI_SYSTEM_PROMPT = os.environ.get(
    'REMOTE_AI_SYSTEM_PROMPT',
    '你是智能外卖平台的AI客服助手。请用友好、专业、简洁的语气解答与菜品、下单、配送、退款、地址相关问题。'
    '不要输出你的思考过程、推理步骤或中间分析，只输出最终答复内容。'
).strip()
ACTIVE_REMOTE_AI_API_URL = REMOTE_AI_API_URL
USE_MODEL_FIELD = True
SERVICE_MONITOR = {
    "ai_chat_requests": 0,
    "ai_chat_failures": 0,
    "smart_order_requests": 0,
    "smart_order_failures": 0,
    "data_analysis_requests": 0,
    "data_analysis_failures": 0,
    "last_ai_chat_at": "",
    "last_smart_order_at": "",
    "last_data_analysis_at": ""
}

def looks_like_truncated_answer(text):
    if not isinstance(text, str):
        return False
    s = text.strip()
    if len(s) < 40:
        return False

    # 以完整句末符号结束时通常已完成
    end_ok = ("。", "！", "？", ".", "!", "?", "）", ")", "]", "】", "」", "\"")
    if s.endswith(end_ok):
        return False

    # 以连接性符号结尾通常是截断
    likely_cut = ("，", ",", "、", "：", ":", "；", ";", "（", "(", "-", "—", "…")
    if s.endswith(likely_cut):
        return True

    # 默认：较长但无正常句末，按疑似截断处理
    return True

def merge_ai_chunks(base_text, extra_text):
    base = (base_text or "").strip()
    extra = (extra_text or "").strip()
    if not base:
        return extra
    if not extra:
        return base
    if extra in base:
        return base

    # 简单重叠去重：匹配 base 后缀与 extra 前缀
    max_overlap = min(len(base), len(extra), 120)
    overlap = 0
    for i in range(max_overlap, 10, -1):
        if base[-i:] == extra[:i]:
            overlap = i
            break
    if overlap > 0:
        return (base + extra[overlap:]).strip()
    return (base + "\n" + extra).strip()

def generate_conversation_id():
    return f"conv_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"

def trim_conversation_history(history):
    if not isinstance(history, list):
        return []
    if AI_CONTEXT_MAX_MESSAGES <= 0:
        return history
    return history[-AI_CONTEXT_MAX_MESSAGES:]

def build_ai_conversation_title(message):
    text = (message or "").strip()
    if not text:
        return "新对话"
    normalized = re.sub(r"\s+", " ", text)
    return normalized[:24] or "新对话"

def serialize_conversation_message(message):
    return {
        "role": message.get("role", "assistant"),
        "content": message.get("content", ""),
        "created_at": message.get("created_at", "")
    }

def serialize_conversation_summary(conversation):
    messages = conversation.get("messages", [])
    preview = ""
    for message in reversed(messages):
        content = (message.get("content") or "").strip()
        if content:
            preview = content[:60]
            break
    return {
        "id": conversation.get("id"),
        "title": conversation.get("title") or "新对话",
        "preview": preview,
        "created_at": conversation.get("created_at", ""),
        "updated_at": conversation.get("updated_at", "")
    }

def serialize_conversation_detail(conversation):
    payload = serialize_conversation_summary(conversation)
    payload["messages"] = [serialize_conversation_message(message) for message in conversation.get("messages", [])]
    return payload

def get_ai_conversations_for_user(user_id):
    return sorted(
        [conversation for conversation in ai_conversations if conversation.get("user_id") == user_id],
        key=lambda item: (item.get("updated_at", ""), item.get("created_at", ""), item.get("id", "")),
        reverse=True
    )

def get_ai_conversation_by_id(conversation_id, user_id=None):
    for conversation in ai_conversations:
        if conversation.get("id") != conversation_id:
            continue
        if user_id is not None and conversation.get("user_id") != user_id:
            return None
        return conversation
    return None

def create_ai_conversation(user, title="新对话"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conversation = {
        "id": generate_conversation_id(),
        "user_id": user.get("id"),
        "title": title or "新对话",
        "created_at": now,
        "updated_at": now,
        "messages": []
    }
    ai_conversations.append(conversation)
    persist_data()
    return conversation

def append_ai_conversation_message(conversation, role, content):
    text = (content or "").strip()
    if not text:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conversation.setdefault("messages", []).append({
        "role": role,
        "content": text,
        "created_at": now
    })
    conversation["messages"] = trim_conversation_history(conversation.get("messages", []))
    conversation["updated_at"] = now

def get_user_by_session(session_id):
    session_payload = get_session_payload(session_id)
    if not session_payload:
        return None
    user_id = session_payload.get("user_id")
    return next((u for u in users if u.get('id') == user_id), None)

def build_store_catalog_summary():
    if not stores:
        return "当前暂无店铺数据。"

    catalog_lines = []
    active_stores = filter_active_records(stores)
    source_stores = active_stores if active_stores else stores

    for store in source_stores:
        store_id = store.get('id')
        store_categories = [c for c in categories if c.get('store_id') == store_id and c.get('status', 'active') == 'active']
        store_menu = [item for item in menu if item.get('store_id') == store_id and item.get('status', 'active') == 'active']
        store_combos = [combo for combo in combos if combo.get('store_id') == store_id and combo.get('status', 'active') == 'active']

        category_names = "、".join(cat.get('name', '') for cat in store_categories[:6] if cat.get('name')) or "未分类"
        menu_names = "；".join(
            f"{item.get('name')} ¥{float(item.get('price', 0)):.2f}"
            for item in store_menu[:8]
        ) or "暂无菜品"
        combo_names = "；".join(
            f"{combo.get('name')} ¥{float(combo.get('price', 0)) * float(combo.get('discount', 1)):.2f}"
            for combo in store_combos[:5]
        ) or "暂无套餐"

        catalog_lines.append(
            f"店铺【{store.get('name')}】"
            f" 评分{float(store.get('rating', 0)):.1f}"
            f" 月售{store.get('monthly_sales', 0)}"
            f" 配送费¥{float(store.get('delivery_fee', 0)):.2f}"
            f" 起送¥{float(store.get('min_order_amount', 0)):.2f}"
            f" 营业状态:{store.get('business_status', '营业中')}"
            f" 分类:{category_names}"
            f" 菜品:{menu_names}"
            f" 套餐:{combo_names}"
        )

    return "\n".join(catalog_lines)

def build_user_preference_summary(user):
    if not user:
        return "当前无登录用户画像。"

    lines = [f"当前登录用户：{user.get('username')}"]

    favorite_store_names = [
        store.get('name')
        for store in stores
        if store.get('id') in user.get('favorite_store_ids', [])
    ]
    favorite_item_names = [
        item.get('name')
        for item in menu
        if item.get('id') in user.get('favorite_menu_ids', [])
    ]
    recent_orders = [o for o in orders if o.get("customer") == user.get("username")]
    recent_views = user.get('recent_views', [])[-5:]
    default_address = next((addr for addr in user.get('addresses', []) if addr.get('is_default')), None)
    if not default_address and user.get('addresses'):
        default_address = user['addresses'][0]

    if favorite_store_names:
        lines.append(f"收藏店铺：{'；'.join(favorite_store_names[:6])}")
    if favorite_item_names:
        lines.append(f"收藏菜品：{'；'.join(favorite_item_names[:8])}")

    if recent_orders:
        order_lines = []
        for order in recent_orders[-5:]:
            item_names = "、".join(item.get('name', '') for item in order.get('items', [])[:5] if item.get('name')) or "无商品明细"
            order_lines.append(
                f"订单#{order.get('id')} 店铺:{order.get('store_name', '')} 状态:{order.get('status')} 金额:¥{float(order.get('total', 0)):.2f} 商品:{item_names}"
            )
        lines.append("历史订单：" + "；".join(order_lines))
    else:
        lines.append("历史订单：暂无订单记录。")

    if recent_views:
        view_descriptions = []
        for view in recent_views:
            if view.get('type') == 'store':
                store = get_store_by_id(view.get('store_id'))
                if store:
                    view_descriptions.append(f"最近浏览店铺:{store.get('name')}")
            elif view.get('type') == 'item':
                item = next((menu_item for menu_item in menu if menu_item.get('id') == view.get('item_id')), None)
                if item:
                    view_descriptions.append(f"最近浏览菜品:{item.get('name')}")
        if view_descriptions:
            lines.append("浏览偏好：" + "；".join(view_descriptions))

    if default_address:
        lines.append(f"默认地址：{default_address.get('address')}")

    lines.append("推荐时优先结合用户历史订单、收藏店铺、收藏菜品、最近浏览记录进行个性化推荐。")
    return "\n".join(lines)

def truncate_text(value, max_length=120):
    text = str(value or "").strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."

def build_compact_user_preference_summary(user):
    if not user:
        return "用户画像：暂无。"

    favorite_store_names = [
        store.get('name')
        for store in stores
        if store.get('id') in (user.get('favorite_store_ids') or [])
    ][:3]
    favorite_item_names = [
        item.get('name')
        for item in menu
        if item.get('id') in (user.get('favorite_menu_ids') or [])
    ][:4]
    recent_orders = [order for order in orders if order.get("customer") == user.get("username")][-2:]
    recent_order_items = []
    for order in recent_orders:
        recent_order_items.extend([
            ordered_item.get('name')
            for ordered_item in order.get('items', [])[:3]
            if ordered_item.get('name')
        ])
    recent_order_items = recent_order_items[:5]
    recent_views = user.get('recent_views', [])[-4:]
    recent_view_labels = []
    for view in recent_views:
        if view.get('type') == 'store':
            store = get_store_by_id(view.get('store_id'))
            if store:
                recent_view_labels.append(f"店铺:{store.get('name')}")
        elif view.get('type') == 'item':
            item = next((menu_item for menu_item in menu if menu_item.get('id') == view.get('item_id')), None)
            if item:
                recent_view_labels.append(f"菜品:{item.get('name')}")

    summary_parts = [f"用户:{user.get('username')}"]
    if favorite_store_names:
        summary_parts.append("收藏店铺:" + "、".join(favorite_store_names))
    if favorite_item_names:
        summary_parts.append("收藏菜品:" + "、".join(favorite_item_names))
    if recent_order_items:
        summary_parts.append("近单:" + "、".join(recent_order_items))
    if recent_view_labels:
        summary_parts.append("近浏览:" + "、".join(recent_view_labels[:4]))
    return "；".join(summary_parts)

def build_compact_smart_plan_summary(plan):
    if not isinstance(plan, dict):
        return "暂无推荐结构。"

    store = plan.get("store") or {}
    item_parts = []
    for item in (plan.get("items") or [])[:4]:
        item_parts.append(
            f"{item.get('name')} ¥{float(item.get('price', 0)):.2f} 理由:{truncate_text(item.get('reason', ''), 24)}"
        )
    combo_parts = []
    for combo in (plan.get("combo_alternatives") or [])[:2]:
        combo_parts.append(f"{combo.get('name')} ¥{float(combo.get('price', 0)):.2f}")

    lines = [
        f"推荐店铺:{store.get('name', '未知店铺')}",
        f"组合总价:¥{float(plan.get('total_price', 0)):.2f}",
        f"约束:{'、'.join(plan.get('constraint_labels') or []) or '无'}",
        "推荐菜品:" + ("；".join(item_parts) if item_parts else "无"),
        "套餐备选:" + ("；".join(combo_parts) if combo_parts else "无"),
    ]
    return "\n".join(lines)

def build_smart_order_model_prompt(user, action, people_count, budget, preferences, scoped_menu, scoped_combos, plan):
    menu_preview = "；".join([
        f"{item.get('name')} ¥{float(item.get('price', 0)):.2f}"
        for item in scoped_menu[:6]
    ]) or "暂无菜单数据"
    combo_preview = "；".join([
        f"{combo.get('name')} ¥{float(combo.get('price', 0)) * float(combo.get('discount', 1)):.2f}"
        for combo in scoped_combos[:3]
    ]) or "暂无套餐数据"

    prompt = (
        "你是智能外卖平台的点餐助手。"
        "请基于以下摘要，用简洁中文输出 3-5 句说明：为什么这样搭配、是否符合预算、下一步如何继续调整。"
        "不要复述原始数据，不要输出 JSON，不要长篇分析。\n"
        f"{build_compact_user_preference_summary(user)}\n"
        f"操作:{action}\n"
        f"人数:{people_count}\n"
        f"预算:{budget if budget not in (None, '') else '未提供'}\n"
        f"偏好:{truncate_text(preferences or '未提供', 80)}\n"
        f"菜单摘要:{menu_preview}\n"
        f"套餐摘要:{combo_preview}\n"
        f"推荐摘要:\n{build_compact_smart_plan_summary(plan)}"
    )
    return truncate_text(prompt, 2200)

def extract_requirement_keywords_with_ai(other_requirements):
    requirement_text = str(other_requirements or "").strip()
    if not requirement_text:
        return [], None

    prompt = (
        "请从以下外卖点餐需求中提炼 3 到 6 个可用于搜索店铺或菜品的短关键词。"
        "只返回关键词，使用中文顿号分隔，不要解释。\n"
        f"需求：{truncate_text(requirement_text, 120)}"
    )
    ai_response, err = call_remote_ai_api(prompt)
    if ai_response:
        normalized = re.split(r"[、,，\n]+", ai_response.strip())
        keywords = []
        for item in normalized:
            keyword = item.strip().strip("。；;")
            if len(keyword) >= 2 and keyword not in keywords:
                keywords.append(keyword)
        return keywords[:6], None
    return [], err

def build_preference_text(preference_tags=None, other_requirements=""):
    tags = [str(tag).strip() for tag in (preference_tags or []) if str(tag).strip()]
    extracted_keywords, ai_err = extract_requirement_keywords_with_ai(other_requirements)
    if not extracted_keywords:
        extracted_keywords = extract_search_terms(other_requirements)[:6] if other_requirements else []

    combined_tokens = []
    for token in tags + extracted_keywords:
        if token and token not in combined_tokens:
            combined_tokens.append(token)

    return {
        "preference_text": "、".join(combined_tokens),
        "requirement_keywords": extracted_keywords,
        "keyword_source": "remote_ai" if extracted_keywords and not ai_err else "local_fallback" if extracted_keywords else "none",
        "keyword_warning": ai_err,
    }

def extract_search_terms(text):
    raw_text = str(text or "").strip().lower()
    if not raw_text:
        return []

    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", raw_text)
    chunks = [chunk.strip() for chunk in normalized.split() if chunk.strip()]
    terms = []
    for chunk in chunks:
        if len(chunk) >= 2:
            terms.append(chunk)
        if len(chunk) >= 4:
            for size in range(min(6, len(chunk)), 1, -1):
                for idx in range(0, len(chunk) - size + 1):
                    piece = chunk[idx:idx + size]
                    if len(piece) >= 2:
                        terms.append(piece)

    deduped = []
    for term in terms:
        if term not in deduped:
            deduped.append(term)
    return deduped[:24]

def clamp_similarity_score(raw_score, term_count, bonus=0):
    if term_count <= 0:
        return 0
    normalized = (raw_score + bonus) / max(term_count * 8, 1)
    return max(0, min(100, int(round(normalized * 100))))

def serialize_catalog_item(item, similarity_score=0):
    store = get_store_by_id(item.get('store_id'))
    category = next((cat for cat in categories if cat.get('id') == item.get('category_id')), None)
    return {
        "type": "item",
        "id": item.get('id'),
        "store_id": item.get('store_id'),
        "store_name": store.get('name') if store else '',
        "name": item.get('name'),
        "description": item.get('description', ''),
        "price": float(item.get('price', 0)),
        "image": item.get('image'),
        "category_name": category.get('name') if category else '',
        "similarity_score": similarity_score,
    }

def serialize_catalog_combo(combo, similarity_score=0):
    store = get_store_by_id(combo.get('store_id'))
    combo_price = float(combo.get('price', 0)) * float(combo.get('discount', 1))
    return {
        "type": "combo",
        "id": combo.get('id'),
        "store_id": combo.get('store_id'),
        "store_name": store.get('name') if store else '',
        "name": combo.get('name'),
        "description": combo.get('description', ''),
        "price": combo_price,
        "original_price": float(combo.get('price', 0)),
        "discount": float(combo.get('discount', 1)),
        "items": combo.get('items', []),
        "similarity_score": similarity_score,
    }

def search_catalog_candidates(query_text):
    terms = extract_search_terms(query_text)
    if not terms:
        return {"stores": [], "items": [], "combos": []}

    scored_stores = []
    visible_stores = get_visible_stores()
    for store in visible_stores:
        store_name = str(store.get('name', '')).lower()
        haystack = " ".join([
            store_name,
            str(store.get('description', '')),
            str(store.get('announcement', '')),
            str(store.get('business_status', ''))
        ]).lower()
        score = 0
        exact_hits = 0
        for term in terms:
            if term == store_name:
                score += 12
                exact_hits += 1
            elif term in store_name:
                score += 8
            elif term in haystack:
                score += 3
        if score:
            similarity = clamp_similarity_score(score, len(terms), bonus=exact_hits * 8)
            store_payload = serialize_store(store)
            store_payload["similarity_score"] = similarity
            scored_stores.append((similarity, score, store_payload))

    scored_items = []
    for item in filter_active_records(menu):
        store = get_store_by_id(item.get('store_id'))
        if not store or store.get('status', 'active') != 'active':
            continue
        category = next((cat for cat in categories if cat.get('id') == item.get('category_id')), None)
        item_name = str(item.get('name', '')).lower()
        haystack = " ".join([
            item_name,
            str(item.get('description', '')),
            str(category.get('name', '') if category else ''),
            str(store.get('name', '')),
            str(store.get('description', ''))
        ]).lower()
        score = 0
        exact_hits = 0
        for term in terms:
            if term == item_name:
                score += 15
                exact_hits += 1
            elif term in item_name:
                score += 10
            elif term in haystack:
                score += 4
        if score:
            similarity = clamp_similarity_score(score, len(terms), bonus=exact_hits * 10)
            scored_items.append((similarity, score, serialize_catalog_item(item, similarity)))

    scored_combos = []
    for combo in filter_active_records(combos):
        store = get_store_by_id(combo.get('store_id'))
        if not store or store.get('status', 'active') != 'active':
            continue
        combo_name = str(combo.get('name', '')).lower()
        combo_item_names = " ".join(
            next((menu_item.get('name', '') for menu_item in menu if menu_item.get('id') == item_id), '')
            for item_id in combo.get('items', [])
        )
        haystack = " ".join([
            combo_name,
            str(combo.get('description', '')),
            combo_item_names,
            str(store.get('name', ''))
        ]).lower()
        score = 0
        exact_hits = 0
        for term in terms:
            if term == combo_name:
                score += 15
                exact_hits += 1
            elif term in combo_name:
                score += 10
            elif term in haystack:
                score += 4
        if score:
            similarity = clamp_similarity_score(score, len(terms), bonus=exact_hits * 10)
            scored_combos.append((similarity, score, serialize_catalog_combo(combo, similarity)))

    scored_stores.sort(key=lambda item: (item[0], item[1], float(item[2].get('rating', 0))), reverse=True)
    scored_items.sort(key=lambda item: (item[0], item[1], -float(item[2].get('price', 0))), reverse=True)
    scored_combos.sort(key=lambda item: (item[0], item[1], -float(item[2].get('price', 0))), reverse=True)

    return {
        "stores": [store for _, _, store in scored_stores[:5]],
        "items": [item for _, _, item in scored_items[:8]],
        "combos": [combo for _, _, combo in scored_combos[:5]],
    }

def build_candidate_context_text(candidates):
    if not candidates:
        return ""

    store_lines = []
    for store in candidates.get("stores", []):
        store_lines.append(
            f"{store.get('name')} 评分{float(store.get('rating', 0)):.1f} "
            f"配送费¥{float(store.get('delivery_fee', 0)):.2f} 起送¥{float(store.get('min_order_amount', 0)):.2f}"
            f" 相似度{int(store.get('similarity_score', 0))}"
        )

    item_lines = []
    for item in candidates.get("items", []):
        item_lines.append(
            f"{item.get('name')} ¥{float(item.get('price', 0)):.2f} "
            f"店铺:{item.get('store_name') or '未知店铺'} 描述:{item.get('description', '')} 相似度{int(item.get('similarity_score', 0))}"
        )

    combo_lines = []
    for combo in candidates.get("combos", []):
        combo_lines.append(
            f"{combo.get('name')} 到手约¥{float(combo.get('price', 0)):.2f} "
            f"店铺:{combo.get('store_name') or '未知店铺'} 描述:{combo.get('description', '')} 相似度{int(combo.get('similarity_score', 0))}"
        )

    lines = []
    if store_lines:
        lines.append("图片识别后命中的相关店铺：" + "；".join(store_lines))
    if item_lines:
        lines.append("图片识别后命中的相关菜品：" + "；".join(item_lines))
    if combo_lines:
        lines.append("图片识别后命中的相关套餐：" + "；".join(combo_lines))
    return "\n".join(lines)

def build_recommendation_cards(candidates):
    cards = []
    for store in candidates.get("stores", []):
        cards.append({
            "card_type": "store",
            "target_type": "store",
            "store_id": store.get("id"),
            "title": store.get("name"),
            "subtitle": f"评分 {float(store.get('rating', 0)):.1f} · 配送费 ¥{float(store.get('delivery_fee', 0)):.2f}",
            "description": store.get("description", "") or store.get("announcement", ""),
            "price_text": f"起送 ¥{float(store.get('min_order_amount', 0)):.2f}",
            "similarity_score": int(store.get("similarity_score", 0)),
        })
    for item in candidates.get("items", []):
        cards.append({
            "card_type": "item",
            "target_type": "item",
            "store_id": item.get("store_id"),
            "item_id": item.get("id"),
            "title": item.get("name"),
            "subtitle": item.get("store_name", ""),
            "description": item.get("description", ""),
            "price_text": f"¥{float(item.get('price', 0)):.2f}",
            "similarity_score": int(item.get("similarity_score", 0)),
        })
    for combo in candidates.get("combos", []):
        cards.append({
            "card_type": "combo",
            "target_type": "combo",
            "store_id": combo.get("store_id"),
            "combo_id": combo.get("id"),
            "title": combo.get("name"),
            "subtitle": combo.get("store_name", ""),
            "description": combo.get("description", ""),
            "price_text": f"到手约 ¥{float(combo.get('price', 0)):.2f}",
            "similarity_score": int(combo.get("similarity_score", 0)),
        })
    cards.sort(key=lambda card: card.get("similarity_score", 0), reverse=True)
    return cards[:8]

def build_image_recommendation_context(image_url, user_message="", session_id=None):
    recognition_prompt = (
        "请识别这张食物图片中的餐品、食材、口味或品类，"
        "输出适合用于外卖搜索和推荐的关键词、菜名或食物描述。"
        "不要解释过程，直接给出识别结果。"
    )
    recognized_text, err = call_remote_ai_api(
        recognition_prompt,
        image_url=image_url,
        history=None,
        session_id=session_id
    )
    if not recognized_text:
        return "", err

    combined_query = f"{recognized_text}\n{user_message or ''}".strip()
    candidates = search_catalog_candidates(combined_query)
    candidate_context = build_candidate_context_text(candidates)

    lines = [
        f"用户上传图片后，模型识别结果：{recognized_text}",
    ]
    if candidate_context:
        lines.append(candidate_context)
        lines.append("请结合图片识别结果和上述命中的店铺、菜品、套餐，为用户做贴合图片内容的推荐。")
    else:
        lines.append("当前平台中没有检索到高度匹配的店铺、菜品或套餐，请基于识别结果给出接近的推荐方向。")

    return "\n".join(lines), None, {
        "recognized_text": recognized_text,
        "candidates": candidates,
        "recommendation_cards": build_recommendation_cards(candidates)
    }

def build_business_context_text(session_id=None):
    lines = [
        "你是智能外卖平台的智能客服与推荐助手。",
        "你可以读取平台店铺、菜品、套餐、用户历史订单、收藏记录和最近浏览记录，为用户提供推荐。",
        "回答时可以结合用户问题，自然组织回复内容，不要套用固定模板。",
        "如果合适，可以给出具体店铺名、菜品名、套餐名、价格区间和推荐理由。",
        "如果用户表达的是点餐需求、预算、口味、人数、场景，请直接进入推荐模式，不要只做泛泛介绍。",
        "如果用户咨询订单问题、复购建议或吃什么，也要结合历史订单和收藏记录进行回答。",
        "信息不足时请明确说明，并引导用户补充预算、人数、口味、忌口、店铺偏好等信息。"
    ]

    lines.append("平台店铺与商品目录：")
    lines.append(build_store_catalog_summary())

    user = get_user_by_session(session_id)
    if user:
        lines.append(build_user_preference_summary(user))
    else:
        orders_preview = orders[-5:]
        recent_text = "；".join([
            f"订单#{o.get('id')} 用户:{o.get('customer')} 状态:{o.get('status')}"
            for o in orders_preview
        ])
        if recent_text:
            lines.append(f"平台最近订单（摘要）：{recent_text}")

    lines.append("如果用户询问订单状态，优先基于已有历史订单回答；若无法定位，再引导提供订单号。")
    lines.append("请根据用户问题自由组织回答形式，但要尽量利用已提供的平台数据和用户数据。")
    return "\n".join(lines)

def build_remote_ai_candidate_urls(url):
    """当返回404时，自动尝试常见接口路径"""
    if not url:
        return []

    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = (parsed.path or "").rstrip("/")

    candidates = []
    def add_candidate(candidate):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add_candidate(url)

    if not path or path == "":
        add_candidate(origin + "/v1/chat/completions")
        add_candidate(origin + "/chat/completions")
        add_candidate(origin + "/api/chat")
        add_candidate(origin + "/generate")
    elif path.endswith("/v1/chat/completions"):
        add_candidate(origin + "/chat/completions")
        add_candidate(origin + "/v1/completions")
        add_candidate(origin + "/api/chat")
    else:
        add_candidate(origin + "/v1/chat/completions")
        add_candidate(origin + "/chat/completions")
        add_candidate(origin + "/api/chat")

    return candidates

# 默认数据结构
DEFAULT_DATA = {
    "stores": [],
    "categories": [
        {"id": 1, "name": "主菜", "store_id": 1},
        {"id": 2, "name": "面食", "store_id": 1},
        {"id": 3, "name": "饮品", "store_id": 1},
        {"id": 4, "name": "套餐", "store_id": 1}
    ],
    "menu": [
        {"id": 1, "name": "麻辣香锅", "description": "香辣可口，大份足量。", "price": 36.0, "category_id": 1, "store_id": 1, "image": None},
        {"id": 2, "name": "宫保鸡丁", "description": "经典川菜，微辣下饭。", "price": 28.0, "category_id": 1, "store_id": 1, "image": None},
        {"id": 3, "name": "番茄牛腩面", "description": "汤浓味足，面条劲道。", "price": 32.0, "category_id": 2, "store_id": 1, "image": None},
        {"id": 4, "name": "红烧茄子盖饭", "description": "家常口味，茄子软糯。", "price": 22.0, "category_id": 1, "store_id": 1, "image": None},
        {"id": 5, "name": "小龙虾套餐", "description": "麻辣龙虾，赠送饮料。", "price": 88.0, "category_id": 4, "store_id": 1, "image": None}
    ],
    "combos": [
        {"id": 1, "name": "家庭套餐", "description": "适合家庭聚餐", "price": 128.0, "items": [1, 2, 3], "discount": 0.9, "store_id": 1}
    ],
    "orders": [],
    "reviews": [],
    "users": [],
    "ai_conversations": [],
    "counters": {
        "next_order_id": 1,
        "next_menu_id": 6,
        "next_category_id": 5,
        "next_combo_id": 2,
        "next_user_id": 1,
        "next_store_id": 1,
        "next_review_id": 1
    }
}

ROLE_LABELS = {
    "customer": "客户端用户",
    "merchant": "商家用户",
    "admin": "管理员"
}

PORTAL_PORTS = {
    "customer": int(os.environ.get("CUSTOMER_PORT", "5001")),
    "merchant": int(os.environ.get("MERCHANT_PORT", "5002")),
    "admin": int(os.environ.get("ADMIN_PORT", "5003"))
}

SESSION_COOKIE_NAMES = {
    "customer": "customer_portal_session",
    "merchant": "merchant_portal_session",
    "admin": "admin_portal_session"
}

DEFAULT_ACCOUNTS = [
    {
        "username": "merchant",
        "password": "merchant123",
        "phone": "",
        "role": "merchant",
        "addresses": [],
        "store_name": "川味小馆",
        "store_description": "主打川菜、盖饭和家常套餐。"
    },
    {
        "username": "merchant2",
        "password": "merchant123",
        "phone": "",
        "role": "merchant",
        "addresses": [],
        "store_name": "轻食能量站",
        "store_description": "轻食沙拉、三明治与健康套餐。"
    },
    {
        "username": "admin",
        "password": "admin123456",
        "phone": "",
        "role": "admin",
        "addresses": []
    }
]

DEFAULT_STORE_VISUALS = {
    "avatar_url": "/static/store-avatar-default.svg",
    "cover_image_url": "/static/store-cover-default.svg"
}

# 数据加载和保存函数
def load_data():
    """从 MySQL 加载数据；若数据库暂不可用则回退默认数据。"""
    return load_mysql_data(DEFAULT_DATA)

def save_data(data):
    """将当前业务数据整体写入 MySQL。"""
    save_mysql_data(data)

def get_all_data():
    """获取当前所有数据。"""
    return load_data()

# 初始化 MySQL 存储，并在首次启动时自动迁移旧 JSON 数据
try:
    init_mysql_database(DEFAULT_DATA, legacy_json_path=DATA_FILE)
except Exception as exc:
    raise RuntimeError(
        "MySQL 初始化失败，请检查 MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DATABASE 配置，"
        "并确认 MySQL 服务已启动。"
        f"\n具体原因: {format_mysql_error(exc)}"
    ) from exc

# 加载数据
app_data = load_data()
stores = app_data.get('stores', DEFAULT_DATA['stores'])
categories = app_data.get('categories', DEFAULT_DATA['categories'])
menu = app_data.get('menu', DEFAULT_DATA['menu'])
combos = app_data.get('combos', DEFAULT_DATA['combos'])
orders = app_data.get('orders', DEFAULT_DATA['orders'])
reviews = app_data.get('reviews', DEFAULT_DATA['reviews'])
users = app_data.get('users', DEFAULT_DATA['users'])
ai_conversations = app_data.get('ai_conversations', DEFAULT_DATA['ai_conversations'])
counters = app_data.get('counters', DEFAULT_DATA['counters'])

next_order_id = counters.get('next_order_id', 1)
next_menu_id = counters.get('next_menu_id', 6)
next_category_id = counters.get('next_category_id', 5)
next_combo_id = counters.get('next_combo_id', 2)
next_user_id = counters.get('next_user_id', 1)
next_store_id = counters.get('next_store_id', 1)
next_review_id = counters.get('next_review_id', 1)

user_sessions = {}  # session_id -> {"user_id": int, "role": str}

ACTIVE_RECORD_STATUSES = ("active", "inactive")
MERCHANT_ORDER_STATUSES = ("已接单", "制作中", "配送中", "已完成", "已取消")

def refresh_runtime_data_from_disk(force=False):
    global app_data, stores, categories, menu, combos, orders, reviews, users, ai_conversations, counters
    global next_order_id, next_menu_id, next_category_id, next_combo_id, next_user_id, next_store_id, next_review_id

    latest_data = load_data()
    app_data = latest_data
    stores = latest_data.get('stores', DEFAULT_DATA['stores'])
    categories = latest_data.get('categories', DEFAULT_DATA['categories'])
    menu = latest_data.get('menu', DEFAULT_DATA['menu'])
    combos = latest_data.get('combos', DEFAULT_DATA['combos'])
    orders = latest_data.get('orders', DEFAULT_DATA['orders'])
    reviews = latest_data.get('reviews', DEFAULT_DATA['reviews'])
    users = latest_data.get('users', DEFAULT_DATA['users'])
    ai_conversations = latest_data.get('ai_conversations', DEFAULT_DATA['ai_conversations'])
    counters = latest_data.get('counters', DEFAULT_DATA['counters'])

    next_order_id = counters.get('next_order_id', 1)
    next_menu_id = counters.get('next_menu_id', 6)
    next_category_id = counters.get('next_category_id', 5)
    next_combo_id = counters.get('next_combo_id', 2)
    next_user_id = counters.get('next_user_id', 1)
    next_store_id = counters.get('next_store_id', 1)
    next_review_id = counters.get('next_review_id', 1)
    return True

@app.before_request
def sync_runtime_data_before_request():
    if request.path.startswith('/static/'):
        return None
    refresh_runtime_data_from_disk()
    return None

def get_store_by_id(store_id):
    return next((store for store in stores if store.get('id') == store_id), None)

def get_store_by_owner_user_id(user_id):
    return next((store for store in stores if store.get('owner_user_id') == user_id), None)

def calculate_store_monthly_sales(store_id):
    if not store_id:
        return 0
    current_month = datetime.now().strftime("%Y-%m")
    count = 0
    for order in orders:
        if order.get("store_id") != store_id or order.get("status") == "已取消":
            continue
        created_at = order.get("created_at", "")
        if isinstance(created_at, str) and created_at.startswith(current_month):
            count += 1
    return count

def serialize_store(store):
    if not store:
        return None
    store_id = store.get("id")
    return {
        "id": store_id,
        "name": store.get("name"),
        "description": store.get("description", ""),
        "owner_user_id": store.get("owner_user_id"),
        "owner_username": next((user.get("username") for user in users if user.get("id") == store.get("owner_user_id")), ""),
        "status": store.get("status", "active"),
        "avatar_url": store.get("avatar_url", DEFAULT_STORE_VISUALS["avatar_url"]),
        "cover_image_url": store.get("cover_image_url", DEFAULT_STORE_VISUALS["cover_image_url"]),
        "business_status": store.get("business_status", "营业中"),
        "business_hours": store.get("business_hours", "09:00-22:00"),
        "rating": float(store.get("rating", 4.8)),
        "monthly_sales": calculate_store_monthly_sales(store_id),
        "delivery_fee": float(store.get("delivery_fee", 4.0)),
        "min_order_amount": float(store.get("min_order_amount", 20.0)),
        "announcement": store.get("announcement", "欢迎光临本店，祝您用餐愉快。"),
        "created_at": store.get("created_at", ""),
        "menu_count": len([item for item in menu if item.get("store_id") == store_id]),
        "combo_count": len([combo for combo in combos if combo.get("store_id") == store_id]),
        "completed_order_count": len([order for order in orders if order.get("store_id") == store_id and order.get("status") == "已完成"]),
        "pending_order_count": len([order for order in orders if order.get("store_id") == store_id and order.get("status") == "已接单"]),
        "total_revenue": round(sum(float(order.get("total", 0)) for order in orders if order.get("store_id") == store_id and order.get("status") == "已完成"), 2)
    }

def get_user_store(user):
    if not user:
        return None
    store_id = user.get("store_id")
    if store_id:
        return get_store_by_id(store_id)
    return get_store_by_owner_user_id(user.get("id"))

def create_store_for_user(user, store_name=None, description=None):
    global next_store_id
    existing_store = get_user_store(user)
    if existing_store:
        if not user.get("store_id"):
            user["store_id"] = existing_store["id"]
        return existing_store

    store = {
        "id": next_store_id,
        "owner_user_id": user["id"],
        "name": store_name or user.get("store_name") or f"{user['username']}店铺",
        "description": description or user.get("store_description", ""),
        "status": "active",
        "avatar_url": DEFAULT_STORE_VISUALS["avatar_url"],
        "cover_image_url": DEFAULT_STORE_VISUALS["cover_image_url"],
        "business_status": "营业中",
        "business_hours": "09:00-22:00",
        "rating": 4.8,
        "delivery_fee": 4.0,
        "min_order_amount": 20.0,
        "announcement": "欢迎光临本店，祝您用餐愉快。",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    stores.append(store)
    user["store_id"] = next_store_id
    next_store_id += 1
    return store

def get_visible_stores():
    return [serialize_store(store) for store in stores if store.get("status", "active") == "active"]

def get_store_id_for_request(user, allow_all_for_admin=False):
    role = user.get('role', 'customer')
    requested_store_id = request.args.get('store_id', type=int)

    if role == 'merchant':
        store = get_user_store(user)
        return store.get('id') if store else None

    if role == 'customer':
        if request.method == 'GET':
            return requested_store_id
        body = request.get_json(silent=True) or {}
        return body.get('store_id')

    if role == 'admin':
        if allow_all_for_admin and not requested_store_id:
            return None
        return requested_store_id

    return None

def filter_records_by_store(records, store_id):
    if store_id is None:
        return list(records)
    return [record for record in records if record.get('store_id') == store_id]

def filter_active_records(records):
    return [record for record in records if record.get('status', 'active') == 'active']

def normalize_users():
    """补齐历史数据中的用户角色字段。"""
    changed = False
    for user in users:
        if not user.get('role'):
            user['role'] = 'customer'
            changed = True
        if 'addresses' not in user:
            user['addresses'] = []
            changed = True
        if 'phone' not in user:
            user['phone'] = ''
            changed = True
        if 'display_name' not in user:
            user['display_name'] = ''
            changed = True
        if 'email' not in user:
            user['email'] = ''
            changed = True
        if 'gender' not in user:
            user['gender'] = ''
            changed = True
        if 'birthday' not in user:
            user['birthday'] = ''
            changed = True
        if 'bio' not in user:
            user['bio'] = ''
            changed = True
        if 'account_status' not in user:
            user['account_status'] = 'active'
            changed = True
        if 'risk_status' not in user:
            user['risk_status'] = 'normal'
            changed = True
        if 'admin_note' not in user:
            user['admin_note'] = ''
            changed = True
        if 'favorite_store_ids' not in user:
            user['favorite_store_ids'] = []
            changed = True
        if 'favorite_menu_ids' not in user:
            user['favorite_menu_ids'] = []
            changed = True
        if 'recent_views' not in user:
            user['recent_views'] = []
            changed = True
        if user.get('role') == 'merchant':
            if 'store_name' not in user:
                user['store_name'] = f"{user.get('username', '商家')}店铺"
                changed = True
            if 'store_description' not in user:
                user['store_description'] = ''
                changed = True
    return changed

def normalize_stores_and_relations():
    global next_store_id, next_category_id, next_menu_id, next_combo_id
    changed = False

    merchant_users = [user for user in users if user.get('role') == 'merchant']
    for user in merchant_users:
        existing_store = get_user_store(user)
        if not existing_store:
            create_store_for_user(user)
            changed = True
        elif user.get("store_id") != existing_store.get("id"):
            user["store_id"] = existing_store.get("id")
            changed = True

    for user in merchant_users:
        store = get_user_store(user)
        if not store:
            continue
        if user.get("username") == "merchant":
            defaults = {
                "name": "川味小馆",
                "description": "主打川菜、盖饭和家常套餐。",
                "business_hours": "10:00-22:30",
                "rating": 4.9,
                "delivery_fee": 3.5,
                "min_order_amount": 18.0,
                "announcement": "招牌麻辣香锅和家庭套餐限时热销中。"
            }
        elif user.get("username") == "merchant2":
            defaults = {
                "name": "轻食能量站",
                "description": "轻食沙拉、三明治与健康套餐。",
                "business_hours": "08:30-20:30",
                "rating": 4.7,
                "delivery_fee": 2.0,
                "min_order_amount": 15.0,
                "announcement": "工作日午餐高峰请提前下单，轻食套餐可减脂搭配。"
            }
        else:
            defaults = {
                "name": user.get("store_name") or store.get("name"),
                "description": user.get("store_description", ""),
                "business_hours": "09:00-21:30",
                "rating": 4.8,
                "delivery_fee": 4.0,
                "min_order_amount": 20.0,
                "announcement": "欢迎光临本店，更多优惠活动持续上线。"
            }
        for key, value in defaults.items():
            if store.get(key) != value and (key in ("name", "description") and user.get("username") in ("merchant", "merchant2") or store.get(key) in (None, "", 4.8, 4.0, 20.0, "09:00-22:00", "欢迎光临本店，祝您用餐愉快。")):
                store[key] = value
                changed = True

    primary_store = get_user_store(merchant_users[0]) if merchant_users else None
    primary_store_id = primary_store.get("id") if primary_store else None

    for category in categories:
        if not category.get('store_id') and primary_store_id:
            category['store_id'] = primary_store_id
            changed = True
        if category.get('status') not in ACTIVE_RECORD_STATUSES:
            category['status'] = 'active'
            changed = True

    for item in menu:
        if not item.get('store_id'):
            if item.get('category_id'):
                category = next((cat for cat in categories if cat.get('id') == item.get('category_id')), None)
                if category and category.get('store_id'):
                    item['store_id'] = category.get('store_id')
                elif primary_store_id:
                    item['store_id'] = primary_store_id
            elif primary_store_id:
                item['store_id'] = primary_store_id
            changed = True
        if item.get('status') not in ACTIVE_RECORD_STATUSES:
            item['status'] = 'active'
            changed = True

    for combo in combos:
        if not combo.get('store_id'):
            first_item_id = (combo.get('items') or [None])[0]
            combo_item = next((item for item in menu if item.get('id') == first_item_id), None)
            combo['store_id'] = combo_item.get('store_id') if combo_item else primary_store_id
            changed = True
        if combo.get('status') not in ACTIVE_RECORD_STATUSES:
            combo['status'] = 'active'
            changed = True

    for order in orders:
        if not order.get('store_id'):
            first_item_id = (order.get('items') or [{}])[0].get('id')
            first_menu_item = next((item for item in menu if item.get('id') == first_item_id), None)
            if first_menu_item:
                order['store_id'] = first_menu_item.get('store_id')
            elif primary_store_id:
                order['store_id'] = primary_store_id
            changed = True
        if order.get('store_id') and not order.get('store_name'):
            store = get_store_by_id(order.get('store_id'))
            if store:
                order['store_name'] = store.get('name')
                changed = True
        if order.get('status') not in MERCHANT_ORDER_STATUSES:
            order['status'] = '已接单'
            changed = True

    for store in stores:
        if store.get("status") not in ("active", "inactive"):
            store["status"] = "active"
            changed = True
        if "avatar_url" not in store:
            store["avatar_url"] = DEFAULT_STORE_VISUALS["avatar_url"]
            changed = True
        if "cover_image_url" not in store:
            store["cover_image_url"] = DEFAULT_STORE_VISUALS["cover_image_url"]
            changed = True
        if "business_status" not in store:
            store["business_status"] = "营业中"
            changed = True
        if "business_hours" not in store:
            store["business_hours"] = "09:00-22:00"
            changed = True
        if "rating" not in store:
            store["rating"] = 4.8
            changed = True
        if "delivery_fee" not in store:
            store["delivery_fee"] = 4.0
            changed = True
        if "min_order_amount" not in store:
            store["min_order_amount"] = 20.0
            changed = True
        if "announcement" not in store:
            store["announcement"] = "欢迎光临本店，祝您用餐愉快。"
            changed = True

    if len(stores) >= 2:
        for store in stores:
            if any(category.get('store_id') == store.get('id') for category in categories):
                continue

            store_categories = [
                {"id": next_category_id, "name": "沙拉轻食", "store_id": store["id"]},
                {"id": next_category_id + 1, "name": "能量主食", "store_id": store["id"], "status": "active"},
                {"id": next_category_id + 2, "name": "饮品", "store_id": store["id"], "status": "active"}
            ]
            store_categories[0]["status"] = "active"
            categories.extend(store_categories)
            next_category_id += 3

            store_menu = [
                {
                    "id": next_menu_id,
                    "name": "鸡胸肉凯撒沙拉",
                    "description": "高蛋白低负担，适合轻食午餐。",
                    "price": 26.0,
                    "category_id": store_categories[0]["id"],
                    "store_id": store["id"],
                    "image": None,
                    "status": "active"
                },
                {
                    "id": next_menu_id + 1,
                    "name": "牛油果鸡肉三明治",
                    "description": "口感清爽，适合工作日快速补能。",
                    "price": 24.0,
                    "category_id": store_categories[1]["id"],
                    "store_id": store["id"],
                    "image": None,
                    "status": "active"
                },
                {
                    "id": next_menu_id + 2,
                    "name": "鲜榨橙汁",
                    "description": "现榨果饮，清新解腻。",
                    "price": 12.0,
                    "category_id": store_categories[2]["id"],
                    "store_id": store["id"],
                    "image": None,
                    "status": "active"
                }
            ]
            menu.extend(store_menu)
            next_menu_id += 3

            combos.append({
                "id": next_combo_id,
                "name": f"{store['name']}双人轻食套餐",
                "description": "适合双人轻食简餐搭配。",
                "price": 58.0,
                "items": [store_menu[0]["id"], store_menu[1]["id"], store_menu[2]["id"]],
                "discount": 0.92,
                "store_id": store["id"],
                "status": "active"
            })
            next_combo_id += 1
            changed = True

    return changed

def ensure_default_accounts():
    """确保系统内置商家和管理员账号存在。"""
    global next_user_id
    changed = False
    for account in DEFAULT_ACCOUNTS:
        exists = next((u for u in users if u.get('username') == account['username']), None)
        if exists:
            if exists.get('role') != account['role']:
                exists['role'] = account['role']
                changed = True
            continue

        user = {
            "id": next_user_id,
            "username": account['username'],
            "password": account['password'],
            "phone": account['phone'],
            "role": account['role'],
            "addresses": account['addresses'],
            "store_name": account.get('store_name', ''),
            "store_description": account.get('store_description', ''),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        users.append(user)
        next_user_id += 1
        changed = True
    return changed

def create_session(user):
    session_id = f"session_{user['id']}_{datetime.now().timestamp()}"
    user_sessions[session_id] = {
        "user_id": user['id'],
        "role": user.get('role', 'customer')
    }
    return session_id

def get_request_port():
    host = (request.host or "").strip()
    if ":" in host:
        try:
            return int(host.rsplit(":", 1)[1])
        except ValueError:
            pass
    try:
        return int(request.environ.get("SERVER_PORT", PORTAL_PORTS["customer"]))
    except (TypeError, ValueError):
        return PORTAL_PORTS["customer"]

def get_request_hostname():
    host = (request.host or "").strip()
    if host.startswith("[") and "]" in host:
        return host.split("]")[0] + "]"
    if ":" in host:
        return host.rsplit(":", 1)[0]
    return host or "127.0.0.1"

def get_active_portal_role():
    request_port = get_request_port()
    for role, port in PORTAL_PORTS.items():
        if port == request_port:
            return role
    return "customer"

def build_portal_url(role, path="/"):
    hostname = get_request_hostname()
    scheme = request.scheme or "http"
    port = PORTAL_PORTS.get(role, PORTAL_PORTS["customer"])
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{scheme}://{hostname}:{port}{normalized_path}"

def get_portal_navigation_urls():
    return {
        "customer_url": build_portal_url("customer", "/"),
        "merchant_url": build_portal_url("merchant", "/"),
        "admin_url": build_portal_url("admin", "/"),
        "chat_url": build_portal_url(get_active_portal_role(), "/chat")
    }

def get_session_cookie_name(role):
    return SESSION_COOKIE_NAMES.get(role, SESSION_COOKIE_NAMES["customer"])

def get_user_by_portal_cookie(role):
    session_id = request.cookies.get(get_session_cookie_name(role), "").strip()
    if not session_id:
        return None

    session_payload = get_session_payload(session_id)
    if not session_payload:
        return None

    user = next((u for u in users if u.get("id") == session_payload.get("user_id")), None)
    if not user:
        return None

    if user.get("account_status", "active") != "active":
        return None

    if user.get("role", "customer") != role:
        return None
    return user

def build_portal_response(role):
    user = get_user_by_portal_cookie(role)
    if not user:
        return redirect("/login")

    template_map = {
        "customer": "index.html",
        "merchant": "merchant.html",
        "admin": "admin.html"
    }
    return render_template(
        template_map[role],
        current_role=role,
        current_user=serialize_user(user),
        **get_portal_navigation_urls(),
        **get_cross_portal_feature_urls()
    )

def get_cross_portal_feature_urls():
    return {
        "customer_chat_url": build_portal_url("customer", "/chat"),
        "customer_order_assistant_url": build_portal_url("customer", "/smart-order"),
        "merchant_analysis_url": build_portal_url("merchant", "/data-analysis")
    }

def render_portal_template(role, template_name, **context):
    return render_template(
        template_name,
        current_role=role,
        current_user=serialize_user(get_user_by_portal_cookie(role)),
        **get_portal_navigation_urls(),
        **get_cross_portal_feature_urls(),
        **context
    )

def require_portal_page_access(role):
    if get_active_portal_role() != role:
        return None, redirect(build_portal_url(role, request.path))

    user = get_user_by_portal_cookie(role)
    if not user:
        return None, redirect(build_portal_url(role, "/login"))
    return user, None

def with_session_cookie(response, role, session_id):
    response.set_cookie(
        get_session_cookie_name(role),
        session_id,
        httponly=True,
        samesite="Lax"
    )
    return response

def get_session_payload(session_id):
    if not session_id:
        return None
    payload = user_sessions.get(session_id)
    if isinstance(payload, int):
        return {"user_id": payload, "role": "customer"}
    return payload

def mark_service_metric(service_name, success=True):
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if service_name == 'ai_chat':
        SERVICE_MONITOR["ai_chat_requests"] += 1
        SERVICE_MONITOR["last_ai_chat_at"] = now_text
        if not success:
            SERVICE_MONITOR["ai_chat_failures"] += 1
    elif service_name == 'smart_order':
        SERVICE_MONITOR["smart_order_requests"] += 1
        SERVICE_MONITOR["last_smart_order_at"] = now_text
        if not success:
            SERVICE_MONITOR["smart_order_failures"] += 1
    elif service_name == 'data_analysis':
        SERVICE_MONITOR["data_analysis_requests"] += 1
        SERVICE_MONITOR["last_data_analysis_at"] = now_text
        if not success:
            SERVICE_MONITOR["data_analysis_failures"] += 1

def get_authenticated_user(required_roles=None):
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        active_role = get_active_portal_role()
        session_id = request.cookies.get(get_session_cookie_name(active_role), "").strip()
    session_payload = get_session_payload(session_id)
    if not session_payload:
        return None, jsonify({"error": "未登录。"}), 401

    user = next((u for u in users if u.get('id') == session_payload.get('user_id')), None)
    if not user:
        return None, jsonify({"error": "用户不存在。"}), 404

    if user.get('account_status', 'active') != 'active':
        return None, jsonify({"error": "当前账户已被限制使用。"}), 403

    role = user.get('role', 'customer')
    if required_roles and role not in required_roles:
        return None, jsonify({"error": "无权限访问该资源。"}), 403

    return user, None, None

def serialize_user(user):
    store = get_user_store(user)
    return {
        "id": user['id'],
        "username": user['username'],
        "phone": user.get('phone', ''),
        "display_name": user.get('display_name', ''),
        "email": user.get('email', ''),
        "gender": user.get('gender', ''),
        "birthday": user.get('birthday', ''),
        "bio": user.get('bio', ''),
        "role": user.get('role', 'customer'),
        "role_label": ROLE_LABELS.get(user.get('role', 'customer'), user.get('role', 'customer')),
        "account_status": user.get('account_status', 'active'),
        "risk_status": user.get('risk_status', 'normal'),
        "admin_note": user.get('admin_note', ''),
        "addresses": user.get('addresses', []),
        "created_at": user.get('created_at', ''),
        "favorite_store_ids": user.get('favorite_store_ids', []),
        "favorite_menu_ids": user.get('favorite_menu_ids', []),
        "store_id": store.get('id') if store else None,
        "store_name": store.get('name') if store else user.get('store_name', '')
    }

def get_review_for_order(order_id):
    return next((review for review in reviews if review.get('order_id') == order_id), None)

def serialize_recent_view(view):
    view_type = view.get('type')
    if view_type == 'store':
        store = get_store_by_id(view.get('store_id'))
        return {
            "type": "store",
            "store_id": view.get('store_id'),
            "title": store.get('name') if store else view.get('title', '店铺'),
            "subtitle": store.get('description', '') if store else '',
            "image": store.get('cover_image_url') if store else '',
            "viewed_at": view.get('viewed_at', '')
        }
    if view_type == 'item':
        item = next((menu_item for menu_item in menu if menu_item.get('id') == view.get('item_id')), None)
        store = get_store_by_id(view.get('store_id'))
        return {
            "type": "item",
            "store_id": view.get('store_id'),
            "item_id": view.get('item_id'),
            "title": item.get('name') if item else view.get('title', '菜品'),
            "subtitle": (store.get('name') if store else '') + (f" · {item.get('description', '')}" if item else ''),
            "image": item.get('image') if item else '',
            "viewed_at": view.get('viewed_at', '')
        }
    return view

def push_recent_view(user, view):
    recent_views = user.setdefault('recent_views', [])
    unique_key = (view.get('type'), view.get('store_id'), view.get('item_id'))
    recent_views[:] = [
        existing for existing in recent_views
        if (existing.get('type'), existing.get('store_id'), existing.get('item_id')) != unique_key
    ]
    recent_views.insert(0, view)
    del recent_views[20:]

def serialize_order(order):
    review = get_review_for_order(order.get('id'))
    return {
        **order,
        "reviewed": bool(review),
        "review": review
    }

def get_portal_login_context(role):
    contexts = {
        "customer": {
            "role": "customer",
            "title": "客户端登录",
            "subtitle": "用户登录与注册",
            "portal_name": "客户端",
            "allow_register": True,
            "submit_label": "登录客户端",
            "register_label": "注册客户端账户",
            "target_path": "/",
            "register_path": "/login"
        },
        "merchant": {
            "role": "merchant",
            "title": "商家端登录",
            "subtitle": "商家用户登录与注册",
            "portal_name": "商家端",
            "allow_register": True,
            "submit_label": "登录商家端",
            "register_label": "注册商家账户",
            "target_path": "/",
            "register_path": "/login"
        },
        "admin": {
            "role": "admin",
            "title": "后台管理员登录",
            "subtitle": "仅管理员可访问后台管理端",
            "portal_name": "后台管理端",
            "allow_register": False,
            "submit_label": "登录后台",
            "register_label": "",
            "target_path": "/",
            "register_path": "/login"
        }
    }
    context = contexts.get(role, contexts["customer"]).copy()
    context.update(get_portal_navigation_urls())
    return context

def update_counters():
    """更新计数器"""
    global next_order_id, next_menu_id, next_category_id, next_combo_id, next_user_id, next_store_id, next_review_id, counters
    counters = {
        'next_order_id': next_order_id,
        'next_menu_id': next_menu_id,
        'next_category_id': next_category_id,
        'next_combo_id': next_combo_id,
        'next_user_id': next_user_id,
        'next_store_id': next_store_id,
        'next_review_id': next_review_id
    }

def persist_data():
    """持久化所有数据到文件"""
    update_counters()
    data = {
        'stores': stores,
        'categories': categories,
        'menu': menu,
        'combos': combos,
        'orders': orders,
        'reviews': reviews,
        'users': users,
        'ai_conversations': ai_conversations,
        'counters': counters
    }
    save_data(data)

users_normalized = normalize_users()
default_accounts_ready = ensure_default_accounts()
stores_normalized = normalize_stores_and_relations()
if users_normalized or default_accounts_ready or stores_normalized:
    persist_data()

@app.route('/')
def index():
    return build_portal_response(get_active_portal_role())

@app.route('/login')
def login():
    active_role = get_active_portal_role()
    if get_user_by_portal_cookie(active_role):
        return redirect("/")
    return render_template('login.html', **get_portal_login_context(active_role))

@app.route('/merchant/login')
def merchant_login():
    return redirect(build_portal_url("merchant", "/login"))

@app.route('/merchant')
def merchant():
    return redirect(build_portal_url("merchant", "/"))

@app.route('/admin/login')
def admin_login():
    return redirect(build_portal_url("admin", "/login"))

@app.route('/admin')
def admin():
    return redirect(build_portal_url("admin", "/"))

@app.route('/chat')
def chat():
    user, redirect_response = require_portal_page_access('customer')
    if redirect_response:
        return redirect_response
    return render_portal_template('customer', 'chat.html')

@app.route('/smart-order')
def smart_order():
    user, redirect_response = require_portal_page_access('customer')
    if redirect_response:
        return redirect_response
    return render_portal_template('customer', 'smart_order.html')

@app.route('/data-analysis')
def data_analysis():
    user, redirect_response = require_portal_page_access('merchant')
    if redirect_response:
        return redirect_response
    return render_portal_template('merchant', 'data_analysis.html')

# 分类管理API
@app.route('/api/categories', methods=['GET'])
def get_categories():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer', 'merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user, allow_all_for_admin=True)
    if user.get('role') == 'customer' and not store_id:
        return jsonify({"error": "请选择店铺后再查看分类。"}), 400
    scoped_categories = filter_records_by_store(categories, store_id)
    if user.get('role') == 'customer':
        scoped_categories = filter_active_records(scoped_categories)
    return jsonify({"categories": scoped_categories})

@app.route('/api/stores', methods=['GET'])
def get_stores():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer', 'merchant', 'admin'])
    if error_response:
        return error_response, status_code

    if user.get('role') == 'merchant':
        return jsonify({"stores": [serialize_store(get_user_store(user))]})
    if user.get('role') == 'admin':
        return jsonify({"stores": [serialize_store(store) for store in stores]})
    return jsonify({"stores": get_visible_stores()})

@app.route('/api/stores/<int:store_id>', methods=['PUT'])
def update_store(store_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code

    store = get_store_by_id(store_id)
    if not store:
        return jsonify({"error": "未找到该店铺。"}), 404

    if user.get('role') == 'merchant':
        merchant_store = get_user_store(user)
        if not merchant_store or merchant_store.get('id') != store_id:
            return jsonify({"error": "无权限编辑该店铺。"}), 403

    data = request.get_json() or {}

    store_name = str(data.get('name', '')).strip()
    description = str(data.get('description', '')).strip()
    avatar_url = data.get('avatar_url') or DEFAULT_STORE_VISUALS["avatar_url"]
    cover_image_url = data.get('cover_image_url') or DEFAULT_STORE_VISUALS["cover_image_url"]
    business_status = str(data.get('business_status', '营业中')).strip() or '营业中'
    business_hours = str(data.get('business_hours', '09:00-22:00')).strip() or '09:00-22:00'
    announcement = str(data.get('announcement', '')).strip() or '欢迎光临本店，祝您用餐愉快。'
    status = str(data.get('status', store.get('status', 'active'))).strip() or 'active'

    if not store_name:
        return jsonify({"error": "店铺名称不能为空。"}), 400
    if status not in ('active', 'inactive'):
        return jsonify({"error": "店铺状态不合法。"}), 400

    try:
        rating = float(data.get('rating', store.get('rating', 4.8)))
        delivery_fee = float(data.get('delivery_fee', store.get('delivery_fee', 4.0)))
        min_order_amount = float(data.get('min_order_amount', store.get('min_order_amount', 20.0)))
    except (TypeError, ValueError):
        return jsonify({"error": "评分、配送费和起送价必须是数字。"}), 400

    if rating < 0 or rating > 5:
        return jsonify({"error": "评分必须在 0 到 5 之间。"}), 400
    if delivery_fee < 0 or min_order_amount < 0:
        return jsonify({"error": "配送费和起送价不能为负数。"}), 400

    store['name'] = store_name
    store['description'] = description
    store['avatar_url'] = avatar_url
    store['cover_image_url'] = cover_image_url
    store['business_status'] = business_status
    store['business_hours'] = business_hours
    store['rating'] = rating
    store['delivery_fee'] = delivery_fee
    store['min_order_amount'] = min_order_amount
    store['announcement'] = announcement
    store['status'] = status

    owner_user = next((item for item in users if item.get('id') == store.get('owner_user_id')), None)
    if owner_user:
        owner_user['store_id'] = store['id']
        owner_user['store_name'] = store_name
        owner_user['store_description'] = description

    for order in orders:
        if order.get('store_id') == store['id']:
            order['store_name'] = store_name

    persist_data()
    return jsonify({"store": serialize_store(store)})

@app.route('/api/categories', methods=['POST'])
def add_category():
    global next_category_id
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user)
    if not store_id:
        return jsonify({"error": "当前商家店铺不存在。"}), 400
    data = request.get_json() or {}
    name = data.get('name', '').strip()

    if not name:
        return jsonify({"error": "分类名称不能为空。"}), 400

    category = {
        "id": next_category_id,
        "name": name,
        "store_id": store_id,
        "status": "active"
    }
    categories.append(category)
    next_category_id += 1
    persist_data()
    return jsonify({"category": category}), 201

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user)
    data = request.get_json() or {}
    category = next((c for c in categories if c['id'] == category_id and (store_id is None or c.get('store_id') == store_id)), None)
    if not category:
        return jsonify({"error": "未找到该分类。"}), 404

    name = data.get('name', '').strip()
    status = data.get('status', category.get('status', 'active'))
    if not name:
        return jsonify({"error": "分类名称不能为空。"}), 400
    if status not in ACTIVE_RECORD_STATUSES:
        return jsonify({"error": "分类状态不合法。"}), 400

    category['name'] = name
    category['status'] = status
    persist_data()
    return jsonify({"category": category})

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    global categories, menu
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user)
    category = next((c for c in categories if c['id'] == category_id and (store_id is None or c.get('store_id') == store_id)), None)
    if not category:
        return jsonify({"error": "未找到该分类。"}), 404

    # 检查是否有商品使用此分类
    if any(item['category_id'] == category_id and item.get('store_id') == category.get('store_id') for item in menu):
        return jsonify({"error": "该分类下有商品，无法删除。"}), 400

    categories = [c for c in categories if c['id'] != category_id]
    persist_data()
    return jsonify({"success": True})

# 商品管理API
@app.route('/api/menu', methods=['GET'])
def get_menu():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer', 'merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user, allow_all_for_admin=True)
    if user.get('role') == 'customer' and not store_id:
        return jsonify({"error": "请选择店铺后再查看菜品。"}), 400
    category_id = request.args.get('category_id', type=int)
    scoped_menu = filter_records_by_store(menu, store_id)
    if user.get('role') == 'customer':
        scoped_menu = filter_active_records(scoped_menu)
    if category_id:
        filtered_menu = [item for item in scoped_menu if item['category_id'] == category_id]
        return jsonify({"menu": filtered_menu})
    return jsonify({"menu": scoped_menu})

@app.route('/api/menu', methods=['POST'])
def add_menu_item():
    global next_menu_id
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user)
    if not store_id:
        return jsonify({"error": "当前商家店铺不存在。"}), 400
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    category_id = data.get('category_id')
    image = data.get('image')
    status = data.get('status', 'active')

    if not name:
        return jsonify({"error": "商品名称不能为空。"}), 400
    if price is None:
        return jsonify({"error": "价格不能为空。"}), 400
    if category_id is None:
        return jsonify({"error": "请选择分类。"}), 400

    try:
        price = float(price)
        category_id = int(category_id)
    except (TypeError, ValueError):
        return jsonify({"error": "请输入合法的价格和分类。"}), 400

    if status not in ACTIVE_RECORD_STATUSES:
        return jsonify({"error": "商品状态不合法。"}), 400

    if not any(cat['id'] == category_id and cat.get('store_id') == store_id for cat in categories):
        return jsonify({"error": "选择的分类不存在。"}), 400

    item = {
        "id": next_menu_id,
        "name": name,
        "description": description,
        "price": round(price, 2),
        "category_id": category_id,
        "store_id": store_id,
        "image": image,
        "status": status
    }
    menu.append(item)
    next_menu_id += 1
    persist_data()
    return jsonify({"item": item}), 201

@app.route('/api/menu/<int:item_id>', methods=['PUT'])
def update_menu_item(item_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user)
    data = request.get_json() or {}
    item = next((m for m in menu if m['id'] == item_id and (store_id is None or m.get('store_id') == store_id)), None)
    if not item:
        return jsonify({"error": "未找到该商品。"}), 404

    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    category_id = data.get('category_id')
    image = data.get('image')
    status = data.get('status', item.get('status', 'active'))

    if not name:
        return jsonify({"error": "商品名称不能为空。"}), 400
    if price is None:
        return jsonify({"error": "价格不能为空。"}), 400
    if category_id is None:
        return jsonify({"error": "请选择分类。"}), 400

    try:
        price = float(price)
        category_id = int(category_id)
    except (TypeError, ValueError):
        return jsonify({"error": "请输入合法的价格和分类。"}), 400

    if status not in ACTIVE_RECORD_STATUSES:
        return jsonify({"error": "商品状态不合法。"}), 400

    if not any(cat['id'] == category_id and cat.get('store_id') == item.get('store_id') for cat in categories):
        return jsonify({"error": "选择的分类不存在。"}), 400

    item['name'] = name
    item['description'] = description
    item['price'] = round(price, 2)
    item['category_id'] = category_id
    item['status'] = status
    if image:
        item['image'] = image
    item['price'] = round(price, 2)
    item['category_id'] = category_id
    persist_data()
    return jsonify({"item": item})

@app.route('/api/menu/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    global menu
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user)
    item = next((m for m in menu if m['id'] == item_id and (store_id is None or m.get('store_id') == store_id)), None)
    if not item:
        return jsonify({"error": "未找到该商品。"}), 404
    menu = [m for m in menu if m['id'] != item_id]
    persist_data()
    return jsonify({"success": True})

# 套餐管理API
@app.route('/api/combos', methods=['GET'])
def get_combos():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer', 'merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user, allow_all_for_admin=True)
    if user.get('role') == 'customer' and not store_id:
        return jsonify({"error": "请选择店铺后再查看套餐。"}), 400
    scoped_combos = filter_records_by_store(combos, store_id)
    if user.get('role') == 'customer':
        scoped_combos = filter_active_records(scoped_combos)
    return jsonify({"combos": scoped_combos})

@app.route('/api/combos', methods=['POST'])
def add_combo():
    global next_combo_id
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user)
    if not store_id:
        return jsonify({"error": "当前商家店铺不存在。"}), 400
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    items = data.get('items', [])
    discount = data.get('discount', 1.0)
    status = data.get('status', 'active')

    if not name:
        return jsonify({"error": "套餐名称不能为空。"}), 400
    if price is None:
        return jsonify({"error": "价格不能为空。"}), 400
    if not items:
        return jsonify({"error": "请选择套餐商品。"}), 400

    try:
        price = float(price)
        discount = float(discount)
        items = [int(item) for item in items]
    except (TypeError, ValueError):
        return jsonify({"error": "请输入合法的价格和商品ID。"}), 400

    if status not in ACTIVE_RECORD_STATUSES:
        return jsonify({"error": "套餐状态不合法。"}), 400

    # 验证商品存在
    for item_id in items:
        if not any(m['id'] == item_id and m.get('store_id') == store_id for m in menu):
            return jsonify({"error": f"商品ID {item_id} 不存在。"}), 400

    combo = {
        "id": next_combo_id,
        "name": name,
        "description": description,
        "price": round(price, 2),
        "items": items,
        "discount": discount,
        "store_id": store_id,
        "status": status
    }
    combos.append(combo)
    next_combo_id += 1
    persist_data()
    return jsonify({"combo": combo}), 201

@app.route('/api/combos/<int:combo_id>', methods=['PUT'])
def update_combo(combo_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user)
    data = request.get_json() or {}
    combo = next((c for c in combos if c['id'] == combo_id and (store_id is None or c.get('store_id') == store_id)), None)
    if not combo:
        return jsonify({"error": "未找到该套餐。"}), 404

    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    items = data.get('items', [])
    discount = data.get('discount', 1.0)
    status = data.get('status', combo.get('status', 'active'))

    if not name:
        return jsonify({"error": "套餐名称不能为空。"}), 400
    if price is None:
        return jsonify({"error": "价格不能为空。"}), 400
    if not items:
        return jsonify({"error": "请选择套餐商品。"}), 400

    try:
        price = float(price)
        discount = float(discount)
        items = [int(item) for item in items]
    except (TypeError, ValueError):
        return jsonify({"error": "请输入合法的价格和商品ID。"}), 400

    if status not in ACTIVE_RECORD_STATUSES:
        return jsonify({"error": "套餐状态不合法。"}), 400

    # 验证商品存在
    for item_id in items:
        if not any(m['id'] == item_id and m.get('store_id') == combo.get('store_id') for m in menu):
            return jsonify({"error": f"商品ID {item_id} 不存在。"}), 400

    combo['name'] = name
    combo['description'] = description
    combo['price'] = round(price, 2)
    combo['items'] = items
    combo['discount'] = discount
    combo['status'] = status
    persist_data()
    return jsonify({"combo": combo})

@app.route('/api/combos/<int:combo_id>', methods=['DELETE'])
def delete_combo(combo_id):
    global combos
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user)
    combo = next((c for c in combos if c['id'] == combo_id and (store_id is None or c.get('store_id') == store_id)), None)
    if not combo:
        return jsonify({"error": "未找到该套餐。"}), 404
    combos = [c for c in combos if c['id'] != combo_id]
    persist_data()
    return jsonify({"success": True})

# 工作台统计API
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    store_id = get_store_id_for_request(user, allow_all_for_admin=True)
    scoped_orders = filter_records_by_store(orders, store_id)
    scoped_menu = filter_records_by_store(menu, store_id)
    scoped_combos = filter_records_by_store(combos, store_id)
    total_orders = len(scoped_orders)
    total_revenue = sum(order['total'] for order in scoped_orders if order['status'] == '已完成')
    pending_orders = len([o for o in scoped_orders if o['status'] in ('已接单', '制作中', '配送中')])
    completed_orders = len([o for o in scoped_orders if o['status'] == '已完成'])
    cancelled_orders = len([o for o in scoped_orders if o['status'] == '已取消'])

    # 今日统计
    today = datetime.now().date()
    today_orders = [o for o in scoped_orders if datetime.strptime(o['created_at'], "%Y-%m-%d %H:%M:%S").date() == today]
    today_revenue = sum(o['total'] for o in today_orders if o['status'] == '已完成')

    return jsonify({
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "today_orders": len(today_orders),
        "today_revenue": round(today_revenue, 2),
        "menu_count": len(scoped_menu),
        "combo_count": len(scoped_combos)
    })

# 订单管理API
@app.route('/api/orders', methods=['GET'])
def get_orders():
    customer = request.args.get('customer', '').strip()
    user, error_response, status_code = get_authenticated_user(required_roles=['customer', 'merchant', 'admin'])
    if error_response:
        return error_response, status_code

    if user.get('role') == 'customer':
        target_customer = customer or user.get('username')
        filtered_orders = [serialize_order(o) for o in orders if o['customer'] == target_customer]
        return jsonify({"orders": filtered_orders})

    store_id = get_store_id_for_request(user, allow_all_for_admin=True)
    scoped_orders = filter_records_by_store(orders, store_id)
    if customer:
        filtered_orders = [serialize_order(o) for o in scoped_orders if o['customer'] == customer]
        return jsonify({"orders": filtered_orders})
    return jsonify({"orders": [serialize_order(order) for order in scoped_orders]})

@app.route('/api/order', methods=['POST'])
def create_order():
    global next_order_id
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code
    data = request.get_json() or {}
    customer = user.get('username')
    store_id = data.get('store_id')
    items = data.get('items', [])
    combo_id = data.get('combo_id')

    if not store_id:
        return jsonify({"error": "请选择店铺后再下单。"}), 400
    store = get_store_by_id(int(store_id))
    if not store:
        return jsonify({"error": "店铺不存在。"}), 404
    if not items and not combo_id:
        return jsonify({"error": "请选择至少一个商品或套餐。"}), 400

    order_items = []
    total = 0.0

    # 处理普通商品
    for item in items:
        menu_item = next((m for m in menu if m['id'] == item.get('id') and m.get('store_id') == int(store_id)), None)
        if not menu_item:
            continue
        quantity = max(1, int(item.get('quantity', 1)))
        subtotal = menu_item['price'] * quantity
        order_items.append({
            "id": menu_item['id'],
            "name": menu_item['name'],
            "price": menu_item['price'],
            "quantity": quantity,
            "subtotal": round(subtotal, 2),
            "type": "item"
        })
        total += subtotal

    # 处理套餐
    if combo_id:
        combo = next((c for c in combos if c['id'] == combo_id and c.get('store_id') == int(store_id)), None)
        if combo:
            combo_total = combo['price'] * combo['discount']
            order_items.append({
                "id": combo['id'],
                "name": combo['name'],
                "price": combo['price'],
                "quantity": 1,
                "subtotal": round(combo_total, 2),
                "type": "combo",
                "discount": combo['discount']
            })
            total += combo_total

    if not order_items:
        return jsonify({"error": "订单中没有有效商品。"}), 400

    order = {
        "id": next_order_id,
        "customer": customer,
        "store_id": int(store_id),
        "store_name": store.get('name'),
        "items": order_items,
        "total": round(total, 2),
        "status": "已接单",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    orders.append(order)
    next_order_id += 1
    persist_data()

    return jsonify({"order": order}), 201

@app.route('/api/order/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['customer', 'merchant', 'admin'])
    if error_response:
        return error_response, status_code
    order = next((o for o in orders if o['id'] == order_id), None)
    if not order:
        return jsonify({"error": "未找到该订单。"}), 404
    if user.get('role') == 'customer' and order.get('customer') != user.get('username'):
        return jsonify({"error": "无权取消该订单。"}), 403
    if user.get('role') == 'merchant':
        merchant_store = get_user_store(user)
        if not merchant_store or order.get('store_id') != merchant_store.get('id'):
            return jsonify({"error": "无权取消其他店铺订单。"}), 403
    if order['status'] == '已取消':
        return jsonify({"error": "订单已取消。"}), 400
    if order['status'] == '已完成':
        return jsonify({"error": "订单已完成，无法取消。"}), 400

    order['status'] = '已取消'
    persist_data()
    return jsonify({"order": order})

@app.route('/api/order/<int:order_id>/complete', methods=['POST'])
def complete_order(order_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    order = next((o for o in orders if o['id'] == order_id), None)
    if not order:
        return jsonify({"error": "未找到该订单。"}), 404
    if user.get('role') == 'merchant':
        merchant_store = get_user_store(user)
        if not merchant_store or order.get('store_id') != merchant_store.get('id'):
            return jsonify({"error": "无权处理其他店铺订单。"}), 403
    if order['status'] != '已接单':
        return jsonify({"error": "该订单无法标记为已完成。"}), 400

    order['status'] = '已完成'
    persist_data()
    return jsonify({"order": order})

@app.route('/api/order/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code
    order = next((o for o in orders if o['id'] == order_id), None)
    if not order:
        return jsonify({"error": "未找到该订单。"}), 404
    if user.get('role') == 'merchant':
        merchant_store = get_user_store(user)
        if not merchant_store or order.get('store_id') != merchant_store.get('id'):
            return jsonify({"error": "无权处理其他店铺订单。"}), 403

    data = request.get_json() or {}
    target_status = str(data.get('status', '')).strip()
    if target_status not in MERCHANT_ORDER_STATUSES:
        return jsonify({"error": "订单状态不合法。"}), 400

    current_status = order.get('status')
    allowed_transitions = {
        '已接单': {'制作中', '配送中', '已完成', '已取消'},
        '制作中': {'配送中', '已完成', '已取消'},
        '配送中': {'已完成'},
        '已完成': set(),
        '已取消': set()
    }

    if target_status == current_status:
        return jsonify({"order": order})
    if target_status not in allowed_transitions.get(current_status, set()):
        return jsonify({"error": f"订单当前状态为 {current_status}，无法更新为 {target_status}。"}), 400

    order['status'] = target_status
    persist_data()
    return jsonify({"order": order})

@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    favorite_store_ids = user.get('favorite_store_ids', [])
    favorite_menu_ids = user.get('favorite_menu_ids', [])
    favorite_stores = [serialize_store(store) for store in stores if store.get('id') in favorite_store_ids]
    favorite_items = [item for item in menu if item.get('id') in favorite_menu_ids]
    recent_views = [serialize_recent_view(view) for view in user.get('recent_views', [])]
    recent_orders = [serialize_order(order) for order in orders if order.get('customer') == user.get('username')]
    recent_orders = sorted(recent_orders, key=lambda order: order.get('id', 0), reverse=True)[:5]

    return jsonify({
        "favorite_store_ids": favorite_store_ids,
        "favorite_menu_ids": favorite_menu_ids,
        "stores": favorite_stores,
        "items": favorite_items,
        "recent_views": recent_views,
        "recent_orders": recent_orders
    })

@app.route('/api/favorites/stores/<int:store_id>/toggle', methods=['POST'])
def toggle_favorite_store(store_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code
    if not get_store_by_id(store_id):
        return jsonify({"error": "店铺不存在。"}), 404

    favorite_store_ids = user.setdefault('favorite_store_ids', [])
    if store_id in favorite_store_ids:
        favorite_store_ids.remove(store_id)
        action = 'removed'
    else:
        favorite_store_ids.append(store_id)
        action = 'added'
    persist_data()
    return jsonify({"success": True, "action": action, "favorite_store_ids": favorite_store_ids})

@app.route('/api/favorites/menu/<int:item_id>/toggle', methods=['POST'])
def toggle_favorite_menu(item_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code
    item = next((menu_item for menu_item in menu if menu_item.get('id') == item_id), None)
    if not item:
        return jsonify({"error": "菜品不存在。"}), 404

    favorite_menu_ids = user.setdefault('favorite_menu_ids', [])
    if item_id in favorite_menu_ids:
        favorite_menu_ids.remove(item_id)
        action = 'removed'
    else:
        favorite_menu_ids.append(item_id)
        action = 'added'
    persist_data()
    return jsonify({"success": True, "action": action, "favorite_menu_ids": favorite_menu_ids})

@app.route('/api/recent-views', methods=['POST'])
def add_recent_view():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    data = request.get_json() or {}
    view_type = data.get('type')
    store_id = data.get('store_id')
    item_id = data.get('item_id')

    if view_type not in ('store', 'item'):
        return jsonify({"error": "浏览记录类型不合法。"}), 400
    if not store_id:
        return jsonify({"error": "缺少店铺信息。"}), 400

    view = {
        "type": view_type,
        "store_id": int(store_id),
        "item_id": int(item_id) if item_id else None,
        "viewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    push_recent_view(user, view)
    persist_data()
    return jsonify({"success": True})

@app.route('/api/orders/<int:order_id>/reorder', methods=['POST'])
def reorder_order(order_id):
    global next_order_id
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    order = next((item for item in orders if item.get('id') == order_id and item.get('customer') == user.get('username')), None)
    if not order:
        return jsonify({"error": "订单不存在。"}), 404

    store_id = order.get('store_id')
    store = get_store_by_id(store_id)
    if not store or store.get('status') != 'active':
        return jsonify({"error": "当前店铺不可下单。"}), 400

    recreated_items = []
    total = 0.0
    for order_item in order.get('items', []):
        if order_item.get('type') == 'item':
            menu_item = next((item for item in menu if item.get('id') == order_item.get('id') and item.get('store_id') == store_id), None)
            if not menu_item:
                continue
            quantity = max(1, int(order_item.get('quantity', 1)))
            subtotal = float(menu_item.get('price', 0)) * quantity
            recreated_items.append({
                "id": menu_item['id'],
                "name": menu_item['name'],
                "price": menu_item['price'],
                "quantity": quantity,
                "subtotal": round(subtotal, 2),
                "type": "item"
            })
            total += subtotal
        elif order_item.get('type') == 'combo':
            combo = next((item for item in combos if item.get('id') == order_item.get('id') and item.get('store_id') == store_id), None)
            if not combo:
                continue
            subtotal = float(combo.get('price', 0)) * float(combo.get('discount', 1))
            recreated_items.append({
                "id": combo['id'],
                "name": combo['name'],
                "price": combo['price'],
                "quantity": 1,
                "subtotal": round(subtotal, 2),
                "type": "combo",
                "discount": combo.get('discount', 1)
            })
            total += subtotal

    if not recreated_items:
        return jsonify({"error": "原订单商品已下架，无法复购。"}), 400

    new_order = {
        "id": next_order_id,
        "customer": user.get('username'),
        "store_id": store_id,
        "store_name": store.get('name'),
        "items": recreated_items,
        "total": round(total, 2),
        "status": "已接单",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_order_id": order_id
    }
    orders.append(new_order)
    next_order_id += 1
    persist_data()
    return jsonify({"order": serialize_order(new_order)})

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    store_id = request.args.get('store_id', type=int)
    order_id = request.args.get('order_id', type=int)
    customer = request.args.get('customer', '').strip()
    filtered_reviews = reviews
    if store_id:
        filtered_reviews = [review for review in filtered_reviews if review.get('store_id') == store_id]
    if order_id:
        filtered_reviews = [review for review in filtered_reviews if review.get('order_id') == order_id]
    if customer:
        filtered_reviews = [review for review in filtered_reviews if review.get('customer') == customer]
    filtered_reviews = sorted(filtered_reviews, key=lambda review: review.get('id', 0), reverse=True)
    return jsonify({"reviews": filtered_reviews})

@app.route('/api/orders/<int:order_id>/review', methods=['POST'])
def create_review(order_id):
    global next_review_id
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    order = next((item for item in orders if item.get('id') == order_id and item.get('customer') == user.get('username')), None)
    if not order:
        return jsonify({"error": "订单不存在。"}), 404
    if order.get('status') != '已完成':
        return jsonify({"error": "仅已完成订单可评价。"}), 400
    if get_review_for_order(order_id):
        return jsonify({"error": "该订单已评价。"}), 400

    data = request.get_json() or {}
    try:
        rating = float(data.get('rating', 0))
        delivery_rating = float(data.get('delivery_rating', 0))
        packaging_rating = float(data.get('packaging_rating', 0))
        taste_rating = float(data.get('taste_rating', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "评分必须是数字。"}), 400

    content = str(data.get('content', '')).strip()
    image = data.get('image')
    if rating <= 0:
        return jsonify({"error": "请填写总体评分。"}), 400

    review = {
        "id": next_review_id,
        "order_id": order_id,
        "customer": user.get('username'),
        "store_id": order.get('store_id'),
        "store_name": order.get('store_name', ''),
        "rating": rating,
        "delivery_rating": delivery_rating,
        "packaging_rating": packaging_rating,
        "taste_rating": taste_rating,
        "content": content,
        "image": image,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    reviews.append(review)
    next_review_id += 1
    persist_data()
    return jsonify({"review": review}), 201

# 用户管理

@app.route('/api/users/register', methods=['POST'])
def register_user():
    global next_user_id
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    phone = data.get('phone', '').strip()
    role = data.get('role', 'customer').strip()

    if not username:
        return jsonify({"error": "用户名不能为空。"}), 400
    if not password:
        return jsonify({"error": "密码不能为空。"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少6个字符。"}), 400
    if role not in ('customer', 'merchant'):
        return jsonify({"error": "仅支持注册客户端或商家账户。"}), 400

    # 检查用户名是否已存在
    if any(u['username'] == username for u in users):
        return jsonify({"error": "用户名已存在。"}), 400

    user = {
        "id": next_user_id,
        "username": username,
        "password": password,
        "phone": phone,
        "display_name": "",
        "email": "",
        "gender": "",
        "birthday": "",
        "bio": "",
        "role": role,
        "account_status": "active",
        "risk_status": "normal",
        "admin_note": "",
        "addresses": [],
        "favorite_store_ids": [],
        "favorite_menu_ids": [],
        "recent_views": [],
        "store_name": f"{username}店铺" if role == 'merchant' else '',
        "store_description": '',
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    users.append(user)
    next_user_id += 1
    if role == 'merchant':
        create_store_for_user(user)
    persist_data()

    # 创建 session
    session_id = create_session(user)

    response = make_response(jsonify({
        "user": serialize_user(user),
        "session_id": session_id
    }), 201)
    return with_session_cookie(response, role, session_id)

@app.route('/api/users/login', methods=['POST'])
def login_user():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', '').strip()

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空。"}), 400

    user = next((u for u in users if u['username'] == username and u['password'] == password), None)
    if not user:
        return jsonify({"error": "用户名或密码错误。"}), 401
    if user.get('account_status', 'active') != 'active':
        return jsonify({"error": "当前账户已被禁用，请联系平台管理员。"}), 403
    if role and user.get('role', 'customer') != role:
        return jsonify({"error": "当前账号不属于该端口。"}), 403

    session_id = create_session(user)

    response = make_response(jsonify({
        "user": serialize_user(user),
        "session_id": session_id
    }), 200)
    return with_session_cookie(response, user.get('role', 'customer'), session_id)

@app.route('/api/users/logout', methods=['POST'])
def logout_user():
    data = request.get_json() or {}
    session_id = data.get('session_id')
    session_payload = get_session_payload(session_id)

    if session_id and session_id in user_sessions:
        del user_sessions[session_id]

    response = make_response(jsonify({"success": True}))
    cookie_roles = ['customer', 'merchant', 'admin']
    if session_payload and session_payload.get("role") in cookie_roles:
        cookie_roles = [session_payload.get("role")]
    for role in cookie_roles:
        response.delete_cookie(get_session_cookie_name(role))
    return response

@app.route('/api/users/session', methods=['GET'])
def get_user_session():
    session_id = request.headers.get('X-Session-ID')
    session_payload = get_session_payload(session_id)

    if not session_payload:
        return jsonify({"error": "未登录。"}), 401

    user = next((u for u in users if u['id'] == session_payload.get('user_id')), None)

    if not user:
        return jsonify({"error": "用户不存在。"}), 404
    if user.get('account_status', 'active') != 'active':
        return jsonify({"error": "当前账户已被限制使用。"}), 403

    return jsonify({
        "user": serialize_user(user),
        "session_id": session_id
    }), 200

@app.route('/api/users/profile', methods=['PUT'])
def update_user_profile():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    display_name = data.get('display_name', '').strip()
    email = data.get('email', '').strip()
    gender = data.get('gender', '').strip()
    birthday = data.get('birthday', '').strip()
    bio = data.get('bio', '').strip()

    if len(display_name) > 128:
        return jsonify({"error": "昵称长度不能超过 128 个字符。"}), 400
    if len(email) > 128:
        return jsonify({"error": "邮箱长度不能超过 128 个字符。"}), 400
    if email and '@' not in email:
        return jsonify({"error": "邮箱格式不正确。"}), 400
    if gender and gender not in ('男', '女', '保密'):
        return jsonify({"error": "性别仅支持男、女、保密。"}), 400
    if len(bio) > 500:
        return jsonify({"error": "个人简介不能超过 500 个字符。"}), 400

    user['phone'] = phone
    user['display_name'] = display_name
    user['email'] = email
    user['gender'] = gender
    user['birthday'] = birthday
    user['bio'] = bio
    persist_data()

    return jsonify({
        "message": "个人信息已更新。",
        "user": serialize_user(user)
    }), 200

@app.route('/api/admin/overview', methods=['GET'])
def get_admin_overview():
    user, error_response, status_code = get_authenticated_user(required_roles=['admin'])
    if error_response:
        return error_response, status_code

    merchant_users = [serialize_user(u) for u in users if u.get('role') == 'merchant']
    customer_users = [serialize_user(u) for u in users if u.get('role') == 'customer']
    recent_orders = sorted(orders, key=lambda o: o.get('id', 0), reverse=True)[:10]

    total_revenue = sum(order['total'] for order in orders if order['status'] == '已完成')

    return jsonify({
        "stats": {
            "user_count": len(users),
            "customer_count": len(customer_users),
            "merchant_count": len(merchant_users),
            "admin_count": len([u for u in users if u.get('role') == 'admin']),
            "disabled_user_count": len([u for u in users if u.get('account_status') == 'disabled']),
            "flagged_user_count": len([u for u in users if u.get('risk_status') == 'flagged']),
            "store_count": len(stores),
            "active_store_count": len([store for store in stores if store.get('status') == 'active']),
            "inactive_store_count": len([store for store in stores if store.get('status') == 'inactive']),
            "order_count": len(orders),
            "completed_order_count": len([o for o in orders if o.get('status') == '已完成']),
            "cancelled_order_count": len([o for o in orders if o.get('status') == '已取消']),
            "total_revenue": round(total_revenue, 2),
            "menu_count": len(menu),
            "combo_count": len(combos)
        },
        "customers": customer_users,
        "merchants": merchant_users,
        "stores": [serialize_store(store) for store in stores],
        "recent_orders": recent_orders,
        "service_monitor": {
            **SERVICE_MONITOR,
            "remote_ai_configured": bool(REMOTE_AI_API_URL),
            "remote_ai_model": REMOTE_AI_MODEL,
            "active_remote_ai_url": ACTIVE_REMOTE_AI_API_URL or REMOTE_AI_API_URL
        }
    })

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def update_admin_user(user_id):
    admin_user, error_response, status_code = get_authenticated_user(required_roles=['admin'])
    if error_response:
        return error_response, status_code

    target_user = next((item for item in users if item.get('id') == user_id), None)
    if not target_user:
        return jsonify({"error": "用户不存在。"}), 404
    if target_user.get('id') == admin_user.get('id') and (request.get_json() or {}).get('account_status') == 'disabled':
        return jsonify({"error": "不能禁用当前管理员账户。"}), 400

    data = request.get_json() or {}
    account_status = str(data.get('account_status', target_user.get('account_status', 'active'))).strip() or 'active'
    risk_status = str(data.get('risk_status', target_user.get('risk_status', 'normal'))).strip() or 'normal'
    admin_note = str(data.get('admin_note', target_user.get('admin_note', ''))).strip()

    if account_status not in ('active', 'disabled'):
        return jsonify({"error": "账户状态不合法。"}), 400
    if risk_status not in ('normal', 'flagged'):
        return jsonify({"error": "风险状态不合法。"}), 400

    target_user['account_status'] = account_status
    target_user['risk_status'] = risk_status
    target_user['admin_note'] = admin_note
    persist_data()
    return jsonify({"user": serialize_user(target_user)})

@app.route('/api/admin/stores/<int:store_id>', methods=['PUT'])
def update_admin_store(store_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['admin'])
    if error_response:
        return error_response, status_code

    store = get_store_by_id(store_id)
    if not store:
        return jsonify({"error": "店铺不存在。"}), 404

    data = request.get_json() or {}
    status = str(data.get('status', store.get('status', 'active'))).strip() or 'active'
    business_status = str(data.get('business_status', store.get('business_status', '营业中'))).strip() or '营业中'
    announcement = str(data.get('announcement', store.get('announcement', ''))).strip()

    if status not in ('active', 'inactive'):
        return jsonify({"error": "店铺展示状态不合法。"}), 400

    store['status'] = status
    store['business_status'] = business_status
    store['announcement'] = announcement
    persist_data()
    return jsonify({"store": serialize_store(store)})

def get_order_item_sales(store_id=None):
    item_sales = {}
    scoped_orders = filter_records_by_store(orders, store_id)
    for order in scoped_orders:
        if order.get('status') == '已取消':
            continue
        for item in order.get('items', []):
            sales = item_sales.setdefault(item.get('name'), {
                "name": item.get('name'),
                "quantity": 0,
                "revenue": 0.0,
                "type": item.get('type', 'item')
            })
            sales["quantity"] += int(item.get('quantity', 0))
            sales["revenue"] += float(item.get('subtotal', 0))
    ranked_sales = sorted(
        item_sales.values(),
        key=lambda sale: (sale["quantity"], sale["revenue"]),
        reverse=True
    )
    return ranked_sales

SMART_ORDER_AVOID_RULES = {
    "no_beef": ["牛肉", "肥牛", "牛腩", "牛排", "beef"],
    "no_coriander": ["香菜", "芫荽", "coriander", "cilantro"],
    "mild": ["麻辣", "香辣", "辣", "川味", "水煮", "火锅", "椒麻"],
}

SMART_ORDER_PREFERENCE_RULES = {
    "mild": ["不辣", "微辣"],
    "medium_spicy": ["中辣"],
    "heavy_spicy": ["重辣", "超辣"],
    "light": ["清淡", "清爽", "少油", "原味", "番茄", "轻食", "沙拉", "蔬菜", "粥"],
    "heavy": ["重口味", "浓郁", "偏油", "麻辣", "香辣", "椒麻"],
    "sweet": ["偏甜", "甜", "蛋糕", "布丁", "面包"],
    "salty": ["偏咸"],
    "sour": ["偏酸", "酸汤", "番茄", "酸辣"],
    "fresh_umami": ["鲜香", "海鲜", "清汤", "蒜香"],
    "oily": ["偏油", "油香", "爆炒", "烧烤"],
}

FREESTYLE_EMOTION_PREFERENCES = {
    "开心": ["甜品", "饮品", "轻松分享"],
    "疲惫": ["热汤", "清淡", "暖胃"],
    "治愈": ["甜品", "热食", "暖心"],
    "压力大": ["清淡", "少辣", "热汤"],
    "想犒劳自己": ["招牌", "套餐", "肉类"],
    "纠结不知道吃什么": ["招牌", "高评分", "经典款"],
}

FREESTYLE_TIME_PREFERENCES = {
    "早餐": ["清淡", "粥", "面食"],
    "午餐": ["盖饭", "套餐", "主食"],
    "下午茶": ["饮品", "甜品", "轻食"],
    "晚餐": ["主菜", "套餐", "热食"],
    "夜宵": ["夜宵", "麻辣", "小吃"],
}

FREESTYLE_SCENE_PREFERENCES = {
    "一个人": {"people_count": 1, "tokens": ["便捷", "单人餐"]},
    "双人": {"people_count": 2, "tokens": ["双人", "分享"]},
    "朋友聚餐": {"people_count": 3, "tokens": ["聚餐", "分享", "套餐"]},
    "宿舍拼单": {"people_count": 4, "tokens": ["拼单", "套餐", "高性价比"]},
    "加班补能量": {"people_count": 1, "tokens": ["饱腹", "热食", "提神"]},
}

def parse_smart_order_constraints(preferences_text):
    text = (preferences_text or "").strip()
    lowered = text.lower()
    return {
        "text": text,
        "no_beef": any(token in lowered for token in ["不吃牛", "不要牛", "不吃牛肉", "不要牛肉", "no beef", "without beef"]),
        "no_coriander": any(token in lowered for token in ["不要香菜", "不吃香菜", "去香菜", "no cilantro", "no coriander"]),
        "mild": any(token in lowered for token in ["不辣", "微辣", "清淡", "少油", "清爽", "light", "mild"]),
        "medium_spicy": any(token in lowered for token in ["中辣"]),
        "heavy_spicy": any(token in lowered for token in ["重辣", "超辣"]),
        "light": any(token in lowered for token in ["清淡", "少油", "轻食", "清爽", "light"]),
        "heavy": any(token in lowered for token in ["重口味", "浓郁", "偏油"]),
        "sweet": any(token in lowered for token in ["偏甜"]),
        "salty": any(token in lowered for token in ["偏咸"]),
        "sour": any(token in lowered for token in ["偏酸"]),
        "fresh_umami": any(token in lowered for token in ["鲜香"]),
        "oily": any(token in lowered for token in ["偏油"]),
        "preferred_tags": [
            key for key, keywords in SMART_ORDER_PREFERENCE_RULES.items()
            if any(keyword.lower() in lowered for keyword in keywords)
        ],
        "search_terms": extract_search_terms(text)[:8]
    }

def get_category_name(category_id):
    category = next((cat for cat in categories if cat.get("id") == category_id), None)
    return category.get("name", "") if category else ""

def get_store_search_text(store_id):
    store = get_store_by_id(store_id)
    if not store:
        return ""
    return " ".join([
        str(store.get("name", "")),
        str(store.get("description", "")),
        str(store.get("announcement", "")),
        str(store.get("business_status", "")),
    ]).lower()

def get_item_search_text(item):
    return " ".join([
        str(item.get("name", "")),
        str(item.get("description", "")),
        get_category_name(item.get("category_id")),
        get_store_search_text(item.get("store_id")),
    ]).lower()

def calculate_item_keyword_match_score(item, search_terms):
    if not search_terms:
        return 0
    item_name = str(item.get("name", "")).lower()
    category_name = get_category_name(item.get("category_id")).lower()
    store_text = get_store_search_text(item.get("store_id"))
    full_text = " ".join([item_name, str(item.get("description", "")).lower(), category_name, store_text])
    score = 0
    for term in search_terms:
        term_lower = str(term).lower()
        if not term_lower:
            continue
        if term_lower == item_name:
            score += 40
        elif term_lower in item_name:
            score += 28
        elif term_lower in category_name:
            score += 20
        elif term_lower in full_text:
            score += 12
    return score

def matches_avoid_constraints(item, constraints):
    text = f"{item.get('name', '')} {item.get('description', '')}".lower()
    if constraints.get("no_beef") and any(token.lower() in text for token in SMART_ORDER_AVOID_RULES["no_beef"]):
        return False
    if constraints.get("no_coriander") and any(token.lower() in text for token in SMART_ORDER_AVOID_RULES["no_coriander"]):
        return False
    return True

def score_smart_order_item(item, user, constraints, preferred_store_id=None):
    text = f"{item.get('name', '')} {item.get('description', '')}".lower()
    score = 30.0
    price = float(item.get("price", 0))
    keyword_match_score = calculate_item_keyword_match_score(item, constraints.get("search_terms", []))

    if preferred_store_id and item.get("store_id") == preferred_store_id:
        score += 6

    if constraints.get("mild") and any(token.lower() in text for token in SMART_ORDER_AVOID_RULES["mild"]):
        score -= 12
    if constraints.get("medium_spicy") and any(token in text for token in ["辣", "香辣", "麻辣", "川味"]):
        score += 10
    if constraints.get("heavy_spicy") and any(token in text for token in ["麻辣", "香辣", "川味", "火锅", "水煮", "烧烤"]):
        score += 16
    if constraints.get("light") and any(token.lower() in text for token in SMART_ORDER_PREFERENCE_RULES["light"]):
        score += 8
    if constraints.get("heavy") and any(token.lower() in text for token in SMART_ORDER_PREFERENCE_RULES["heavy"]):
        score += 10
    if constraints.get("sweet") and any(token.lower() in text for token in SMART_ORDER_PREFERENCE_RULES["sweet"]):
        score += 10
    if constraints.get("salty") and any(token.lower() in text for token in SMART_ORDER_PREFERENCE_RULES["salty"]):
        score += 8
    if constraints.get("sour") and any(token.lower() in text for token in SMART_ORDER_PREFERENCE_RULES["sour"]):
        score += 10
    if constraints.get("fresh_umami") and any(token.lower() in text for token in SMART_ORDER_PREFERENCE_RULES["fresh_umami"]):
        score += 9
    if constraints.get("oily") and any(token.lower() in text for token in SMART_ORDER_PREFERENCE_RULES["oily"]):
        score += 8

    for tag in constraints.get("preferred_tags", []):
        keywords = SMART_ORDER_PREFERENCE_RULES.get(tag, [])
        if any(keyword.lower() in text for keyword in keywords):
            score += 10

    if item.get("id") in (user.get("favorite_menu_ids") or []):
        score += 12

    recent_views = user.get("recent_views") or []
    if any(view.get("item_id") == item.get("id") for view in recent_views[-8:]):
        score += 5
    if any(view.get("store_id") == item.get("store_id") and view.get("type") == "store" for view in recent_views[-5:]):
        score += 3

    recent_orders = [order for order in orders if order.get("customer") == user.get("username")]
    ordered_item_names = {
        ordered_item.get("name")
        for order in recent_orders[-8:]
        for ordered_item in order.get("items", [])
    }
    if item.get("name") in ordered_item_names:
        score += 4

    score += keyword_match_score
    score += max(0, 10 - price / 5)
    return round(score, 2)

def estimate_target_item_count(people_count, budget=None):
    people = max(1, int(people_count or 1))
    count = 2 if people == 1 else min(people + 1, 4)
    if budget not in (None, ""):
        try:
            budget_value = float(budget)
            if budget_value <= 25:
                count = 1
            elif budget_value <= 45:
                count = min(count, 2)
        except (TypeError, ValueError):
            pass
    return max(1, count)

def summarize_constraint_labels(constraints):
    labels = []
    if constraints.get("mild"):
        labels.append("少辣/清淡")
    if constraints.get("no_coriander"):
        labels.append("去香菜")
    if constraints.get("no_beef"):
        labels.append("不吃牛肉")
    if constraints.get("light"):
        labels.append("偏清淡")
    return labels

def serialize_smart_order_item(item, score=None, reason="", card_type="item"):
    store = get_store_by_id(item.get("store_id"))
    return {
        "id": item.get("id"),
        "type": card_type,
        "name": item.get("name", ""),
        "description": item.get("description", ""),
        "price": round(float(item.get("price", 0)), 2),
        "price_text": f"¥{float(item.get('price', 0)):.2f}",
        "store_id": item.get("store_id"),
        "store_name": store.get("name") if store else "",
        "store_avatar_url": store.get("avatar_url") if store else "",
        "store_cover_image_url": store.get("cover_image_url") if store else "",
        "image": item.get("image"),
        "score": score,
        "reason": reason
    }

def build_smart_order_bundle(
    user,
    preferences,
    budget=None,
    people_count=1,
    store_id=None,
    excluded_item_ids=None,
    locked_item_ids=None,
    replace_item_id=None
):
    constraints = parse_smart_order_constraints(preferences)
    excluded_item_ids = {int(item_id) for item_id in (excluded_item_ids or []) if str(item_id).isdigit()}
    locked_item_ids = [int(item_id) for item_id in (locked_item_ids or []) if str(item_id).isdigit()]
    normalized_budget = None
    if budget not in (None, ""):
        try:
            normalized_budget = round(float(budget), 2)
        except (TypeError, ValueError):
            normalized_budget = None

    scoped_menu = filter_active_records(menu)
    if store_id:
        scoped_menu = [item for item in scoped_menu if item.get("store_id") == int(store_id)]

    candidate_items = []
    for item in scoped_menu:
        if item.get("id") in excluded_item_ids:
            continue
        if not matches_avoid_constraints(item, constraints):
            continue
        candidate_items.append(item)

    strong_keyword_matches = []
    if constraints.get("search_terms"):
        for item in candidate_items:
            match_score = calculate_item_keyword_match_score(item, constraints["search_terms"])
            if match_score >= 20:
                strong_keyword_matches.append(item)
        if strong_keyword_matches:
            candidate_items = strong_keyword_matches

    active_store_ids = sorted({item.get("store_id") for item in candidate_items if item.get("store_id") is not None})
    if not candidate_items:
        return None

    store_scores = {}
    for item in candidate_items:
        current_score = score_smart_order_item(item, user, constraints, preferred_store_id=store_id)
        store_scores[item.get("store_id")] = store_scores.get(item.get("store_id"), 0) + current_score

    ranked_store_ids = [item[0] for item in sorted(store_scores.items(), key=lambda pair: pair[1], reverse=True)]
    target_count = estimate_target_item_count(people_count, normalized_budget)

    for candidate_store_id in ranked_store_ids:
        store_items = [item for item in candidate_items if item.get("store_id") == candidate_store_id]
        scored_items = []
        for item in store_items:
            score = score_smart_order_item(item, user, constraints, preferred_store_id=store_id)
            scored_items.append((score, item))
        scored_items.sort(key=lambda pair: (pair[0], -float(pair[1].get("price", 0))), reverse=True)

        selected_items = []
        selected_ids = set()
        total_price = 0.0

        for locked_item_id in locked_item_ids:
            locked_item = next((item for item in store_items if item.get("id") == locked_item_id), None)
            if not locked_item:
                continue
            selected_items.append((score_smart_order_item(locked_item, user, constraints, preferred_store_id=store_id), locked_item))
            selected_ids.add(locked_item_id)
            total_price += float(locked_item.get("price", 0))

        for score, item in scored_items:
            if item.get("id") in selected_ids:
                continue
            if normalized_budget is not None and total_price + float(item.get("price", 0)) > normalized_budget + 0.001:
                continue
            selected_items.append((score, item))
            selected_ids.add(item.get("id"))
            total_price += float(item.get("price", 0))
            if len(selected_items) >= target_count:
                break

        if not selected_items:
            continue

        if replace_item_id and replace_item_id in selected_ids:
            continue

        if normalized_budget is not None and total_price > normalized_budget + 0.001:
            continue

        selected_cards = []
        for index, (score, item) in enumerate(selected_items, start=1):
            reason_parts = [f"第 {index} 道推荐"]
            matched_terms = [
                term for term in (constraints.get("search_terms") or [])
                if term.lower() in get_item_search_text(item)
            ][:3]
            if matched_terms:
                reason_parts.append("命中需求:" + "、".join(matched_terms))
            if constraints.get("preferred_tags"):
                reason_parts.append("符合偏好")
            if constraints.get("light"):
                reason_parts.append("更偏清淡")
            if item.get("id") in (user.get("favorite_menu_ids") or []):
                reason_parts.append("你收藏过相近菜品")
            selected_cards.append(serialize_smart_order_item(item, score=score, reason="，".join(reason_parts)))

        combo_candidates = []
        scoped_combos = filter_active_records(combos)
        for combo in scoped_combos:
            if combo.get("store_id") != candidate_store_id:
                continue
            combo_price = round(float(combo.get("price", 0)) * float(combo.get("discount", 1)), 2)
            if normalized_budget is not None and combo_price > normalized_budget + 0.001:
                continue
            combo_candidates.append({
                "id": combo.get("id"),
                "type": "combo",
                "name": combo.get("name", ""),
                "description": combo.get("description", ""),
                "price": combo_price,
                "price_text": f"¥{combo_price:.2f}",
                "store_id": combo.get("store_id"),
                "store_name": get_store_by_id(combo.get("store_id")).get("name") if get_store_by_id(combo.get("store_id")) else "",
                "score": round(40 - combo_price / 6, 2),
                "items": combo.get("items", []),
            })
        combo_candidates = sorted(combo_candidates, key=lambda combo: combo.get("score", 0), reverse=True)[:2]

        store = get_store_by_id(candidate_store_id)
        labels = summarize_constraint_labels(constraints)
        summary_parts = [
            f"已为 {max(1, int(people_count or 1))} 人推荐 {len(selected_cards)} 道菜",
            f"推荐店铺：{store.get('name') if store else '未知店铺'}",
            f"当前组合约 ¥{total_price:.2f}"
        ]
        if normalized_budget is not None:
            summary_parts.append(f"预算上限 ¥{normalized_budget:.2f}")
        if labels:
            summary_parts.append("约束：" + "、".join(labels))

        considered_stores = []
        for store_id_item in ranked_store_ids[:6]:
            store_item = get_store_by_id(store_id_item)
            if not store_item:
                continue
            store_item_menu_count = len([item for item in candidate_items if item.get("store_id") == store_id_item])
            considered_stores.append({
                "id": store_item.get("id"),
                "name": store_item.get("name"),
                "menu_count": store_item_menu_count,
                "rating": float(store_item.get("rating", 0)),
            })

        return {
            "store": serialize_store(store) if store else None,
            "items": selected_cards,
            "combo_alternatives": combo_candidates,
            "total_price": round(total_price, 2),
            "budget": normalized_budget,
            "people_count": max(1, int(people_count or 1)),
            "preferences": preferences,
            "constraint_labels": labels,
            "selected_item_ids": [item["id"] for item in selected_cards],
            "candidate_store_count": len(active_store_ids),
            "candidate_item_count": len(candidate_items),
            "considered_stores": considered_stores,
            "summary": "；".join(summary_parts),
        }

    return None

def build_freestyle_preferences(emotion, time_slot, scene, extra_notes):
    tokens = []
    emotion = (emotion or "").strip()
    time_slot = (time_slot or "").strip()
    scene = (scene or "").strip()
    extra_notes = (extra_notes or "").strip()

    tokens.extend(FREESTYLE_EMOTION_PREFERENCES.get(emotion, []))
    tokens.extend(FREESTYLE_TIME_PREFERENCES.get(time_slot, []))
    scene_config = FREESTYLE_SCENE_PREFERENCES.get(scene, {})
    tokens.extend(scene_config.get("tokens", []))
    if extra_notes:
        tokens.append(extra_notes)

    deduped = []
    for token in tokens:
        token = str(token).strip()
        if token and token not in deduped:
            deduped.append(token)
    return "、".join(deduped)

def build_local_order_assistant_reply(preferences, budget=None, people_count=1, menu_source=None, combo_source=None):
    preferences = (preferences or "").strip()
    people_count = max(1, int(people_count or 1))
    normalized_budget = None
    if budget not in (None, ""):
        try:
            normalized_budget = float(budget)
        except (TypeError, ValueError):
            normalized_budget = None

    menu_source = menu if menu_source is None else menu_source
    combo_source = combos if combo_source is None else combo_source
    ranked_items = sorted(menu_source, key=lambda item: item.get("price", 0))
    if normalized_budget is not None:
        ranked_items = [item for item in ranked_items if float(item.get("price", 0)) <= normalized_budget]
    if preferences:
        preference_keywords = preferences.lower()
        ranked_items = sorted(
            ranked_items,
            key=lambda item: (
                preference_keywords in (item.get("name", "").lower() + item.get("description", "").lower()),
                -float(item.get("price", 0))
            ),
            reverse=True
        )

    recommended_items = ranked_items[:3]
    ranked_combos = sorted(combo_source, key=lambda combo: combo.get("price", 0) * combo.get("discount", 1))
    if normalized_budget is not None:
        ranked_combos = [
            combo for combo in ranked_combos
            if float(combo.get("price", 0)) * float(combo.get("discount", 1)) <= normalized_budget
        ]
    recommended_combo = ranked_combos[0] if ranked_combos else None

    lines = [
        f"已根据 {people_count} 人用餐场景生成点餐建议。"
    ]
    if preferences:
        lines.append(f"你的偏好：{preferences}")
    if normalized_budget is not None:
        lines.append(f"预算参考：¥{normalized_budget:.2f}")

    if recommended_items:
        item_text = "；".join([
            f"{item.get('name')} ¥{float(item.get('price', 0)):.2f}（{item.get('description', '暂无描述')}）"
            for item in recommended_items
        ])
        lines.append(f"推荐单品：{item_text}")
    else:
        lines.append("当前预算下没有合适单品，建议放宽预算或选择套餐。")

    if recommended_combo:
        combo_price = float(recommended_combo.get("price", 0)) * float(recommended_combo.get("discount", 1))
        lines.append(f"推荐套餐：{recommended_combo.get('name')}，到手约 ¥{combo_price:.2f}。")

    lines.append("如果你告诉我口味、忌口、预算或人数，我可以继续缩小推荐范围。")
    return "\n".join(lines)


def build_analysis_narrative_summary(store, stats, top_items, review_stats):
    store_name = (store or {}).get("name") or "当前店铺"
    summary_parts = []
    summary_parts.append(
        f"{store_name} 目前累计订单 {stats['total_orders']} 单，已完成 {stats['completed_orders']} 单，"
        f"实现营业额 ¥{stats['total_revenue']:.2f}，平均客单价 ¥{stats['average_order_value']:.2f}。"
    )
    if top_items:
        top_item = top_items[0]
        summary_parts.append(
            f"现阶段最强势的商品是 {top_item['name']}，累计售出 {top_item['quantity']} 份，"
            f"对应营收约 ¥{top_item['revenue']:.2f}。"
        )
    if stats["repurchase_rate"] > 0:
        summary_parts.append(
            f"复购率约为 {stats['repurchase_rate']:.2f}%，说明已有一部分用户形成稳定回购。"
        )
    else:
        summary_parts.append("当前复购用户仍偏少，后续可以通过套餐和回购券继续拉升复购。")

    if review_stats["review_count"] > 0:
        summary_parts.append(
            f"用户共提交 {review_stats['review_count']} 条评价，综合评分 {review_stats['average_rating']:.1f} 分，"
            f"配送 {review_stats['delivery_rating']:.1f}、包装 {review_stats['packaging_rating']:.1f}、口味 {review_stats['taste_rating']:.1f}。"
        )
        if review_stats["low_rating_count"] > 0:
            summary_parts.append(
                f"其中 {review_stats['low_rating_count']} 条为低分评价，建议优先复盘差评里的出餐、包装和口味问题。"
            )
    else:
        summary_parts.append("目前还没有形成足够评价样本，建议引导已完成订单用户补充评价，便于后续做口碑优化。")

    if stats["pending_orders"] > 0:
        summary_parts.append(f"当前仍有 {stats['pending_orders']} 单待处理，需要兼顾履约效率与用户体验。")
    if stats["cancelled_orders"] > 0:
        summary_parts.append(f"累计取消 {stats['cancelled_orders']} 单，建议关注高峰时段、库存同步和描述一致性。")
    return "".join(summary_parts)


def build_merchant_assistant_fallback_reply(message, analysis_payload):
    stats = analysis_payload.get("stats", {})
    top_items = analysis_payload.get("top_items", [])
    suggestions = analysis_payload.get("suggestions", [])
    risks = analysis_payload.get("risks", [])
    review_stats = analysis_payload.get("review_stats", {})

    prompt = (message or "").strip()
    lines = []

    if "复购" in prompt:
        lines.append(f"当前复购率约为 {stats.get('repurchase_rate', 0):.2f}%。")
        lines.append("建议用热销商品做复购券、老客套餐和二次下单提醒。")
    elif "评价" in prompt or "口碑" in prompt:
        lines.append(
            f"当前共有 {review_stats.get('review_count', 0)} 条评价，综合评分 {review_stats.get('average_rating', 0):.1f} 分。"
        )
        if review_stats.get("low_rating_count", 0):
            lines.append("低分评价需要优先拆解配送、包装、口味三个维度，逐项整改。")
    elif "销量" in prompt or "商品" in prompt:
        if top_items:
            top_text = "；".join([f"{item['name']} 销量 {item['quantity']}" for item in top_items[:3]])
            lines.append(f"当前热销商品主要是：{top_text}。")
        lines.append("建议围绕热销商品做搭配套餐，并对低销量商品重新定价或调整描述。")
    else:
        lines.append(analysis_payload.get("narrative_summary") or "当前已生成店铺经营概览。")

    if suggestions:
        lines.append("经营建议：" + "；".join(suggestions[:3]))
    if risks:
        lines.append("风险提醒：" + "；".join(risks[:2]))
    lines.append("你也可以继续追问，例如“怎么提高复购”“哪些商品该重点推广”“差评该怎么处理”。")
    return "\n".join(lines)

def build_local_analysis_payload(store_id=None):
    scoped_orders = filter_records_by_store(orders, store_id)
    scoped_menu = filter_records_by_store(menu, store_id)
    scoped_combos = filter_records_by_store(combos, store_id)
    scoped_reviews = filter_records_by_store(reviews, store_id)
    store = get_store_by_id(store_id) if store_id else None
    total_orders = len(scoped_orders)
    completed_orders = [order for order in scoped_orders if order.get('status') == '已完成']
    pending_orders = [order for order in scoped_orders if order.get('status') in ('已接单', '制作中', '配送中')]
    cancelled_orders = [order for order in scoped_orders if order.get('status') == '已取消']
    total_revenue = round(sum(float(order.get('total', 0)) for order in completed_orders), 2)
    average_order_value = round(total_revenue / len(completed_orders), 2) if completed_orders else 0.0
    item_sales = get_order_item_sales(store_id=store_id)
    top_items = item_sales[:5]
    completed_customer_counts = {}
    for order in completed_orders:
        customer = order.get('customer', '')
        if not customer:
            continue
        completed_customer_counts[customer] = completed_customer_counts.get(customer, 0) + 1
    repurchase_customers = len([count for count in completed_customer_counts.values() if count >= 2])
    repurchase_rate = round((repurchase_customers / len(completed_customer_counts)) * 100, 2) if completed_customer_counts else 0.0

    order_trend_map = {}
    for order in scoped_orders:
        created_at = str(order.get('created_at', ''))
        day_key = created_at[:10] if len(created_at) >= 10 else '未知日期'
        order_trend_map[day_key] = order_trend_map.get(day_key, 0) + 1
    order_trend = [
        {"label": label, "value": value}
        for label, value in sorted(order_trend_map.items())[-7:]
    ]

    time_slot_map = {
        '早餐': 0,
        '午餐': 0,
        '下午茶': 0,
        '晚餐': 0,
        '夜宵': 0
    }
    for order in scoped_orders:
        created_at = str(order.get('created_at', ''))
        hour = None
        if len(created_at) >= 13:
            try:
                hour = int(created_at[11:13])
            except ValueError:
                hour = None
        if hour is None:
            continue
        if 6 <= hour < 10:
            time_slot_map['早餐'] += 1
        elif 10 <= hour < 14:
            time_slot_map['午餐'] += 1
        elif 14 <= hour < 17:
            time_slot_map['下午茶'] += 1
        elif 17 <= hour < 21:
            time_slot_map['晚餐'] += 1
        else:
            time_slot_map['夜宵'] += 1
    time_distribution = [{"label": label, "value": value} for label, value in time_slot_map.items()]

    review_count = len(scoped_reviews)
    average_rating = round(
        sum(float(review.get("rating", 0)) for review in scoped_reviews) / review_count, 1
    ) if review_count else 0.0
    delivery_rating = round(
        sum(float(review.get("delivery_rating", 0)) for review in scoped_reviews) / review_count, 1
    ) if review_count else 0.0
    packaging_rating = round(
        sum(float(review.get("packaging_rating", 0)) for review in scoped_reviews) / review_count, 1
    ) if review_count else 0.0
    taste_rating = round(
        sum(float(review.get("taste_rating", 0)) for review in scoped_reviews) / review_count, 1
    ) if review_count else 0.0
    low_rating_reviews = [review for review in scoped_reviews if float(review.get("rating", 0)) <= 3]
    review_stats = {
        "review_count": review_count,
        "average_rating": average_rating,
        "delivery_rating": delivery_rating,
        "packaging_rating": packaging_rating,
        "taste_rating": taste_rating,
        "low_rating_count": len(low_rating_reviews)
    }

    insights = []
    if top_items:
        insights.append(f"当前销量最高的是 {top_items[0]['name']}，累计售出 {top_items[0]['quantity']} 份。")
    insights.append(f"已完成订单 {len(completed_orders)} 单，平均客单价 ¥{average_order_value:.2f}。")
    insights.append(f"复购率约为 {repurchase_rate:.2f}%，可重点维护重复下单用户。")
    if review_count:
        insights.append(
            f"当前共有 {review_count} 条评价，综合评分 {average_rating:.1f} 分，口味评分 {taste_rating:.1f} 分。"
        )
    if pending_orders:
        insights.append(f"还有 {len(pending_orders)} 单待处理，建议关注出餐和配送节奏。")
    if cancelled_orders:
        insights.append(f"累计取消 {len(cancelled_orders)} 单，可复盘高频取消时段和商品。")

    suggestions = [
        "优先围绕热销商品设计组合套餐，提高连带购买率。",
        "对低销量商品做限时活动或重新优化描述、图片和定价。",
        "高峰时段前提前备货，减少待处理订单积压。"
    ]
    risks = []
    if cancelled_orders and total_orders and (len(cancelled_orders) / total_orders) >= 0.2:
        risks.append("取消订单占比较高，建议排查出餐时效、配送稳定性和商品描述一致性。")
    if pending_orders and len(pending_orders) >= 5:
        risks.append("当前待处理订单偏多，高峰承载压力较大，需关注履约节奏。")
    if repurchase_rate < 20 and completed_orders:
        risks.append("复购率偏低，建议加强会员运营、回购优惠和招牌商品复购引导。")
    if review_count and average_rating < 4.0:
        risks.append("当前综合评分偏低，建议重点排查差评中的口味稳定性、包装完整性和配送时效。")
    if not risks:
        risks.append("当前未发现明显高风险项，可持续观察订单取消率和高峰时段波动。")

    narrative_summary = build_analysis_narrative_summary(store, {
        "total_orders": total_orders,
        "completed_orders": len(completed_orders),
        "pending_orders": len(pending_orders),
        "cancelled_orders": len(cancelled_orders),
        "total_revenue": total_revenue,
        "average_order_value": average_order_value,
        "repurchase_rate": repurchase_rate
    }, top_items, review_stats)

    return {
        "store": serialize_store(store) if store else None,
        "stats": {
            "total_orders": total_orders,
            "order_volume": total_orders,
            "completed_orders": len(completed_orders),
            "pending_orders": len(pending_orders),
            "cancelled_orders": len(cancelled_orders),
            "total_revenue": total_revenue,
            "revenue": total_revenue,
            "average_order_value": average_order_value,
            "repurchase_rate": repurchase_rate,
            "menu_count": len(scoped_menu),
            "combo_count": len(scoped_combos)
        },
        "top_items": top_items,
        "review_stats": review_stats,
        "charts": {
            "order_trend": order_trend,
            "top_items": top_items,
            "time_distribution": time_distribution
        },
        "narrative_summary": narrative_summary,
        "insights": insights,
        "suggestions": suggestions,
        "risks": risks
    }

# 地址管理
@app.route('/api/addresses', methods=['GET'])
def get_addresses():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    return jsonify({"addresses": user['addresses']}), 200

@app.route('/api/addresses', methods=['POST'])
def add_address():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    address = data.get('address', '').strip()
    phone = data.get('phone', '').strip()
    is_default = data.get('is_default', False)

    if not name:
        return jsonify({"error": "收货人名称不能为空。"}), 400
    if not address:
        return jsonify({"error": "地址不能为空。"}), 400
    if not phone:
        return jsonify({"error": "电话不能为空。"}), 400

    # 如果设为默认，取消其他默认地址
    if is_default:
        for addr in user['addresses']:
            addr['is_default'] = False

    next_address_id = max((addr['id'] for addr in user['addresses']), default=0) + 1
    new_address = {
        "id": next_address_id,
        "name": name,
        "address": address,
        "phone": phone,
        "is_default": is_default,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    user['addresses'].append(new_address)
    persist_data()

    return jsonify({"address": new_address}), 201

@app.route('/api/addresses/<int:address_id>', methods=['PUT'])
def update_address(address_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    address = next((a for a in user['addresses'] if a['id'] == address_id), None)
    if not address:
        return jsonify({"error": "地址不存在。"}), 404

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    addr = data.get('address', '').strip()
    phone = data.get('phone', '').strip()
    is_default = data.get('is_default', address['is_default'])

    if not name:
        return jsonify({"error": "收货人名称不能为空。"}), 400
    if not addr:
        return jsonify({"error": "地址不能为空。"}), 400
    if not phone:
        return jsonify({"error": "电话不能为空。"}), 400

    # 如果设为默认，取消其他默认地址
    if is_default and not address['is_default']:
        for a in user['addresses']:
            a['is_default'] = False

    address['name'] = name
    address['address'] = addr
    address['phone'] = phone
    address['is_default'] = is_default
    persist_data()

    return jsonify({"address": address}), 200

@app.route('/api/addresses/<int:address_id>', methods=['DELETE'])
def delete_address(address_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    address = next((a for a in user['addresses'] if a['id'] == address_id), None)
    if not address:
        return jsonify({"error": "地址不存在。"}), 404

    user['addresses'] = [a for a in user['addresses'] if a['id'] != address_id]
    persist_data()

    return jsonify({"success": True}), 200

@app.route('/api/smart-order-assistant', methods=['POST'])
def smart_order_assistant():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    data = request.get_json() or {}
    store_id = data.get('store_id')
    preference_tags = data.get('preference_tags') or []
    other_requirements = str(data.get('other_requirements', '')).strip()
    budget = data.get('budget')
    people_count = data.get('people_count', 1)
    action = str(data.get('action', 'generate')).strip() or 'generate'
    if store_id not in (None, ''):
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return jsonify({"error": "店铺参数不合法。"}), 400
    else:
        store_id = None

    existing_item_ids = data.get('existing_item_ids') or []
    replace_item_id = data.get('replace_item_id')
    if replace_item_id not in (None, ''):
        try:
            replace_item_id = int(replace_item_id)
        except (TypeError, ValueError):
            replace_item_id = None

    excluded_item_ids = data.get('excluded_item_ids') or []
    locked_item_ids = []
    if action == 'replace_item' and replace_item_id:
        locked_item_ids = [
            int(item_id) for item_id in existing_item_ids
            if str(item_id).isdigit() and int(item_id) != replace_item_id
        ]
        excluded_item_ids = list(set(excluded_item_ids + [replace_item_id]))
    elif action in ('rebalance_budget', 'reroll'):
        excluded_item_ids = list({int(item_id) for item_id in excluded_item_ids if str(item_id).isdigit()})

    preference_payload = build_preference_text(
        preference_tags=preference_tags,
        other_requirements=other_requirements
    )
    preferences = preference_payload["preference_text"]

    plan = build_smart_order_bundle(
        user=user,
        preferences=preferences,
        budget=budget,
        people_count=people_count,
        store_id=store_id,
        excluded_item_ids=excluded_item_ids,
        locked_item_ids=locked_item_ids,
        replace_item_id=replace_item_id
    )
    if not plan:
        return jsonify({"error": "当前条件下没有匹配的推荐结果，请放宽预算或减少忌口限制。"}), 400

    scoped_menu = filter_records_by_store(menu, plan["store"]["id"] if plan.get("store") else store_id)
    scoped_combos = filter_records_by_store(combos, plan["store"]["id"] if plan.get("store") else store_id)
    prompt = build_smart_order_model_prompt(
        user=user,
        action=action,
        people_count=people_count,
        budget=budget,
        preferences=preferences,
        scoped_menu=scoped_menu,
        scoped_combos=scoped_combos,
        plan=plan
    )

    ai_response, err = call_remote_ai_api(prompt, session_id=request.headers.get('X-Session-ID'))
    if ai_response:
        mark_service_metric('smart_order', success=True)
        return jsonify({
            "recommendation": ai_response,
            "source": "remote_api",
            "plan": plan,
            "requirement_keywords": preference_payload["requirement_keywords"],
            "keyword_source": preference_payload["keyword_source"],
        }), 200

    mark_service_metric('smart_order', success=False)
    return jsonify({
        "recommendation": (
            f"{plan['summary']}。\n"
            "你可以继续点击“换一道菜”“预算不变重新搭配”，也可以补充少辣、清淡、去香菜、不吃牛肉等约束继续细化。"
        ),
        "plan": plan,
        "source": "local_fallback",
        "warning": err or "远程AI不可用，已回退本地点餐建议。",
        "requirement_keywords": preference_payload["requirement_keywords"],
        "keyword_source": preference_payload["keyword_source"],
        "keyword_warning": preference_payload["keyword_warning"],
    }), 200

@app.route('/api/smart-order-freestyle', methods=['POST'])
def smart_order_freestyle():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code

    data = request.get_json() or {}
    emotion = str(data.get('emotion', '')).strip()
    time_slot = str(data.get('time_slot', '')).strip()
    scene = str(data.get('scene', '')).strip()
    budget = data.get('budget')
    extra_notes = str(data.get('extra_notes', '')).strip()
    store_id = data.get('store_id')

    if store_id not in (None, ''):
        try:
            store_id = int(store_id)
        except (TypeError, ValueError):
            return jsonify({"error": "店铺参数不合法。"}), 400
    else:
        store_id = None

    if not any([emotion, time_slot, scene, extra_notes]):
        return jsonify({"error": "请至少填写情绪、时间段、场景或补充说明中的一项。"}), 400

    freestyle_preferences = build_freestyle_preferences(emotion, time_slot, scene, extra_notes)
    scene_config = FREESTYLE_SCENE_PREFERENCES.get(scene, {})
    people_count = int(scene_config.get("people_count", data.get('people_count', 1) or 1))

    plan = build_smart_order_bundle(
        user=user,
        preferences=freestyle_preferences,
        budget=budget,
        people_count=people_count,
        store_id=store_id
    )
    if not plan:
        return jsonify({"error": "当前随心条件下没有匹配的推荐结果，请放宽预算或减少限制。"}), 400

    scoped_menu = filter_records_by_store(menu, plan["store"]["id"] if plan.get("store") else store_id)
    scoped_combos = filter_records_by_store(combos, plan["store"]["id"] if plan.get("store") else store_id)

    prompt = build_smart_order_model_prompt(
        user=user,
        action='freestyle',
        people_count=people_count,
        budget=budget,
        preferences=f"{freestyle_preferences}；情绪:{emotion or '未提供'}；时段:{time_slot or '未提供'}；场景:{scene or '未提供'}",
        scoped_menu=scoped_menu,
        scoped_combos=scoped_combos,
        plan=plan
    )

    ai_response, err = call_remote_ai_api(prompt, session_id=request.headers.get('X-Session-ID'))
    if ai_response:
        mark_service_metric('smart_order', success=True)
        return jsonify({
            "recommendation": ai_response,
            "source": "remote_api",
            "plan": plan,
            "freestyle_preferences": freestyle_preferences,
            "people_count": people_count
        }), 200

    mark_service_metric('smart_order', success=False)
    return jsonify({
        "recommendation": (
            f"已根据你的情绪、时间段和场景生成随心推荐：{plan['summary']}。\n"
            f"系统理解到的偏好是：{freestyle_preferences or '未提炼出明确偏好'}。"
        ),
        "plan": plan,
        "source": "local_fallback",
        "warning": err or "远程AI不可用，已回退本地随心推荐。",
        "freestyle_preferences": freestyle_preferences,
        "people_count": people_count
    }), 200

@app.route('/api/data-analysis', methods=['GET'])
def get_data_analysis():
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code

    store_id = get_store_id_for_request(user, allow_all_for_admin=True)
    analysis_payload = build_local_analysis_payload(store_id=store_id)
    top_items_text = "；".join([
        f"{item['name']} 销量{item['quantity']} 营收¥{item['revenue']:.2f}"
        for item in analysis_payload["top_items"][:5]
    ]) or "暂无销量数据"

    prompt = (
        "你是餐饮经营分析助手。请基于以下经营数据输出一段自然语言总结，"
        "同时补充 3 条核心洞察、3 条经营建议和风险提示，语言简洁，适合商家直接查看。\n"
        f"店铺：{analysis_payload.get('store', {}).get('name', '当前店铺')}\n"
        f"总订单：{analysis_payload['stats']['total_orders']}\n"
        f"已完成订单：{analysis_payload['stats']['completed_orders']}\n"
        f"待处理订单：{analysis_payload['stats']['pending_orders']}\n"
        f"已取消订单：{analysis_payload['stats']['cancelled_orders']}\n"
        f"总营收：¥{analysis_payload['stats']['total_revenue']:.2f}\n"
        f"平均客单价：¥{analysis_payload['stats']['average_order_value']:.2f}\n"
        f"复购率：{analysis_payload['stats']['repurchase_rate']:.2f}%\n"
        f"商品数：{analysis_payload['stats']['menu_count']}\n"
        f"套餐数：{analysis_payload['stats']['combo_count']}\n"
        f"评价数：{analysis_payload['review_stats']['review_count']}\n"
        f"综合评分：{analysis_payload['review_stats']['average_rating']:.1f}\n"
        f"配送评分：{analysis_payload['review_stats']['delivery_rating']:.1f}\n"
        f"包装评分：{analysis_payload['review_stats']['packaging_rating']:.1f}\n"
        f"口味评分：{analysis_payload['review_stats']['taste_rating']:.1f}\n"
        f"热销商品：{top_items_text}"
    )

    ai_response, err = call_remote_ai_api(prompt, session_id=request.headers.get('X-Session-ID'))
    mark_service_metric('data_analysis', success=bool(ai_response))
    analysis_payload["ai_summary"] = ai_response or analysis_payload["narrative_summary"]
    analysis_payload["source"] = "remote_api" if ai_response else "local_fallback"
    if err and not ai_response:
        analysis_payload["warning"] = err
    return jsonify(analysis_payload), 200


@app.route('/api/merchant-assistant', methods=['POST'])
def merchant_assistant():
    user, error_response, status_code = get_authenticated_user(required_roles=['merchant', 'admin'])
    if error_response:
        return error_response, status_code

    data = request.get_json() or {}
    message = str(data.get("message", "")).strip()
    history = data.get("history") or []
    if not message:
        return jsonify({"error": "请输入经营问题。"}), 400

    store_id = get_store_id_for_request(user, allow_all_for_admin=True)
    analysis_payload = build_local_analysis_payload(store_id=store_id)
    store_name = analysis_payload.get("store", {}).get("name", "当前店铺")
    top_items_text = "；".join([
        f"{item['name']} 销量{item['quantity']} 营收¥{item['revenue']:.2f}"
        for item in analysis_payload["top_items"][:5]
    ]) or "暂无销量数据"
    recent_reviews = filter_records_by_store(reviews, store_id)
    recent_reviews = sorted(recent_reviews, key=lambda review: review.get("created_at", ""), reverse=True)[:5]
    review_text = "；".join([
        f"{review.get('customer', '匿名用户')} 评分{float(review.get('rating', 0)):.1f}：{(review.get('content') or '未填写评价')[:40]}"
        for review in recent_reviews
    ]) or "暂无近期评价"
    recent_orders = filter_records_by_store(orders, store_id)
    recent_orders = sorted(recent_orders, key=lambda order: order.get("created_at", ""), reverse=True)[:5]
    order_text = "；".join([
        f"订单#{order.get('id')} {order.get('status')} ¥{float(order.get('total', 0)):.2f} {order.get('created_at', '')}"
        for order in recent_orders
    ]) or "暂无近期订单"

    assistant_prompt = (
        "你是商家经营助手，需要基于店铺真实经营数据给出可执行建议。"
        "回答要直接、具体，优先结合销量、订单、评价、复购和履约情况。"
        "如用户追问方案，给出分步骤建议。不要输出思考过程。\n"
        f"店铺名称：{store_name}\n"
        f"系统自动总结：{analysis_payload.get('narrative_summary', '')}\n"
        f"经营指标：总订单{analysis_payload['stats']['total_orders']}，已完成{analysis_payload['stats']['completed_orders']}，"
        f"待处理{analysis_payload['stats']['pending_orders']}，已取消{analysis_payload['stats']['cancelled_orders']}，"
        f"营业额¥{analysis_payload['stats']['total_revenue']:.2f}，客单价¥{analysis_payload['stats']['average_order_value']:.2f}，"
        f"复购率{analysis_payload['stats']['repurchase_rate']:.2f}%\n"
        f"评价指标：综合{analysis_payload['review_stats']['average_rating']:.1f}，配送{analysis_payload['review_stats']['delivery_rating']:.1f}，"
        f"包装{analysis_payload['review_stats']['packaging_rating']:.1f}，口味{analysis_payload['review_stats']['taste_rating']:.1f}，"
        f"评价数{analysis_payload['review_stats']['review_count']}\n"
        f"热销商品：{top_items_text}\n"
        f"近期订单：{order_text}\n"
        f"近期评价：{review_text}\n"
        f"系统洞察：{'；'.join(analysis_payload.get('insights', []))}\n"
        f"系统建议：{'；'.join(analysis_payload.get('suggestions', []))}\n"
        f"系统风险：{'；'.join(analysis_payload.get('risks', []))}\n"
        f"商家问题：{message}"
    )

    normalized_history = history[-8:] if isinstance(history, list) else []
    ai_response, err = call_remote_ai_api(
        assistant_prompt,
        history=normalized_history,
        session_id=request.headers.get('X-Session-ID')
    )
    if ai_response:
        mark_service_metric('data_analysis', success=True)
        return jsonify({
            "reply": ai_response,
            "source": "remote_api",
            "context_summary": analysis_payload.get("narrative_summary", "")
        }), 200

    mark_service_metric('data_analysis', success=False)
    return jsonify({
        "reply": build_merchant_assistant_fallback_reply(message, analysis_payload),
        "source": "local_fallback",
        "warning": err or "远程AI不可用，已回退到本地经营建议。",
        "context_summary": analysis_payload.get("narrative_summary", "")
    }), 200

# AI 客服对话（代理远程模型 HTTP API）
def build_ai_payload(message, image_url=None, history=None, include_model=True):
    messages = [{"role": "system", "content": REMOTE_AI_SYSTEM_PROMPT}]

    # 可选历史上下文（前端可传 role/content 结构）
    if isinstance(history, list):
        for msg in history:
            role = (msg or {}).get("role")
            content = (msg or {}).get("content")
            if role in ("user", "assistant", "system") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content.strip()})

    if image_url:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": message},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        })
    else:
        messages.append({"role": "user", "content": message})

    payload = {
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
        "max_tokens": REMOTE_AI_MAX_TOKENS,
        "max_new_tokens": REMOTE_AI_MAX_TOKENS
    }
    if include_model and REMOTE_AI_MODEL:
        payload["model"] = REMOTE_AI_MODEL
    return payload

def build_prompt_payload(message, image_url=None, history=None, include_model=True):
    """兼容仅支持 prompt 字段的推理服务"""
    prompt_parts = []
    if isinstance(history, list):
        for msg in history:
            role = (msg or {}).get("role", "user")
            content = (msg or {}).get("content", "")
            if isinstance(content, str) and content.strip():
                prompt_parts.append(f"{role}: {content.strip()}")

    prompt_parts.append(f"user: {message}")
    if image_url:
        prompt_parts.append(f"image_url: {image_url}")
    prompt_parts.append("assistant:")
    prompt_text = "\n".join(prompt_parts)

    payload = {"prompt": prompt_text}
    payload["max_tokens"] = REMOTE_AI_MAX_TOKENS
    payload["max_new_tokens"] = REMOTE_AI_MAX_TOKENS
    if include_model and REMOTE_AI_MODEL:
        payload["model"] = REMOTE_AI_MODEL
    return payload

def build_prompt_payload_variants(message, image_url=None, history=None, include_model=True):
    """不同服务对 prompt 协议字段要求不同，按常见组合自动重试"""
    base_payload = build_prompt_payload(
        message,
        image_url=image_url,
        history=history,
        include_model=include_model
    )

    variants = []
    def add_variant(v):
        if v not in variants:
            variants.append(v)

    # 1) 极简 prompt（很多 FastAPI 封装只接受这个）
    add_variant(dict(base_payload))

    # 2) 常见推理参数
    with_sampling = dict(base_payload)
    with_sampling["temperature"] = 0.7
    with_sampling["stream"] = False
    add_variant(with_sampling)

    # 3) 补充 max_tokens（部分服务要求）
    with_tokens = dict(base_payload)
    with_tokens["max_tokens"] = max(REMOTE_AI_MAX_TOKENS, 1024)
    with_tokens["max_new_tokens"] = max(REMOTE_AI_MAX_TOKENS, 1024)
    add_variant(with_tokens)

    return variants

def is_model_not_found_error(error_text):
    lower = (error_text or "").lower()
    return "model" in lower and ("does not exist" in lower or "not found" in lower)

def sanitize_ai_answer(text):
    if not isinstance(text, str):
        return text

    cleaned = text

    # 去掉常见思考标签块
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)

    # 如果包含“最终回答/回答”，优先截取该段后的内容
    final_markers = [
        "最终回答：", "最终回答:", "最终答案：", "最终答案:",
        "回答：", "回答:"
    ]
    for marker in final_markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[1]
            break

    # 清理“思考过程”标题行
    cleaned = re.sub(r"^\s*(思考过程|推理过程|分析过程)\s*[:：]\s*$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

    # 规范空行
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or text.strip()

def extract_ai_text(response_json):
    if not isinstance(response_json, dict):
        return None

    # OpenAI 风格: {"choices":[{"message":{"content":"..."}}]}
    choices = response_json.get("choices")
    if isinstance(choices, list) and choices:
        message = (choices[0] or {}).get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return sanitize_ai_answer(content.strip())
        if isinstance(content, list):
            text_parts = []
            for part in content:
                text = (part or {}).get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
            if text_parts:
                return sanitize_ai_answer("\n".join(text_parts))

    # 兼容一些常见自定义字段
    for key in ("response", "answer", "text", "output_text", "content"):
        value = response_json.get(key)
        if isinstance(value, str) and value.strip():
            return sanitize_ai_answer(value.strip())

    return None


def build_remote_ai_endpoint(path):
    base_url = (ACTIVE_REMOTE_AI_API_URL or REMOTE_AI_API_URL or "").rstrip("/")
    return f"{base_url}{path}"


def build_remote_ai_prompt(message, history=None):
    prompt_sections = [REMOTE_AI_SYSTEM_PROMPT]

    if isinstance(history, list):
        dialogue_lines = []
        for item in history[-AI_CONTEXT_MAX_MESSAGES:]:
            if not isinstance(item, dict):
                continue
            role = (item.get("role") or "").strip().lower()
            content = item.get("content")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        text_parts.append(part["text"].strip())
                content = "\n".join(part for part in text_parts if part)
            if not isinstance(content, str) or not content.strip():
                continue
            role_name = {
                "system": "系统",
                "user": "用户",
                "assistant": "助手"
            }.get(role, "消息")
            dialogue_lines.append(f"{role_name}：{content.strip()}")
        if dialogue_lines:
            prompt_sections.append("以下是对话上下文：\n" + "\n".join(dialogue_lines))

    prompt_sections.append(f"当前用户问题：{message.strip()}")
    prompt_sections.append("请直接给出最终回答，不要输出思考过程。")
    return "\n\n".join(section for section in prompt_sections if section).strip()


def decode_image_data_url(image_url):
    if not isinstance(image_url, str) or not image_url.strip():
        return None

    image_url = image_url.strip()
    if not image_url.startswith("data:"):
        return None

    match = re.match(r"^data:(image/[\w.+-]+);base64,(.*)$", image_url, flags=re.DOTALL)
    if not match:
        return None

    mime_type = match.group(1)
    encoded = match.group(2)
    try:
        binary = base64.b64decode(encoded)
    except (ValueError, TypeError):
        return None

    extension = mime_type.split("/", 1)[-1].replace("+xml", "")
    extension = "jpg" if extension == "jpeg" else extension
    filename = f"upload.{extension or 'png'}"
    return filename, mime_type, binary


def build_remote_ai_headers(include_json=True):
    headers = {}
    if include_json:
        headers["Content-Type"] = "application/json"
    if REMOTE_AI_API_KEY:
        headers["X-API-Key"] = REMOTE_AI_API_KEY
    return headers


def call_remote_ai_api(message, image_url=None, history=None, session_id=None):
    global ACTIVE_REMOTE_AI_API_URL, USE_MODEL_FIELD

    if not REMOTE_AI_API_URL:
        return None, "REMOTE_AI_API_URL 未配置。"

    try:
        prompt = build_remote_ai_prompt(message, history=history)
        request_kwargs = {
            "timeout": (REMOTE_AI_CONNECT_TIMEOUT, REMOTE_AI_TIMEOUT)
        }

        if image_url:
            image_payload = decode_image_data_url(image_url)
            if not image_payload:
                return None, "当前图片格式无法识别，请重新上传后再试。"
            filename, mime_type, binary = image_payload
            form_data = {"prompt": prompt}
            if session_id:
                form_data["session_id"] = session_id
            resp = requests.post(
                build_remote_ai_endpoint("/api/v1/chat"),
                headers=build_remote_ai_headers(include_json=False),
                data=form_data,
                files={"image": (filename, binary, mime_type)},
                **request_kwargs
            )
        else:
            payload = {"prompt": prompt}
            if session_id:
                payload["session_id"] = session_id
            resp = requests.post(
                build_remote_ai_endpoint("/api/v1/chat/text-only"),
                headers=build_remote_ai_headers(include_json=True),
                json=payload,
                **request_kwargs
            )

        if not resp.ok:
            text_preview = (resp.text or "").strip().replace("\n", " ")
            text_preview = text_preview[:220] if text_preview else ""
            if text_preview:
                return None, f"远程AI服务调用失败，状态码 {resp.status_code}，响应: {text_preview}"
            return None, f"远程AI服务调用失败，状态码 {resp.status_code}"

        body = resp.json()
        text = extract_ai_text(body)
        if not text:
            return None, "远程AI返回格式无法识别，请检查 /api/v1/chat 或 /api/v1/chat/text-only 的响应结构。"
        return text, None
    except requests.Timeout:
        return None, f"远程AI服务超时（读取超时 {REMOTE_AI_TIMEOUT:.0f}s），请稍后重试。"
    except requests.RequestException as e:
        return None, f"远程AI服务请求异常: {e}"
    except ValueError:
        return None, "远程AI返回的不是合法JSON。"

def generate_mock_response(message):
    """模拟AI回复（当远程AI不可用时使用）"""
    message_lower = message.lower()
    
    if "菜单" in message_lower or "菜" in message_lower:
        return "您好！我们有各种美味的菜品，包括主菜、面食、饮品和套餐。您可以在菜单页面浏览所有商品。"
    elif "订单" in message_lower:
        return "关于订单问题，您可以在订单查询页面查看订单状态，或联系客服热线400-123-4567。"
    elif "配送" in message_lower or "送餐" in message_lower:
        return "我们的配送时间通常在30-60分钟，具体时间根据距离和订单量而定。您可以在订单详情中查看预计送达时间。"
    elif "退款" in message_lower or "取消" in message_lower:
        return "如果需要取消订单或申请退款，请在订单页面操作，或联系我们的客服团队。"
    elif "地址" in message_lower:
        return "您可以在个人中心管理收货地址，确保配送信息准确无误。"
    else:
        return "您好！我是智能外卖平台的AI助手。如有任何问题，请详细描述，我会尽力帮助您！"

@app.route('/api/ai-conversations', methods=['GET'])
def get_ai_conversations():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code
    return jsonify({
        "conversations": [
            serialize_conversation_summary(conversation)
            for conversation in get_ai_conversations_for_user(user.get("id"))
        ]
    }), 200

@app.route('/api/ai-conversations', methods=['POST'])
def create_ai_conversation_api():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code
    data = request.get_json() or {}
    title = str(data.get("title", "")).strip() or "新对话"
    conversation = create_ai_conversation(user, title=title)
    return jsonify({"conversation": serialize_conversation_detail(conversation)}), 201

@app.route('/api/ai-conversations/<conversation_id>', methods=['GET'])
def get_ai_conversation_detail(conversation_id):
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code
    conversation = get_ai_conversation_by_id(conversation_id, user_id=user.get("id"))
    if not conversation:
        return jsonify({"error": "会话不存在。"}), 404
    return jsonify({"conversation": serialize_conversation_detail(conversation)}), 200

@app.route('/api/ai-agent', methods=['POST'])
@app.route('/api/chat', methods=['POST'])  # 兼容旧前端
def ai_agent():
    user, error_response, status_code = get_authenticated_user(required_roles=['customer'])
    if error_response:
        return error_response, status_code
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    image_url = data.get('image_url')
    history = data.get('history')
    conversation_id = (data.get('conversation_id') or '').strip()
    reset_context = bool(data.get('reset_context', False))
    session_id = request.headers.get('X-Session-ID') or (data.get('session_id') or '').strip()

    if not message and not image_url:
        return jsonify({"error": "消息不能为空。"}), 400

    if not message:
        message = "请识别这张图片并给出外卖相关建议。"

    conversation = get_ai_conversation_by_id(conversation_id, user_id=user.get("id")) if conversation_id else None
    if not conversation:
        initial_title = build_ai_conversation_title(message) if message and not image_url else "新对话"
        conversation = create_ai_conversation(user, title=initial_title)
        conversation_id = conversation.get("id")

    if reset_context:
        conversation["messages"] = []
        conversation["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        persist_data()

    stored_history = [
        {"role": item.get("role"), "content": item.get("content", "")}
        for item in conversation.get("messages", [])
    ]
    business_context = build_business_context_text(session_id=session_id)
    effective_history = [{"role": "system", "content": business_context}]

    image_recommendation_payload = None
    if image_url:
        image_context, image_err, image_recommendation_payload = build_image_recommendation_context(
            image_url,
            user_message=message,
            session_id=session_id or conversation_id
        )
        if image_context:
            effective_history.append({"role": "system", "content": image_context})
        elif image_err:
            print(f"图片识别检索上下文构建失败: {image_err}")

    # 客户端显式 history 优先，其次用服务端缓存 history
    if isinstance(history, list) and history:
        effective_history.extend(trim_conversation_history(history))
    else:
        effective_history.extend(trim_conversation_history(stored_history))

    response_text, err = call_remote_ai_api(
        message,
        image_url=image_url,
        history=effective_history,
        session_id=session_id or conversation_id
    )
    if response_text:
        mark_service_metric('ai_chat', success=True)
        final_response = response_text

        # 自动续写：当回答疑似被截断时，补 1~N 轮续写
        if REMOTE_AI_CONTINUE_ROUNDS > 0 and looks_like_truncated_answer(final_response):
            base_history = list(effective_history)
            continuation_prompt = "请紧接上一条回答继续完成，不要重复前文，不要输出思考过程。"

            for _ in range(REMOTE_AI_CONTINUE_ROUNDS):
                continuation_history = list(base_history)
                continuation_history.append({"role": "user", "content": message})
                continuation_history.append({"role": "assistant", "content": final_response})

                next_chunk, next_err = call_remote_ai_api(
                    continuation_prompt,
                    image_url=None,
                    history=continuation_history,
                    session_id=session_id or conversation_id
                )
                if not next_chunk:
                    if next_err:
                        print(f"AI续写失败: {next_err}")
                    break

                final_response = sanitize_ai_answer(merge_ai_chunks(final_response, next_chunk))
                if not looks_like_truncated_answer(final_response):
                    break

        if not conversation.get("messages"):
            conversation["title"] = build_ai_conversation_title(message)
        append_ai_conversation_message(conversation, "user", message)
        append_ai_conversation_message(conversation, "assistant", final_response)
        persist_data()

        return jsonify({
            "response": final_response,
            "source": "remote_api",
            "conversation_id": conversation_id,
            "conversation": serialize_conversation_summary(conversation),
            "recognized_text": (image_recommendation_payload or {}).get("recognized_text"),
            "recommendations": (image_recommendation_payload or {}).get("recommendation_cards", [])
        }), 200

    # 失败时回退到模拟回复，保证页面可用
    mark_service_metric('ai_chat', success=False)
    print(f"AI代理回退到模拟回复: {err}")
    fallback = generate_mock_response(message)
    if not conversation.get("messages"):
        conversation["title"] = build_ai_conversation_title(message)
    append_ai_conversation_message(conversation, "user", message)
    append_ai_conversation_message(conversation, "assistant", fallback)
    persist_data()
    return jsonify({
        "response": fallback,
        "source": "mock",
        "warning": err or "远程AI服务不可用，已回退模拟回复。",
        "conversation_id": conversation_id,
        "conversation": serialize_conversation_summary(conversation),
        "recognized_text": (image_recommendation_payload or {}).get("recognized_text"),
        "recommendations": (image_recommendation_payload or {}).get("recommendation_cards", [])
    }), 200

if __name__ == '__main__':
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    else:
        port = int(os.environ.get('PORT', port))

    flask_debug = os.environ.get('FLASK_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    app.run(
        debug=flask_debug,
        use_reloader=False,
        host='0.0.0.0',
        port=port,
    )
