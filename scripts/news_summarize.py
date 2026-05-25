#!/usr/bin/env python3
"""
AI摘要生成脚本 - news_summarize.py
功能：读取已抓取的新闻数据，生成AI摘要，输出到gh-pages
场景：Layer2(9:00) 调用，在news_pipeline.py抓取完成后执行
"""
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from minimax_utils import translate_to_chinese, generate_news_summary

# 配置
WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
GHPAGES_DIR = WORK_DIR / "gh-pages"
DATA_DIR = GHPAGES_DIR / "data"

def load_news_data():
    """加载最新日期的新闻数据"""
    # 找最新的日期目录
    if not DATA_DIR.exists():
        print(f"  ✗ 数据目录不存在: {DATA_DIR}")
        return None
    
    date_dirs = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    if not date_dirs:
        print(f"  ✗ 没有找到日期目录")
        return None
    
    latest_date = sorted(date_dirs, reverse=True)[0]
    news_path = latest_date / "news.json"
    
    if not news_path.exists():
        print(f"  ✗ 新闻文件不存在: {news_path}")
        return None
    
    print(f"  读取 {news_path}")
    with open(news_path, "r", encoding="utf-8") as f:
        return json.load(f), latest_date.name

def detect_language(text):
    """检测文本语言：返回 'en', 'zh', 或 'mixed'"""
    if not text:
        return 'en'
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_chars = sum(1 for c in text if 'A' <= c <= 'Z' or 'a' <= c <= 'z')
    if chinese_chars > english_chars * 0.5:
        return 'zh'
    return 'en'

def generate_ai_summaries(news_list):
    """为新闻生成摘要：英文翻译标题+摘要，中文直接用原摘要"""
    results = []
    translated_count = 0
    original_count = 0
    total = len(news_list)
    
    for i, item in enumerate(news_list):
        title = item.get("title", "")
        summary = item.get("summary", "")
        
        # 跳过已处理过的项目（status != "new"）
        if item.get("status") != "new" and item.get("ai_summary"):
            print(f"  跳过 {i+1}/{total}: 已处理 ({title[:40]}...)")
            results.append(item)
            continue
        
        lang = detect_language(summary)
        summary_len = len(summary)
        
        if lang == 'en':
            # 英文来源：翻译标题 + 翻译摘要（全文不截断）
            print(f"  处理 {i+1}/{total}: [EN] {title[:40]}... (摘要{summary_len}字)")
            try:
                item["title_cn"] = translate_to_chinese(title)
                time.sleep(0.5)
                if summary_len > 1500:
                    # 超长摘要：先调用AI生成精炼中文摘要（200字左右），再翻译
                    print(f"    📝 超长摘要({summary_len}字)，生成AI摘要后翻译...")
                    item["ai_summary"] = generate_news_summary(summary)
                else:
                    # 正常长度：直接完整翻译
                    item["ai_summary"] = translate_to_chinese(summary)
                item["status"] = "translated"
                print(f"    ✓ 标题翻译: {item.get('title_cn','')[:30]}...")
                print(f"    ✓ 摘要翻译完成: {len(item.get('ai_summary',''))}字")
                translated_count += 1
            except Exception as e:
                print(f"    ✗ 翻译失败: {e}")
                item["title_cn"] = title
                item["ai_summary"] = summary
                item["status"] = "fallback"
        else:
            # 中文来源：不翻译，直接用原始摘要（全文不截断）
            print(f"  处理 {i+1}/{total}: [ZH] {title[:40]}... (摘要{summary_len}字)")
            item["title_cn"] = None
            item["ai_summary"] = summary  # 保持全文，不截断
            item["status"] = "original"
            original_count += 1
            print(f"    ✓ 保持原样 ({summary_len}字)")
        
        results.append(item)
        time.sleep(1)  # 避免API限流
    
    print(f"  ✓ 处理完成 (英: {translated_count} 条, 中: {original_count} 条)")
    return results

def save_output(categorized_news, date_str):
    """保存输出文件"""
    # 保存到日期目录
    date_dir = DATA_DIR / date_str
    news_path = date_dir / "news.json"
    with open(news_path, "w", encoding="utf-8") as f:
        json.dump(categorized_news, f, ensure_ascii=False, indent=2)
    
    # 同时保存到gh-pages根目录
    root_path = GHPAGES_DIR / "news.json"
    with open(root_path, "w", encoding="utf-8") as f:
        json.dump(categorized_news, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 已保存到 {news_path}")
    print(f"✓ 已保存到 {root_path}")

def main():
    print("=" * 60)
    print("AI摘要生成脚本 v1.0")
    print("=" * 60)
    
    start_time = time.time()
    
    # 加载新闻数据
    print("\n[1/3] 加载新闻数据...")
    result = load_news_data()
    if not result:
        print("  ✗ 加载失败")
        return
    
    categorized, date_str = result
    
    # 统计当前状态
    total = sum(len(v) for v in categorized.values())
    summarized = sum(1 for v in categorized.values() for item in v if item.get("ai_summary"))
    print(f"  日期: {date_str}")
    print(f"  总条数: {total}")
    print(f"  已有摘要: {summarized}")
    
    # 展开所有新闻
    print("\n[2/3] 生成AI摘要...")
    all_news = []
    for cat_name, items in categorized.items():
        for item in items:
            item["category"] = cat_name
            all_news.append(item)
    
    # 生成摘要
    news_with_ai = generate_ai_summaries(all_news)
    
    # 重新分类整理
    print("\n[3/3] 重新整理分类...")
    categorized_new = {
        "must-read": [],
        "AI前沿": [],
        "大国博弈": [],
        "产业趋势": [],
        "投资参考": []
    }
    for item in news_with_ai:
        cat = item.get("category", "must-read")
        if cat in categorized_new:
            categorized_new[cat].append(item)
    
    # 限制每个分类数量
    for cat in categorized_new:
        categorized_new[cat] = categorized_new[cat][:10]
    
    # 统计
    total = sum(len(v) for v in categorized_new.values())
    summarized = sum(1 for v in categorized_new.values() for item in v if item.get("ai_summary"))
    print(f"  must-read: {len(categorized_new['must-read'])} 条")
    print(f"  AI前沿: {len(categorized_new['AI前沿'])} 条")
    print(f"  大国博弈: {len(categorized_new['大国博弈'])} 条")
    print(f"  产业趋势: {len(categorized_new['产业趋势'])} 条")
    print(f"  投资参考: {len(categorized_new['投资参考'])} 条")
    print(f"  总计: {total} 条 (已有摘要: {summarized})")
    
    # 保存输出
    save_output(categorized_new, date_str)
    
    elapsed = time.time() - start_time
    print(f"\n✓ 完成! 耗时: {elapsed:.1f}秒")

if __name__ == "__main__":
    main()