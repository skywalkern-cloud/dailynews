#!/usr/bin/env python3
"""
新闻抓取主脚本 - news_pipeline.py
功能：RSS新闻抓取 + 去重 + 分类 + 评分（纯采集，无AI摘要）
AI摘要由 Layer2 的 news_summarize.py 统一生成
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
from dotenv import load_dotenv
from minimax_utils import translate_to_chinese

# 英文来源列表（需要翻译）
EN_SOURCES = {
    "Bloomberg", "Financial Times", "BBC", "CNN", "The Guardian",
    "Reuters", "Wired", "MIT Technology Review", "VentureBeat",
    "Stratechery", "Noah Smith", "Off the Chain"
}

# 中文来源列表（不需要翻译）
ZH_SOURCES = {
    "36氪", "第一财经", "虎嗅", "创业邦", "爱范儿", "晚点",
    "机器之心", "极客公园", "品玩", "腾讯科技", "新浪科技", "财新", "少数派"
}

# 加载 .env 环境变量
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

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
            
            # 翻译处理：英文来源翻译标题和摘要，中文来源保持原样
            title_cn = summary_cn = None
            raw_title = entry.get("title", "").strip()
            # 【FIX】不要截断摘要，保存全文供后续翻译使用
            raw_summary = summary
            if source_name in EN_SOURCES:
                time.sleep(0.3)  # 控制频率避免限流
                title_cn = translate_to_chinese(raw_title)
                time.sleep(0.3)
                # Layer1翻译摘要是初步翻译，Layer2的news_summarize.py会再次翻译全文
                # 【FIX】不要截断，传入完整原文供翻译（translate_to_chinese内部已支持分段翻译）
                summary_cn = translate_to_chinese(raw_summary) if raw_summary else ""
            elif source_name in ZH_SOURCES:
                # 中文来源：title和summary已经是中文
                title_cn = raw_title
                summary_cn = raw_summary
            
            items.append({
                "id": str(uuid.uuid4()),
                "title": raw_title,
                "source": source_name,
                "url": entry.get("link", ""),
                "summary": raw_summary,
                "title_cn": title_cn,
                "summary_cn": summary_cn,
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

def fetch_playwright(source_name, url, timeout=30):
    """通过Playwright浏览器抓取动态页面"""
    try:
        print(f"  抓取 {source_name} (Playwright)...")
        from playwright.sync_api import sync_playwright
        
        articles = []
        seen = set()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(url, timeout=timeout*1000, wait_until='domcontentloaded')
            page.wait_for_timeout(5000)
            
            # 找新闻链接
            patterns = [
                'a[href*="/news/"]',
                'a[href*="/article/"]',
                'a[href*="/p/"]',
            ]
            
            for pattern in patterns:
                links = page.query_selector_all(pattern)
                for link in links[:50]:  # 最多50条
                    title = link.inner_text().strip()
                    href = link.get_attribute('href') or ''
                    
                    # 过滤非新闻链接
                    if not title or len(title) < 10:
                        continue
                    if '/news/' not in href and '/article/' not in href and '/p/' not in href:
                        continue
                    # 跳过专题/视频/直播等
                    skip_words = ['video', 'live', 'special', 'topic', 'column', 'vip', 'about', 'contact']
                    if any(w in href.lower() for w in skip_words):
                        continue
                    
                    if href not in seen:
                        seen.add(href)
                        full_url = href if href.startswith('http') else url.rstrip('/') + href
                        articles.append({
                            "id": str(uuid.uuid4()),
                            "title": title,
                            "source": source_name,
                            "url": full_url,
                            "summary": "",
                            "title_cn": title if source_name in ZH_SOURCES else None,
                            "summary_cn": "",
                            "published": "",
                            "published_at": "",
                            "published_parsed": None,
                            "fetched_at": datetime.now().isoformat(),
                            "status": "new"
                        })
                if articles:
                    break
            
            browser.close()
        
        print(f"    ✓ 获取 {len(articles)} 条")
        return articles
        
    except ImportError:
        print(f"    ✗ Playwright未安装")
        return []
    except Exception as e:
        print(f"    ✗ Playwright失败: {e}")
        return []

def fetch_huxiu_mobile():
    """通过手机版抓取虎嗅"""
    try:
        print(f"  抓取 虎嗅 (手机版)...")
        from playwright.sync_api import sync_playwright
        
        articles = []
        seen = set()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
                viewport={'width': 390, 'height': 844},
                is_mobile=True,
            )
            page = context.new_page()
            
            page.goto('https://m.huxiu.com/', timeout=30000)
            page.wait_for_timeout(8000)
            
            all_links = page.query_selector_all('a')
            for link in all_links:
                href = link.get_attribute('href') or ''
                if '/article/' in href and href not in seen:
                    title = link.inner_text().strip()
                    if title and len(title) > 10:
                        seen.add(href)
                        full_url = href if href.startswith('http') else 'https://m.huxiu.com' + href
                        articles.append({
                            "id": str(uuid.uuid4()),
                            "title": title,
                            "source": "虎嗅",
                            "url": full_url,
                            "summary": "",
                            "title_cn": title,  # 虎嗅是中文来源
                            "summary_cn": "",
                            "published": "",
                            "published_at": "",
                            "published_parsed": None,
                            "fetched_at": datetime.now().isoformat(),
                            "status": "new"
                        })
            
            browser.close()
        
        print(f"    ✓ 获取 {len(articles)} 条")
        return articles
        
    except Exception as e:
        print(f"    ✗ 失败: {e}")
        return []

def fetch_latepost_playwright():
    """通过Playwright抓取晚点"""
    try:
        print(f"  抓取 晚点 (Playwright)...")
        from playwright.sync_api import sync_playwright
        
        articles = []
        seen = set()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto('https://www.latepost.com/', timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(5000)
            
            # 尝试多种选择器
            for sel in ['h3 a', 'h2 a', '.title a', '[href*="/news/"]']:
                links = page.query_selector_all(sel)
                for link in links[:30]:
                    href = link.get_attribute('href') or ''
                    if '/news/' in href and href not in seen:
                        title = link.inner_text().strip()
                        if title and len(title) > 10:
                            seen.add(href)
                            full_url = href if href.startswith('http') else 'https://www.latepost.com' + href
                            articles.append({
                                "id": str(uuid.uuid4()),
                                "title": title,
                                "source": "晚点",
                                "url": full_url,
                                "summary": "",
                                "title_cn": title,  # 晚点是中文来源
                                "summary_cn": "",
                                "published": "",
                                "published_at": "",
                                "published_parsed": None,
                                "fetched_at": datetime.now().isoformat(),
                                "status": "new"
                            })
                if articles:
                    break
            
            browser.close()
        
        print(f"    ✓ 获取 {len(articles)} 条")
        return articles
        
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
        
        # 根据method选择抓取方式
        method = source.get("method", "rss")
        
        if method == "playwright":
            items = fetch_playwright(source["name"], url)
        elif method == "huxiu_mobile":
            items = fetch_huxiu_mobile()
        elif method == "latepost_playwright":
            items = fetch_latepost_playwright()
        else:
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

def _is_ai_related(text, categories):
    """严格判断是否AI强相关（不含通用词和地缘政治）"""
    ai_kws = categories.get('AI前沿', {}).get('keywords', [])
    ai_kws_lower = [k.lower() for k in ai_kws]
    # 地缘政治污染词（如果出现且没有真正的AI技术词，则不算AI）
    geo_noise = ['iran', 'ukraine', 'russia', 'china-us', 'china us', 'taiwan', 'nato', 
                'ceasefire', 'sanction', 'trade war', 'middle east', 'hormuz', 'opec',
                '原油', '油价', '美元', '美联储', '收益率', '债券']
    geo_match = any(g in text for g in geo_noise)
    # 必须有关键词匹配，且忽略短词
    ai_match = any(k in text for k in ai_kws_lower if len(k) > 2)
    # 如果是地缘政治新闻，即使含通用AI词也不算AI前沿
    if geo_match:
        # 真正的AI新闻应该包含AI技术词，而不只是AI这个字
        real_ai_kws = ['openai', 'anthropic', 'deepmind', 'nvidia', 'amd', 'llm', 'gpt-', 
                       'chatgpt', 'aigc', '人形机器人', 'humanoid', 'large language',
                       'generative', 'multimodal', 'AI chip', 'AI agent', 'world model',
                       'quantum computing', 'machine learning', 'neural']
        if not any(k in text for k in real_ai_kws):
            return False
    return ai_match

def _is_geo_related(text, categories):
    """判断是否大国博弈相关"""
    geo_kws = categories.get('大国博弈', {}).get('keywords', [])
    geo_kws_lower = [k.lower() for k in geo_kws]
    return any(k in text for k in geo_kws_lower if len(k) > 2)

def categorize_news(news_list, keywords_config):
    """按分类整理新闻 - 优先级分类，同一条新闻只进一个分类，避免重复"""
    categories = keywords_config.get('categories', {})
    
    categorized = {
        "must-read": [],
        "AI前沿": [],
        "大国博弈": [],
        "产业趋势": [],
        "投资参考": []
    }
    
    assigned_urls = set()  # 防止重复分配
    
    for item in news_list:
        title = item.get("title", "").lower()
        summary = item.get("summary", "").lower()
        text = title + " " + summary
        url = item.get("url", "")
        
        # 跳过已分配的新闻
        if url in assigned_urls and url:
            continue
        
        # 优先级1: AI前沿（最严格，必须是AI技术相关，不含地缘政治）
        if _is_ai_related(text, categories):
            categorized["AI前沿"].append(item)
            assigned_urls.add(url)
            continue
        
        # 优先级2: 大国博弈
        if _is_geo_related(text, categories):
            categorized["大国博弈"].append(item)
            assigned_urls.add(url)
            continue
        
        # 优先级3-4: 产业趋势、投资参考
        assigned = False
        for cat_name in ["产业趋势", "投资参考"]:
            cat_kws = [k.lower() for k in categories.get(cat_name, {}).get('keywords', [])]
            if any(k in text for k in cat_kws if len(k) > 2):
                categorized[cat_name].append(item)
                assigned_urls.add(url)
                assigned = True
                break
        
        if not assigned:
            categorized["must-read"].append(item)
            if url:
                assigned_urls.add(url)
    
    # 【FIX】must-read = 英文5条 + 中文5条，按score排序
    # 从全部新闻中选，不排除任何板块
    english_sources = {
        "Bloomberg", "Financial Times", "BBC", "CNN", "The Guardian",
        "Reuters", "Wired", "MIT Technology Review", "VentureBeat",
        "WSJ", "The Information", "Stratechery", "Noah Smith"
    }
    
    # 按score降序
    sorted_news = sorted(news_list, key=lambda x: x.get('score', 0), reverse=True)
    
    english_news = [item for item in sorted_news
                    if item.get('source', '') in english_sources][:5]
    chinese_news = [item for item in sorted_news
                    if item.get('source', '') not in english_sources][:5]
    
    must_read_items = english_news + chinese_news
    must_read_ids = {id(item) for item in must_read_items}
    
    # 用新的must-read替换老的
    categorized["must-read"] = must_read_items
    
    # 从其他板块中移除已在must-read中的文章，避免重复
    for cat in ["AI前沿", "大国博弈", "产业趋势", "投资参考"]:
        categorized[cat] = [item for item in categorized[cat] if id(item) not in must_read_ids]
    
    # 限制其他分类数量
    for cat in ["产业趋势", "投资参考"]:
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
    print("\n[1/3] 加载配置...")
    sources, keywords, weights = load_config()
    all_keywords = get_all_keywords(keywords)
    print(f"  已加载 {len(sources['news_sources'])} 个新闻源")
    print(f"  已加载 {len(all_keywords)} 个关键词")
    
    # 抓取新闻
    print("\n[2/3] 抓取新闻...")
    news_list = fetch_all_news(sources, all_keywords, weights)
    print(f"\n  共抓取 {len(news_list)} 条新闻")
    
    if not news_list:
        print("  ⚠️ 没有抓取到任何新闻")
        return
    
    # 按URL去重
    print("\n  去重处理...")
    news_list = deduplicate_news(news_list)
    
    # 按评分排序
    news_list.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 分类整理（AI摘要由Layer2的news_summarize.py统一生成）
    print("\n[3/3] 分类整理...")
    categorized = categorize_news(news_list, keywords)
    
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
    print(f"  注: AI摘要由 Layer2 的 news_summarize.py 生成")
    
    return output_path

if __name__ == "__main__":
    main()