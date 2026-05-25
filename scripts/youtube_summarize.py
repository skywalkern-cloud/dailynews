#!/usr/bin/env python3
"""
YouTube摘要生成脚本 - youtube_summarize.py
功能：用transcript生成AI摘要
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
from minimax_utils import generate_youtube_summary, translate_to_chinese

def main():
    print("=" * 60)
    print("YouTube摘要生成脚本")
    print("=" * 60)
    
    if not PENDING_FILE.exists():
        print("❌ 没有待处理的YouTube")
        return
    
    with open(PENDING_FILE, encoding='utf-8') as f:
        pending = json.load(f)
    
    # 只处理有transcript或description但没有summary的
    to_summarize = [p for p in pending if (p.get("transcript") or p.get("description")) and not p.get("summary")]
    
    if not to_summarize:
        print("✓ 没有待生成摘要的视频")
        return
    
    print(f"\n待生成摘要: {len(to_summarize)} 条")
    
    for i, ep in enumerate(to_summarize):
        print(f"\n[{i+1}/{len(to_summarize)}] {ep.get('title', '')[:50]}...")
        
        # 使用transcript或description生成摘要
        transcript = ep.get("transcript", "") or ep.get("description", "")
        
        # 如果没有transcript（纯description fallback）且内容不足500字，标记失败不调用AI
        is_description_only = not ep.get("transcript")
        if is_description_only and len(transcript.strip()) < 500:
            ep["summary"] = "[音频下载失败，无法生成摘要]"
            ep["summary_time"] = datetime.now().isoformat()
            print(f"    ⚠️ 音频下载失败，description仅{len(transcript.strip())}字，跳过AI生成")
            continue
        
        summary = generate_youtube_summary(transcript)
        
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
    
    output_data = []
    for ep in pending:
        if ep.get("summary"):
            output_data.append({
                "id": ep.get("id"),
                "title": ep.get("title"),
                "source": ep.get("source"),
                "channel": ep.get("channel"),
                "link": ep.get("url"),
                "summary": ep.get("summary"),
                "pubDate": ep.get("upload_date"),
                "published_at": ep.get("upload_date"),
                "fetched_at": datetime.now().isoformat(),
                "status": "summarized",
                "summary_source": "whisper" if ep.get("transcript") else "rss_description",
                "word_count": len(ep.get("summary", ""))
            })
    
    output_dir = DATA_DIR / today
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "youtube.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已保存到 {output_file}")
    print(f"   共 {len(output_data)} 条数据")

if __name__ == "__main__":
    main()