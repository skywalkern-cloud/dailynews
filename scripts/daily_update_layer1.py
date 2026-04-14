#!/usr/bin/env python3
"""
DailyNews Layer 1 - 采集层 (6:00执行)
功能：新闻 + 播客列表 + YouTube抓取 + 生成HTML + 部署

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

def run_script(name, script_path, env=None, background=False):
    """运行脚本并打印结果"""
    print(f"\n{'='*60}")
    print(f"▶ {name}")
    print(f"{'='*60}")
    
    cmd = ["python3", str(script_path)]
    
    if background:
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
    
    result = subprocess.run(cmd, cwd=str(WORK_DIR), env=env or os.environ)
    
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

    # 环境变量
    fetch_env = os.environ.copy()
    fetch_env["FETCH_ONLY"] = "true"

    # ====== Step 1: 新闻采集 ======
    run_script("Step 1: 新闻采集", SCRIPTS_DIR / "news_pipeline.py")

    # ====== Step 2: 播客列表采集 (FETCH_ONLY) ======
    run_script("Step 2: 播客列表采集", SCRIPTS_DIR / "podcast_daily.py", env=fetch_env)
    # 注意：不再需要后台下载，直接在Layer2用description生成摘要

    # ====== Step 3: YouTube抓取 + AI摘要 (后台运行) ======
    print(f"\n{'='*60}")
    print("▶ Step 3: YouTube抓取+摘要 (后台)")
    print(f"{'='*60}")
    run_script("YouTube抓取+摘要", SCRIPTS_DIR / "youtube_daily.py", background=True)

    # ====== Step 4: 生成初步HTML ======
    run_script("Step 4: 生成初步HTML", SCRIPTS_DIR / "generate_html_v2.py")
    
    # ====== Step 5: 初步部署 ======
    run_script("Step 5: 初步部署", SCRIPTS_DIR / "deploy_website.py")

    print("\n" + "=" * 60)
    print("✅ Layer 1 采集完成!")
    print("=" * 60)
    print("下一步: 9:00 执行 Layer 2")
    print("  1. podcast_summarize.py (用description生成摘要)")
    print("  2. generate_html_v2.py")
    print("  3. deploy_website.py")
    print("=" * 60)

if __name__ == "__main__":
    main()