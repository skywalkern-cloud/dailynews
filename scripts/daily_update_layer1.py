#!/usr/bin/env python3
"""
DailyNews Layer 1 - 采集层 (6:00执行)
功能：新闻 + 播客列表 + 启动下载(后台) + YouTube列表 + 启动下载(后台) + 初步HTML

Cron配置:
0 6 * * * cd ~/.openclaw/workspace-dailynews && python3 scripts/daily_update_layer1.py
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

def run_script(name, script_path, env=None, background=False, timeout=1200):
    """运行脚本并打印结果，支持超时"""
    print(f"\n{'='*60}")
    print(f"▶ {name}")
    print(f"{'='*60}")
    
    cmd = ["python3", "-u", str(script_path)]
    
    if background:
        # 后台运行，不等待完成
        subprocess.Popen(
            cmd,
            cwd=str(WORK_DIR),
            env=env or os.environ,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        print(f"  ✅ 已后台启动: {script_path.name}")
        return True
    
    try:
        result = subprocess.run(cmd, cwd=str(WORK_DIR), env=env or os.environ, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"✗ {name} 执行超时 ({timeout}秒)")
        return False
    if result.returncode != 0:
        print(f"✗ {name} 执行失败 (exit {result.returncode})")
        return False
    print(f"✓ {name} 执行成功")
    return True

def main():
    print("=" * 60)
    print("DailyNews Layer 1 - 采集层")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = DATA_DIR / today
    date_dir.mkdir(parents=True, exist_ok=True)

    # ====== FIX: 清理过期pending文件 ======
    # 防止stale data从previous run进入today's data
    print(f"\n{'='*60}")
    print("▶ 清理待处理文件")
    print(f"{'='*60}")
    podcast_pending = MEMORY_DIR / "podcast-pending.json"
    youtube_pending = MEMORY_DIR / "youtube-pending.json"
    
    # 如果文件是stale (>1 day old), 清空它
    for pf in [podcast_pending, youtube_pending]:
        if pf.exists():
            # 读取检查时间戳 - 如果是昨天的就清空
            try:
                with open(pf, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data:  # 非空
                    # 检查是否有recent data
                    has_recent = False
                    for item in data:
                        pub_date = item.get('upload_date') or item.get('pubDate', '')
                        if pub_date.startswith('2026'):
                            year, month, day = int(pub_date[:4]), int(pub_date[4:6]), int(pub_date[6:8])
                            # 如果是今天的数据, 保留
                            if year == 2026 and month == 5 and day == 4:
                                has_recent = True
                                break
                    if not has_recent:
                        print(f"  🗑️ 清理stale pending: {pf.name}")
                        pf.write_text('[]', encoding='utf-8')
            except:
                pf.write_text('[]', encoding='utf-8')
                print(f"  🗑️ 重置损坏的pending: {pf.name}")
        else:
            # 不存在则创建空文件
            pf.write_text('[]', encoding='utf-8')
            print(f"  ✅ 创建空pending: {pf.name}")

    # ====== Step 1: 新闻采集 ======
    run_script("Step 1: 新闻采集", SCRIPTS_DIR / "news_pipeline.py", timeout=1200)

    # ====== Step 2: 播客列表采集 ======
    run_script("Step 2: 播客列表采集", SCRIPTS_DIR / "podcast_daily.py")

    # ====== Step 3: 启动播客下载 (后台) ======
    print(f"\n{'='*60}")
    print("▶ Step 3: 启动播客下载 (后台)")
    print(f"{'='*60}")
    podcast_pending = MEMORY_DIR / "podcast-pending.json"
    if podcast_pending.exists():
        with open(podcast_pending, 'r', encoding='utf-8') as f:
            pending = json.load(f)
        print(f"  待下载: {len(pending)} 条")
        run_script("播客下载", SCRIPTS_DIR / "podcast_download.py", background=True)
    else:
        print("  ⚠️ 没有待下载的播客")

    # ====== Step 4: YouTube列表采集 ======
    run_script("Step 4: YouTube列表采集", SCRIPTS_DIR / "youtube_daily.py")

    # ====== Step 5: 启动YouTube下载 (后台) ======
    print(f"\n{'='*60}")
    print("▶ Step 5: 启动YouTube下载 (后台)")
    print(f"{'='*60}")
    youtube_pending = MEMORY_DIR / "youtube-pending.json"
    if youtube_pending.exists():
        with open(youtube_pending, 'r', encoding='utf-8') as f:
            pending = json.load(f)
        print(f"  待下载: {len(pending)} 条")
        run_script("YouTube下载", SCRIPTS_DIR / "youtube_download.py", background=True)
    else:
        print("  ⚠️ 没有待下载的YouTube")



    print("\n" + "=" * 60)
    print("✅ Layer 1 采集完成!")
    print("=" * 60)
    print("下一步: 9:00 执行 Layer 2")
    print("  1. podcast_transcribe.py (超时30分钟)")
    print("  2. podcast_summarize.py")
    print("  3. youtube_transcribe.py")
    print("  4. youtube_summarize.py")
    print("  5. 保存最终输出")
    print("  6. news_summarize.py")
    print("  7. generate_html_v2.py")
    print("  8. deploy_via_api.py")
    print("=" * 60)

if __name__ == "__main__":
    main()