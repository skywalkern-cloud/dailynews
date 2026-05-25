#!/usr/bin/env python3
"""
GitHub API部署脚本 - deploy_via_api.py
使用GitHub API代替git push方式部署
"""
import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
from datetime import datetime

# 配置
REPO_OWNER = "skywalkern-cloud"
REPO_NAME = "dailynews"
BRANCH = "gh-pages"
GH_TOKEN = os.environ.get("GH_TOKEN", "")

if not GH_TOKEN:
    print("❌ 请设置 GH_TOKEN 环境变量")
    exit(1)

WORK_DIR = Path("~/.openclaw/workspace-dailynews").expanduser()
GHPAGES_DIR = WORK_DIR / "gh-pages"

# 跳过特殊文件
SKIP_FILES = [".DS_Store"]

def get_file_sha(repo_path):
    """获取文件的SHA用于更新"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{repo_path}"
    headers = {"Authorization": f"token {GH_TOKEN}"}
    params = {"ref": BRANCH}  # 指定分支
    r = requests.get(url, headers=headers, params=params)
    if r.status_code == 200:
        return r.json().get("sha")
    return None

def upload_file(file_path, repo_path):
    """上传单个文件到GitHub"""
    # 跳过特殊文件
    if file_path.name in SKIP_FILES:
        print(f"  ⏭️ 跳过: {repo_path}")
        return True
    
    # 使用二进制模式读取所有文件
    try:
        with open(file_path, "rb") as f:
            content = f.read()
    except Exception as e:
        print(f"  ❌ 读取失败: {repo_path} - {e}")
        return False
    
    b64_content = base64.b64encode(content).decode("utf-8")
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{repo_path}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "message": f"Deploy: {file_path.name}",
        "content": b64_content,
        "branch": BRANCH
    }
    
    sha = get_file_sha(repo_path)
    if sha:
        data["sha"] = sha
    
    r = requests.put(url, headers=headers, json=data)
    if r.status_code in [200, 201]:
        print(f"  ✅ {repo_path}")
        return True
    else:
        print(f"  ❌ {repo_path}: {r.status_code}")
        return False

def main():
    print("=" * 60)
    print("GitHub API部署脚本")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if not GHPAGES_DIR.exists():
        print(f"❌ gh-pages目录不存在: {GHPAGES_DIR}")
        return
    
    # 获取所有文件
    files = []
    for root, dirs, filenames in os.walk(GHPAGES_DIR):
        for f in filenames:
            full_path = Path(root) / f
            rel_path = full_path.relative_to(GHPAGES_DIR)
            repo_path = str(rel_path)
            files.append((full_path, repo_path))
    
    print(f"\n待上传: {len(files)} 个文件")
    
    success = 0
    failed = 0
    
    for full_path, repo_path in files:
        if upload_file(full_path, repo_path):
            success += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    if failed == 0:
        print(f"✅ 部署完成! 成功: {success}")
    else:
        print(f"⚠️ 部分失败: 成功 {success}, 失败 {failed}")
    print("=" * 60)

if __name__ == "__main__":
    main()