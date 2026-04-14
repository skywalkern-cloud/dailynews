#!/usr/bin/env python3
"""
Daily News 统一调度脚本 - daily_update.py
功能：依次执行新闻 → 播客 → YouTube → 生成HTML → 部署
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
SCRIPTS_DIR = WORK_DIR / "scripts"

def run_script(name, script_path, *args):
    """运行脚本并打印结果"""
    print(f"\n{'='*60}")
    print(f"▶ {name}")
    print(f"{'='*60}")
    
    cmd = ["python3", str(script_path)] + list(args)
    result = subprocess.run(cmd, cwd=str(WORK_DIR))
    
    if result.returncode != 0:
        print(f"✗ {name} 执行失败 (exit {result.returncode})")
        return False
    print(f"✓ {name} 执行成功")
    return True

def main():
    print("=" * 60)
    print(f"Daily News 更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    steps = [
        ("Step 1: 新闻采集", SCRIPTS_DIR / "news_pipeline.py"),
        ("Step 2: 播客采集", SCRIPTS_DIR / "podcast_daily.py"),
        ("Step 3: YouTube采集", SCRIPTS_DIR / "youtube_daily.py"),
        ("Step 4: 生成HTML", SCRIPTS_DIR / "generate_html_v2.py"),
        ("Step 5: 部署到GitHub", SCRIPTS_DIR / "deploy_website.py"),
    ]

    for step_name, script_path in steps:
        if not run_script(step_name, script_path):
            print(f"\n✗ 流程中断于: {step_name}\")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ Daily News 更新全部完成!")
    print(f"  访问: https://dailynews.pages.dev")
    print("=" * 60)

if __name__ == "__main__":
    main()
