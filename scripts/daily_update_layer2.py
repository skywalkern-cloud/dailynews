#!/usr/bin/env python3
"""
DailyNews Layer 2 - 处理层 (9:00执行)
功能：转录 + 摘要 + 生成完整HTML + 部署

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
GHPAGES_DIR = WORK_DIR / "gh-pages"

PODCAST_PENDING = MEMORY_DIR / "podcast-pending.json"
YOUTUBE_PENDING = MEMORY_DIR / "youtube-pending.json"

# 超时配置
TRANSCRIBE_TIMEOUT = 1800  # 30分钟
SUMMARIZE_TIMEOUT = 600    # 10分钟

def run_script(name, script_path, timeout=None):
    """运行脚本并打印结果，支持超时"""
    print(f"\n{'='*60}")
    print(f"▶ {name}")
    print(f"{'='*60}")
    
    cmd = ["python3", "-u", str(script_path)]
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
    
    if not pending:
        print(f"  ⚠️ {pending_file.name} 为空")
        return 0
    
    # ====== FIX: 只处理最近7天的数据 ======
    # 支持多种日期格式解析
    def parse_date_to_days_ago(date_str):
        """解析日期字符串，返回(days_ago, success)。解析失败返回(None, False)"""
        if not date_str:
            return None, False
        # 格式1: YYYYMMDD 或 YYYY-MM-DD (YouTube)
        if len(date_str) >= 8 and date_str[:4].isdigit():
            try:
                dt = datetime(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
                return (datetime.now() - dt).days, True
            except:
                pass
        # 格式2: RFC 2822 (播客 RSS, e.g. "Fri, 01 May 2026 21:37:00 +0000")
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str).replace(tzinfo=None)
            return (datetime.now() - dt).days, True
        except:
            pass
        return None, False

    recent_data = []
    stale_data = []
    for ep in pending:
        pub_date = ep.get('upload_date') or ep.get('pubDate', '') or ''
        fetched_at = ep.get('fetched_at', '')
        
        days_ago, parsed = parse_date_to_days_ago(pub_date)
        if not parsed:
            # 无法解析pubDate，用fetched_at兜底
            days_ago, parsed = parse_date_to_days_ago(fetched_at)
        
        if not parsed:
            # 仍然无法解析：默认进recent（避免误删新内容）
            recent_data.append(ep)
        elif days_ago <= 7:
            recent_data.append(ep)
        else:
            stale_data.append(ep)
    
    if stale_data:
        print(f"  ⏭️ 跳过stale数据: {len(stale_data)}条")
    
    output_data = [transform_fn(ep) for ep in recent_data if ep.get('summary')]
    
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ====== 去重逻辑：合并历史数据 ======
    # 读取已有的gh-pages播客数据（当天），按 (source, title) 去重
    existing = []
    if output_file.name == "podcasts.json" or output_file.name == "youtube.json":
        if output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except:
                existing = []
    
    # 按 (source, title) 去重，新的覆盖旧的
    key_map = {}
    for p in existing:
        key = (p.get('source', ''), p.get('title', ''))
        key_map[key] = p
    for p in output_data:
        key = (p.get('source', ''), p.get('title', ''))
        key_map[key] = p
    
    all_items = list(key_map.values())
    all_items.sort(key=lambda x: x.get('fetched_at', ''), reverse=True)
    all_items = all_items[:50]  # 保留最新50条
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    
    # 【重要】同时更新根目录文件，确保日期过滤一致
    root_file = GHPAGES_DIR / output_file.name
    with open(root_file, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    
    return len(output_data)

def main():
    print("=" * 60)
    print("DailyNews Layer 2 - 处理层")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = DATA_DIR / today

    # ====== Step 1: 播客转录 (超时30分钟保护) ======
    run_script("Step 1: 播客转录 (超时30分钟)", 
               SCRIPTS_DIR / "podcast_transcribe.py", 
               timeout=TRANSCRIBE_TIMEOUT)

    # ====== Step 2: 播客摘要 (超时10分钟保护) ======
    run_script("Step 2: 播客摘要", 
               SCRIPTS_DIR / "podcast_summarize.py", 
               timeout=SUMMARIZE_TIMEOUT)

    # ====== Step 3: YouTube转录 (超时30分钟保护) ======
    run_script("Step 3: YouTube转录 (超时30分钟)", 
               SCRIPTS_DIR / "youtube_transcribe.py", 
               timeout=TRANSCRIBE_TIMEOUT)

    # ====== Step 4: YouTube摘要 (超时10分钟保护) ======
    run_script("Step 4: YouTube摘要", 
               SCRIPTS_DIR / "youtube_summarize.py", 
               timeout=SUMMARIZE_TIMEOUT)

    # ====== Step 5: 保存最终输出 ======
    print(f"\n{'='*60}")
    print("▶ Step 5: 保存最终输出")
    print(f"{'='*60}")
    
    # 播客
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
    
    # 【重要】处理完成后清除pending文件
    if podcast_count > 0 and PODCAST_PENDING.exists():
        PODCAST_PENDING.write_text('[]', encoding='utf-8')
        print(f"  🧹 已清除 pending 文件")
    
    # YouTube
    youtube_count = save_pending_to_json(
        YOUTUBE_PENDING,
        output_dir / "youtube.json",
        lambda ep: {
            'id': ep.get('id', ''),
            'title': ep.get('title', ''),
            'source': ep.get('source', ''),
            'channel': ep.get('channel', ''),
            'link': ep.get('url', ''),
            'summary': ep.get('summary', ''),
            'pubDate': ep.get('upload_date', ''),
            'published_at': ep.get('upload_date', ''),
            'fetched_at': datetime.now().isoformat(),
            'status': 'summarized',
            'word_count': len(ep.get('summary', ''))
        }
    )
    print(f"  ✅ YouTube: {youtube_count} 条")

    # ====== Step 6: 新闻AI摘要 ======
    # 将英文新闻的summary翻译成中文（生成ai_summary字段）
    run_script("Step 6: 新闻AI摘要(翻译)", SCRIPTS_DIR / "news_summarize.py", timeout=3600)

    # ====== Step 7: 生成完整HTML ======
    run_script("Step 7: 生成完整HTML", SCRIPTS_DIR / "generate_html_v2.py")

    # ====== Step 8: 部署到GitHub ======
    run_script("Step 8: 部署到GitHub", SCRIPTS_DIR / "deploy_via_api.py")

    print("\n" + "=" * 60)
    print("✅ Layer 2 处理完成!")
    print(f"  输出目录: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()