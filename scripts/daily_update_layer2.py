#!/usr/bin/env python3
"""
DailyNews Layer 2 - 处理层 (9:00执行)
功能：播客摘要 + 生成HTML + 部署

Cron配置:
0 9 * * * cd ~/.openclaw/workspace-dailynews && python3 scripts/daily_update_layer2.py
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
SCRIPTS_DIR = WORK_DIR / "scripts"
MEMORY_DIR = WORK_DIR / "memory"
DATA_DIR = WORK_DIR / "gh-pages" / "data"

PODCAST_PENDING = MEMORY_DIR / "podcast-pending.json"

# 超时配置
SUMMARIZE_TIMEOUT = 600    # 10分钟

def run_script(name, script_path, timeout=None):
    """运行脚本并打印结果，支持超时"""
    print(f"\n{'='*60}")
    print(f"▶ {name}")
    print(f"{'='*60}")
    
    cmd = ["python3", str(script_path)]
    try:
        result = subprocess.run(cmd, cwd=str(WORK_DIR), timeout=timeout)
        if result.returncode != 0:
            print(f"✗ {name} 执行失败 (exit {result.returncode})")
            return False
        print(f"✓ {name} 执行成功")
        return True
    except subprocess.TimeoutExpired:
        print(f"✗ {name} 执行超时 ({timeout}秒)")
        return False

def save_pending_to_json(pending_file, output_file, transform_fn):
    """将pending数据保存到最终输出"""
    if not pending_file.exists():
        print(f"  ⚠️ {pending_file.name} 不存在")
        return 0
    
    with open(pending_file, 'r', encoding='utf-8') as f:
        pending = json.load(f)
    
    output_data = [transform_fn(ep) for ep in pending if ep.get('summary')]
    
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    return len(output_data)

def main():
    print("=" * 60)
    print("DailyNews Layer 2 - 处理层")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = DATA_DIR / today

    # ====== Step 1: 播客摘要 (直接用description，无需转录) ======
    run_script("Step 1: 播客摘要 (优化版)", 
               SCRIPTS_DIR / "podcast_summarize.py", 
               timeout=SUMMARIZE_TIMEOUT)

    # ====== Step 2: 保存最终输出 ======
    print(f"\n{'='*60}")
    print("Step 2: 保存最终输出")
    print(f"{'='*60}")
    
    # 播客
    if PODCAST_PENDING.exists():
        podcast_count = save_pending_to_json(
            PODCAST_PENDING,
            output_dir / "podcasts.json",
            lambda ep: {
                'id': ep.get('id', ''),
                'title': ep.get('title', ''),
                'source': ep.get('source', ''),
                'link': ep.get('link', ''),
                'summary': ep.get('summary', ''),
                'pubDate': ep.get('pubDate', ''),
                'published_at': ep.get('pubDate', ''),
                'fetched_at': datetime.now().isoformat(),
                'status': 'summarized',
                'word_count': len(ep.get('summary', ''))
            }
        )
        print(f"  ✅ 播客: {podcast_count} 条")
    else:
        print("  ⚠️ 播客pending不存在")
    
    # YouTube数据来自Layer 1的youtube_daily.py
    youtube_file = output_dir / "youtube.json"
    if youtube_file.exists():
        with open(youtube_file, 'r', encoding='utf-8') as f:
            yt_data = json.load(f)
        print(f"  ✅ YouTube: {len(yt_data)} 条")
    else:
        # 尝试从根目录复制
        root_youtube = WORK_DIR / "gh-pages" / "youtube-data.json"
        if root_youtube.exists():
            with open(root_youtube, 'r', encoding='utf-8') as f:
                yt_data = json.load(f)
            output_dir.mkdir(parents=True, exist_ok=True)
            with open(youtube_file, 'w', encoding='utf-8') as f:
                json.dump(yt_data, f, ensure_ascii=False, indent=2)
            print(f"  ✅ YouTube: {len(yt_data)} 条")

    # ====== Step 3: 生成完整HTML ======
    run_script("Step 3: 生成完整HTML", SCRIPTS_DIR / "generate_html_v2.py")

    # ====== Step 4: 部署到GitHub ======
    run_script("Step 4: 部署到GitHub", SCRIPTS_DIR / "deploy_website.py")

    print("\n" + "=" * 60)
    print("✅ Layer 2 处理完成!")
    print(f"  输出目录: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()