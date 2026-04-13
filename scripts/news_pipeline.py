#!/usr/bin/env python3
"""
新闻抓取主脚本 - news_pipeline.py
功能：RSS新闻抓取 + AI摘要生成 + 输出到gh-pages/news.json
"""
import os
import sys
import json
import time
import uuid
import re
import feedparser
import requests
from datetime import datetime, timedelta
from pathlib import Path

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from minimax_utils import generate_news_summary, translate_to_chinese

# 配置
WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
CONFIG_DIR = WORK_DIR / "config"
GHPAGES_DIR = WORK_DIR / "gh-pages"
DATA_DIR = GHPAGES_DIR / "data"

# 加载配置
def load_config():
    with open(CONFIG_DIR / "sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)
    with open(CONFIG_DIR / "keywords.json", "r", encoding="utf-8") as f:
        keywords = json.load(f)
    with open(CONFIG_DIR / "weights.json", "r", encoding="utf-8") as f:
        weights = json.load(f)
    return sources, keywords, weights

def get_all_keywords(keywords_config):
    """获取所有关键词列表"""
    kw_list = keywords_config.get("keywords", {})
    all_kw = set()
    for lang_kws in kw_list.values():
        all_kw.update([k.lower() for k in lang_kws])
    return all_kw

def calculate_score(item, source_weight, keywords_set):
    """计算新闻评分"""
    score = 0
    title = item.get("title", "").lower()
    summary = item.get("summary", "").lower()
    
    # 关键词匹配
    for kw in keywords_set:
        if kw in title or kw in summary:
            score += 1
    
    # 来源权重
    score *= source_weight
    
    return score

def fetch_rss(source_name, url, timeout=10):
    """抓取单个RSS源"""
    try:
        print(f"  抓取 {source_name}...")
        # feedparser.parse() 不支持 timeout 参数，需要先用 requests 获取
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.encoding = 'utf-8'
        feed = feedparser.parse(response.text)
        
        if feed.bozo and not feed.entries:
            print(f"    ⚠️ 解析失败: {feed.bozo_exception}")
            return []
        
        now = datetime.now().isoformat()
        items = []
        for entry in feed.entries[:20]:  # 最多取20条
            # 清理HTML标签
            summary = entry.get("summary", "")
            if summary:
                summary = re.sub(r'<[^>]+>', '', summary)
                summary = re.sub(r'\s+', ' ', summary).strip()
            
            # 解析published_parsed为ISO时间
            published_at = ""
            if entry.get("published_parsed"):
                try:
                    pub_time = datetime(*entry["published_parsed"][:6])
                    published_at = pub_time.isoformat()
                except:
                    pass
            
            items.append({
                "id": str(uuid.uuid4()),
                "title": translate_to_chinese(entry.get("title", "").strip()),
                "source": source_name,
                "url": entry.get("link", ""),
                "summary": summary[:500],  # 限制摘要长度
                "published": entry.get("published", ""),
                "published_at": published_at,
                "published_parsed": entry.get("published_parsed", None),
                "fetched_at": now,
                "status": "new"
            })
        
        print(f"    ✓ 获取 {len(items)} 条")
        return items
    except Exception as e:
        print(f"    ✗ 失败: {e}")
        return []

def fetch_all_news(sources, keywords_set, weights):
    """抓取所有新闻源"""
    all_news = []
    news_sources = sources.get("news_sources", [])
    
    for source in news_sources:
        url = source.get("url")
        if not url:
            continue
        
        items = fetch_rss(source["name"], url)
        
        weight = weights.get("source_weights", {}).get(source["name"], 1)
        
        for item in items:
            score = calculate_score(item, weight, keywords_set)
            item["score"] = score
            item["category"] = source.get("category", "科技")
            
            # 计算时间衰减
            if item.get("published_parsed"):
                try:
                    pub_time = datetime(*item["published_parsed"][:6])
                    hours_ago = (datetime.now() - pub_time).total_seconds() / 3600
                    if hours_ago <= 24:
                        time_factor = 1.0
                    elif hours_ago <= 48:
                        time_factor = 0.95
                    elif hours_ago <= 72:
                        time_factor = 0.9
                    else:
                        time_factor = 0.8
                    item["score"] *= time_factor
                except:
                    pass
            
            all_news.append(item)
        
        time.sleep(1)  # 避免请求过快
    
    return all_news

def generate_ai_summaries(news_list):
    """为评分>=1的新闻生成AI摘要"""
    results = []
    ai_count = 0
    total = len(news_list)
    
    for i, item in enumerate(news_list):
        # P1-6: AI摘要阈值 score>=1
        score = item.get("score", 0)
        if score < 1:
            item["ai_summary"] = None
            item["status"] = "skipped"
            results.append(item)
            continue
        
        print(f"  AI摘要 {i+1}/{total}: {item['title'][:40]}... (score={score:.1f})")
        
        # 直接使用RSS原始摘要
        summary = item.get("summary", "")
        # 用AI生成摘要
        from minimax_utils import generate_news_summary, translate_to_chinese
        ai_summ = generate_news_summary(summary)
        # 确保AI摘要为中文：若英文占比超过30%则翻译
        if ai_summ:
            en_chars = sum(1 for c in ai_summ if ('A' <= c <= 'Z') or ('a' <= c <= 'z'))
            cn_chars = sum(1 for c in ai_summ if '\u4e00' <= c <= '\u9fff')
            if en_chars > 0 and cn_chars == 0:
                ai_summ = translate_to_chinese(ai_summ)
        item["ai_summary"] = ai_summ if ai_summ else summary
        item["status"] = "summarized"
        results.append(item)
        ai_count += 1
        
        time.sleep(0.5)  # 避免API限流
    
    print(f"  ✓ AI摘要生成完成 ({ai_count} 条触发阈值)")
    return results

def categorize_news(news_list, keywords_config):
    """按分类整理新闻"""
    categories = keywords_config.get("categories", {})
    
    categorized = {
        "must-read": [],
        "AI前沿": [],
        "大国博弈": [],
        "产业趋势": [],
        "投资参考": []
    }
    
    # 关键词匹配分类
    for item in news_list:
        title = item.get("title", "").lower()
        summary = item.get("summary", "").lower()
        text = title + " " + summary
        
        # 优先匹配must-read (高评分)
        if item.get("score", 0) >= 5:
            categorized["must-read"].append(item)
            continue
        
        # 按分类匹配
        assigned = False
        for cat_name, cat_config in categories.items():
            cat_keywords = [k.lower() for k in cat_config.get("keywords", [])]
            if any(kw in text for kw in cat_keywords):
                categorized[cat_name].append(item)
                assigned = True
                break
        
        if not assigned:
            categorized["must-read"].append(item)
    
    # 限制每个分类数量
    for cat in categorized:
        categorized[cat] = categorized[cat][:10]
    
    return categorized

def save_output(categorized_news):
    """保存输出文件"""
    # 创建日期目录
    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = DATA_DIR / today
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存news.json
    news_path = date_dir / "news.json"
    with open(news_path, "w", encoding="utf-8") as f:
        json.dump(categorized_news, f, ensure_ascii=False, indent=2)
    
    # 同时保存到gh-pages根目录
    root_path = GHPAGES_DIR / "news.json"
    with open(root_path, "w", encoding="utf-8") as f:
        json.dump(categorized_news, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 已保存到 {news_path}")
    print(f"✓ 已保存到 {root_path}")
    
    return str(news_path)

def deduplicate_news(news_list):
    """P2-7: 按URL去重"""
    seen_urls = set()
    deduped = []
    for item in news_list:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(item)
        elif not url:
            # 没有URL的也保留
            deduped.append(item)
    if len(news_list) > len(deduped):
        print(f"  ✓ 去重: {len(news_list)} -> {len(deduped)} 条")
    return deduped

def main():
    print("=" * 60)
    print("新闻抓取主脚本 v1.0")
    print("=" * 60)
    
    start_time = time.time()
    
    # 加载配置
    print("\n[1/4] 加载配置...")
    sources, keywords, weights = load_config()
    all_keywords = get_all_keywords(keywords)
    print(f"  已加载 {len(sources['news_sources'])} 个新闻源")
    print(f"  已加载 {len(all_keywords)} 个关键词")
    
    # 抓取新闻
    print("\n[2/4] 抓取新闻...")
    news_list = fetch_all_news(sources, all_keywords, weights)
    print(f"\n  共抓取 {len(news_list)} 条新闻")
    
    if not news_list:
        print("  ⚠️ 没有抓取到任何新闻")
        return
    
    # P2-7: 按URL去重
    print("\n  去重处理...")
    news_list = deduplicate_news(news_list)
    
    # 按评分排序
    news_list.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 生成AI摘要 (仅score>=1)
    print("\n[3/4] 生成AI摘要 (阈值: score>=1)...")
    news_with_ai = generate_ai_summaries(news_list)
    
    # 分类整理
    print("\n[4/4] 分类整理...")
    categorized = categorize_news(news_with_ai, keywords)
    
    # 统计
    total = sum(len(v) for v in categorized.values())
    print(f"  must-read: {len(categorized['must-read'])} 条")
    print(f"  AI前沿: {len(categorized['AI前沿'])} 条")
    print(f"  大国博弈: {len(categorized['大国博弈'])} 条")
    print(f"  产业趋势: {len(categorized['产业趋势'])} 条")
    print(f"  投资参考: {len(categorized['投资参考'])} 条")
    print(f"  总计: {total} 条")
    
    # 保存输出
    output_path = save_output(categorized)
    
    elapsed = time.time() - start_time
    print(f"\n✓ 完成! 耗时: {elapsed:.1f}秒")
    
    return output_path

if __name__ == "__main__":
    main()