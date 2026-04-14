#!/usr/bin/env python3
"""
播客摘要生成脚本 - podcast_summarize.py
功能：直接用description生成AI摘要（跳过下载/转录）
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 设置路径
SCRIPT_DIR = Path(__file__).parent
WORKSPACE = SCRIPT_DIR.parent
PENDING_FILE = WORKSPACE / "memory" / "podcast-pending.json"
DATA_DIR = WORKSPACE / "gh-pages" / "data"

sys.path.insert(0, str(SCRIPT_DIR))
from minimax_utils import generate_podcast_summary, translate_to_chinese

def main():
    print("=" * 60)
    print("播客摘要生成脚本 (优化版)")
    print("=" * 60)
    
    if not PENDING_FILE.exists():
        print("❌ 没有待处理的播客")
        return
    
    with open(PENDING_FILE, encoding='utf-8') as f:
        pending = json.load(f)
    
    # 只处理有description但没有summary的
    to_summarize = [p for p in pending if p.get("description") and not p.get("summary")]
    
    if not to_summarize:
        print("✓ 没有待生成摘要的播客")
        return
    
    print(f"\n待生成摘要: {len(to_summarize)} 条")
    
    for i, ep in enumerate(to_summarize):
        print(f"\n[{i+1}/{len(to_summarize)}] {ep.get('title', '')[:50]}...")
        
        # 直接用description生成摘要（跳过下载/转录）
        description = ep.get("description", "")
        summary = generate_podcast_summary(description)
        
        # 翻译成中文
        summary_cn = translate_to_chinese(summary)
        
        ep["summary"] = summary_cn
        ep["summary_time"] = datetime.now().isoformat()
        print(f"    ✅ 摘要生成完成: {len(summary_cn)}字")
    
    # 保存结果
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    
    # 生成最终输出
    print("\n生成最终输出文件...")
    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = DATA_DIR / today
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_data = []
    for ep in pending:
        if ep.get("summary"):
            output_data.append({
                "id": ep.get("id"),
                "title": ep.get("title"),
                "source": ep.get("source"),
                "link": ep.get("link"),
                "summary": ep.get("summary"),
                "pubDate": ep.get("pubDate"),
                "published_at": ep.get("pubDate"),
                "fetched_at": datetime.now().isoformat(),
                "status": "summarized",
                "summary_source": "description",
                "word_count": len(ep.get("summary", ""))
            })
    
    output_file = output_dir / "podcasts.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已保存 {len(output_data)} 条到 {output_file}")

if __name__ == "__main__":
    main()