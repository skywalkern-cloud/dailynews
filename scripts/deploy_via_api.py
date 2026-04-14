#!/usr/bin/env python3
"""
GitHub API部署脚本
"""
import os
import base64
import requests
from pathlib import Path

REPO_OWNER = "skywalkern-cloud"
REPO_NAME = "dailynews"
BRANCH = "gh-pages"
GH_TOKEN = os.environ.get("GH_TOKEN", "")

if not GH_TOKEN:
    print("❌ 需要设置 GH_TOKEN 环境变量")
    exit(1)

WORK_DIR = Path("~/.openclaw/workspace-dailynews").expanduser()
GHPAGES_DIR = WORK_DIR / "gh-pages"

def get_sha(path):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    r = requests.get(url, headers={"Authorization": f"token {GH_TOKEN}"}, params={"ref": BRANCH})
    return r.json().get("sha") if r.status_code == 200 else None

def upload(fp, path):
    with open(fp, "rb"):
        content = base64.b64encode(open(fp, "rb").read()).decode()
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    data = {"message": f"Deploy {path}", "content": content, "branch": BRANCH}
    if sha := get_sha(path):
        data["sha"] = sha
    r = requests.put(url, headers={"Authorization": f"token {GH_TOKEN}"}, json=data)
    print(f"  {'✅' if r.status_code in [200,201] else '❌'} {path}")
    return r.status_code in [200, 201]

print("开始部署...")
files = [(Path(r)/p, str(p)) for r,_,fs in os.walk(GHPAGES_DIR) for p in fs if p!=".DS_Store"]
print(f"共 {len(files)} 个文件")
for fp, rp in files:
    upload(fp, rp)
print("完成")