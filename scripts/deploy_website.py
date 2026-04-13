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

WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
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
    """提交到GitHub gh-pages分支 → Cloudflare Pages自动部署"""
    print("\n提交到GitHub (gh-pages)...")

    try:
        # 1. 切换到 gh-pages 分支
        result = subprocess.run(["git", "checkout", "gh-pages"], cwd=str(WORK_DIR), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"✗ 切换gh-pages分支失败: {result.stderr}")
            return False
        print("  ✓ 已切换到 gh-pages 分支")

        # 2. 用 gh-pages/ 目录的内容覆盖根目录
        import shutil
        for item in GHPAGES_DIR.iterdir():
            if item.name == '.git':
                continue
            dest = WORK_DIR / item.name
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            elif dest.exists() and not dest.is_symlink():
                dest.unlink()
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        print("  ✓ gh-pages/ 内容已覆盖根目录")

        # 3. 检查变更
        result = subprocess.run(["git", "status", "--short"], cwd=str(WORK_DIR), capture_output=True, text=True)
        if not result.stdout.strip():
            print("  无文件变更")
            return True

        # 4. Git add + commit + push
        subprocess.run(["git", "add", "."], cwd=str(WORK_DIR), capture_output=True)
        commit_msg = f"Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(WORK_DIR), capture_output=True)
        subprocess.run(["git", "push", "origin", "gh-pages"], cwd=str(WORK_DIR), capture_output=True)

        print("✓ GitHub gh-pages 推送成功 → Cloudflare Pages 将自动部署")
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
        choices=["github"],
        default="github",
        help="部署目标: github / cloudflare / all (默认: all)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("网站部署脚本 v1.0")
    print("=" * 60)

    if args.target in ["github", "all"]:
        deploy_to_github()

    print("\n✓ 部署完成!")

if __name__ == "__main__":
    main()
