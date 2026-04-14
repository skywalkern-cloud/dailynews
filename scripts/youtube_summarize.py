#!/usr/bin/env python3
"""
YouTube摘要生成脚本 - youtube_summarize.py
分批处理第4步：生成AI摘要
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 设置路径
SCRIPT_DIR = Path(__file__).parent
WORKSPACE = SCRIPT_DIR.parent
PENDING_FILE = WORKSPACE / "memory" / "youtube-pending.json"
DATA_DIR = WORKSPACE / "gh-pages" / "data"

sys.path.insert(0, str(SCRIPT_DIR))
from minimax_utils import generate_youtube_summary

def main():
    print("=" * 60)
    print("YouTube摘要生成脚本")
    print("=" * 60)
    
    if not PENDING_FILE.exists():
        print("❌ 没有待处理的YouTube视频")
        return
    
    with open(PENDING_FILE, encoding='utf-8') as f:
        pending = json.load(f)
    
    # 只处理有transcript但没有summary的
    to_summarize = [p for p in pending if p.get("transcript") and not p.get("summary")]
    
    if not to_summarize:
        print("✓ 没有待生成摘要的YouTube视频")
        return
    
    print(f"\n待生成摘要: {len(to_summarize)} 条")
    
    for i, ep in enumerate(to_summarize):
        print(f"\n[{i+1}/{len(to_summarize)}] {ep.get('title', '')[:50]}...")
        
        # 使用transcript生成摘要
        transcript = ep.get("transcript", "")
        summary = generate_youtube_summary(transcript)
        ep["summary"] = summary
        ep["summary_time"] = datetime.now().isoformat()
        print(f"    ✅ 摘要生成完成: {len(summary)}字")
    
    # 保存结果
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    
    # 生成最终输出
    print("\n生成最终输出文件...")
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 保存到gh-pages/data/{date}/youtube-data.json
    output_data = []
    for ep in pending:
        if ep.get("summary"):
            output_data.append({
                "id": ep.get("id"),
                "title": ep.get("title"),
                "url": ep.get("url"),
                "channel": ep.get("channel"),
                "summary": ep.get("summary"),
                "upload_date": ep.get("upload_date"),
                "fetched_at": datetime.now().isoformat(),
                "status": "summarized"
            })
    
    output_dir = DATA_DIR / today
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "youtube-data.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已保存到 {output_file}")
    
    # 清理pending文件
    PENDING_FILE.unlink()
    print("✅ 已清理临时文件")

if __name__ == "__main__":
    main()
