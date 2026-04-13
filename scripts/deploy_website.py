#!/usr/bin/env python3
"""
网站部署脚本 - deploy_website.py
功能：部署到Cloudflare Pages / GitHub
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-market-insight"))
GHPAGES_DIR = WORK_DIR / "gh-pages"

def deploy_to_cloudflare(project_name=None):
    """部署到Cloudflare Pages"""
    print("开始部署到Cloudflare Pages...")

    # 检查wrangler配置
    wrangler_path = WORK_DIR / "wrangler.toml"
    if not wrangler_path.exists():
        print("✗ 未找到wrangler.toml配置文件")
        return False

    # 执行部署
    try:
        cmd = ["wrangler", "pages", "deploy", str(GHPAGES_DIR)]
        if project_name:
            cmd.append(f"--project-name={project_name}")
        env = os.environ.copy()
        env["CLOUDFLARE_API_TOKEN"] = os.environ.get("CLOUDFLARE_API_TOKEN", "")

        result = subprocess.run(cmd, cwd=str(WORK_DIR), capture_output=True, text=True, env=env)

        if result.returncode == 0:
            print("✓ 部署成功!")
            print(result.stdout)
            return True
        else:
            print(f"✗ 部署失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ 部署异常: {e}")
        return False

def deploy_to_github():
    """提交到GitHub"""
    print("\n提交到GitHub...")

    try:
        # 检查git状态
        result = subprocess.run(["git", "status", "--short"], cwd=str(WORK_DIR), capture_output=True, text=True)

        if not result.stdout.strip():
            print("  无文件变更")
            return True

        # 添加文件
        subprocess.run(["git", "add", "-A"], cwd=str(WORK_DIR), capture_output=True)

        # 提交
        commit_msg = f"Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(WORK_DIR), capture_output=True)

        # 推送
        subprocess.run(["git", "push"], cwd=str(WORK_DIR), capture_output=True)

        print("✓ GitHub提交成功")
        return True
    except Exception as e:
        print(f"✗ GitHub提交失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="网站部署脚本")
    parser.add_argument(
        "--project-name",
        dest="project_name",
        default=None,
        help="Cloudflare Pages项目名称 (覆盖wrangler.toml中的配置)"
    )
    parser.add_argument(
        "target",
        nargs="?",
        choices=["github", "cloudflare", "all"],
        default="all",
        help="部署目标: github / cloudflare / all (默认: all)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("网站部署脚本 v1.0")
    print("=" * 60)

    if args.target in ["github", "all"]:
        deploy_to_github()

    if args.target in ["cloudflare", "all"]:
        deploy_to_cloudflare(args.project_name)

    print("\n✓ 部署完成!")

if __name__ == "__main__":
    main()
