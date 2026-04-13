# Daily News 项目完整设计方案

**版本**：v1.0 | **日期**：2026-04-12 | **作者**：龙六

---

## 一、项目概述

### 1.1 目标
打造一个个人每日资讯聚合平台，自动采集新闻、播客、YouTube 内容，生成静态网站并部署上线。

### 1.2 项目目录
```
~/.openclaw/workspace-dailynews/
```

**⚠️ 重要提醒**：彻底忘掉 workspace-market-insight，本项目只用 workspace-dailynews。

---

## 二、技术架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│  OpenClaw Cron (6:00-6:30)                                         │
│  scripts/daily_update.py                                            │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1: scripts/news_pipeline.py                                   │
│  → gh-pages/news.json                                               │
│  → gh-pages/data/YYYY-MM-DD/news.json                              │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Step 2: scripts/podcast_daily.py                                   │
│  → gh-pages/podcast-data.json                                       │
│  → gh-pages/data/YYYY-MM-DD/podcasts.json                          │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Step 3: scripts/youtube_daily.py                                   │
│  → gh-pages/youtube-data.json                                       │
│  → gh-pages/data/YYYY-MM-DD/youtube.json                           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Step 4: scripts/generate_html_v21.py                              │
│  → gh-pages/index.html                                              │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Step 5: GitHub Push → Cloudflare 自动部署                          │
│  → git add gh-pages/ → commit → push                              │
│  → GitHub 触发 Cloudflare Pages webhook                            │
│  → Cloudflare 自动构建并部署                                        │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
                    https://dailynews.pages.dev
```

### 2.2 数据流

```
RSS源 (20+)  ──→  news_pipeline.py  ──→  news.json
小宇宙API   ──→  podcast_daily.py   ──→  podcast-data.json
YouTube API ──→  youtube_daily.py   ──→  youtube-data.json
                                                      ↓
                                              generate_html_v21.py
                                                      ↓
                                               index.html
                                                      ↓
                                               gh-pages/
                                                      ↓
                                                 GitHub Push
                                                      ↓
                                            Cloudflare Pages 自动部署
                                                      ↓
                                               dailynews.pages.dev
```

---

## 三、GitHub + Cloudflare 部署方案

### 3.1 整体流程

```
workspace-dailynews/  ──→  GitHub 仓库  ──→  Cloudflare Pages
       │                      │                      │
       │ git push             │ GitHub webhook      │ 自动构建
       ↓                      ↓                      ↓
   gh-pages/           skywalkern-cloud/      dailynews.pages.dev
   (静态文件)           /dailynews
                       (gh-pages 分支)
```

### 3.2 GitHub 仓库设计

**仓库名**：`skywalkern-cloud/dailynews`

**分支策略**：

| 分支 | 用途 | 内容 |
|:---|:---|:---|
| **master** | 开发分支 | 源代码、脚本、配置（不包含 gh-pages 数据） |
| **gh-pages** | 生产分支 | 纯静态网站文件（index.html、*.json、data/） |

**工作流**：
1. 代码开发在 master 分支
2. 定时任务执行时，将 gh-pages/ 目录的内容同步到 gh-pages 分支并 push
3. Cloudflare 检测到 gh-pages 更新，自动构建部署

### 3.3 .gitignore 设计

```
# 忽略 gh-pages 目录里的数据文件（不需要版本控制）
gh-pages/*.json
gh-pages/data/

# 保留 index.html（可能需要版本控制）
# gh-pages/index.html

# 忽略临时文件
*.log
*.tmp
.DS_Store
```

**说明**：每天的数据文件不需要在 Git 里版本化（太大且无意义），只需要 index.html 等静态资源。

### 3.4 Git 操作流程

```bash
# 场景：每天定时任务触发 deploy

# 1. 切换到 gh-pages 分支
git checkout gh-pages

# 2. 用 gh-pages/ 目录的内容覆盖根目录
# （因为 gh-pages 分支只有静态文件，没有脚本和配置）
cp -r gh-pages/* .

# 3. Git add + commit + push
git add .
git commit -m "Update: $(date '+%Y-%m-%d %H:%M')"
git push origin gh-pages
```

### 3.5 Cloudflare Pages 配置

| 配置项 | 值 |
|:---|:---|
| Project name | `dailynews` |
| Production branch | `gh-pages` |
| 构建命令 | 留空（纯静态） |
| 构建输出目录 | `/` |
| 部署方式 | 连接到 GitHub 自动触发 |

**触发逻辑**：
- GitHub push 到 gh-pages 分支
- GitHub 发送 webhook 到 Cloudflare
- Cloudflare 拉取最新代码并部署
- 约 1-5 分钟生效

---

## 四、实施步骤

### Phase 0：准备（老板操作）

#### Step 0.1：创建 GitHub 仓库

1. 打开 https://github.com/new
2. Repository name: `dailynews`
3. Private
4. **不要勾选** Initialize with README
5. Create repository

#### Step 0.2：Cloudflare Pages 连接 GitHub

1. 进入 https://dash.cloudflare.com/pages
2. Create a project → Import Git repository
3. 连接 `skywalkern-cloud/dailynews`
4. 配置：
   - Project name: `dailynews`
   - Production branch: `gh-pages`
   - 构建命令：留空
   - 构建输出目录：`/`
5. 创建并部署

---

### Phase 1：初始化 Git + 修复 Bug（我来执行）

#### Step 1.1：初始化 Git 仓库

```bash
cd ~/.openclaw/workspace-dailynews
git init
git add .
git commit -m "Initial commit - 2026-04-12"
git remote add origin https://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@github.com/skywalkern-cloud/dailynews.git
git push -u origin master
```

#### Step 1.2：创建 .gitignore

创建 `~/.openclaw/workspace-dailynews/.gitignore`：

```
# gh-pages 数据文件（不需要版本控制）
gh-pages/*.json
gh-pages/data/

# 临时文件
*.log
*.tmp
.DS_Store
```

#### Step 1.3：创建 gh-pages orphan 分支

```bash
cd ~/.openclaw/workspace-dailynews
git checkout --orphan gh-pages
git rm -rf .
git add .gitignore
git commit -m "Initial gh-pages branch"
git push origin gh-pages
```

---

### Phase 2：代码修复 + 新建统一调度脚本（我来执行）

#### Step 2.1：修复 deploy_website.py 的路径 bug

**文件**：`scripts/deploy_website.py`

**第12行**：
```python
# 错误 ❌
WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-market-insight"))

# 正确 ✅
WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
```

#### Step 2.2：修改 deploy_website.py 部署逻辑

**当前问题**：
- 直接 `wrangler pages deploy`
- 不走 GitHub

**改为**：
```python
def deploy_to_github():
    """将 gh-pages 内容推送到 GitHub gh-pages 分支"""
    import shutil
    
    try:
        # 切换到 gh-pages 分支
        subprocess.run(["git", "checkout", "gh-pages"], cwd=str(WORK_DIR), capture_output=True)
        
        # 用 gh-pages/ 目录覆盖根目录
        gh_pages_src = WORK_DIR / "gh-pages"
        for item in gh_pages_src.iterdir():
            if item.name == ".git":
                continue
            dest = WORK_DIR / item.name
            if dest.is_dir():
                shutil.rmtree(dest)
            elif dest.exists():
                dest.unlink()
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        
        # Git add
        subprocess.run(["git", "add", "."], cwd=str(WORK_DIR), capture_output=True)
        
        # 检查是否有变更
        result = subprocess.run(["git", "status", "--short"], cwd=str(WORK_DIR), capture_output=True, text=True)
        if not result.stdout.strip():
            print("  无变更，跳过部署")
            return True
        
        # Commit
        commit_msg = f"Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(WORK_DIR), capture_output=True)
        
        # Push
        result = subprocess.run(
            ["git", "push", "origin", "gh-pages"],
            cwd=str(WORK_DIR),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ GitHub push 成功，Cloudflare 将自动构建")
            return True
        else:
            print(f"✗ GitHub push 失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ 部署异常: {e}")
        return False
```

#### Step 2.3：修改 main() 函数

**移除** `deploy_to_cloudflare()` 调用，只保留 `deploy_to_github()`

#### Step 2.4：创建统一调度脚本

**文件**：`scripts/daily_update.py`（新建）

```python
#!/usr/bin/env python3
"""
每日统一更新脚本 - daily_update.py
依次执行：新闻 → 播客 → YouTube → 生成HTML → 部署
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

WORK_DIR = Path("~/.openclaw/workspace-dailynews").expanduser()

def run_script(name, script_path, timeout=300):
    """运行单个脚本"""
    print(f"\n{'='*60}")
    print(f"▶ {name}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(WORK_DIR),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            print(f"✓ {name} 完成")
            return True
        else:
            print(f"✗ {name} 失败")
            if result.stderr:
                print(f"  {result.stderr[-300:]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ {name} 超时 ({timeout}s)")
        return False
    except Exception as e:
        print(f"✗ {name} 异常: {e}")
        return False

def main():
    print("=" * 60)
    print("每日统一更新脚本")
    print("=" * 60)
    
    scripts = [
        ("新闻采集", "scripts/news_pipeline.py"),
        ("播客采集", "scripts/podcast_daily.py"),
        ("YouTube采集", "scripts/youtube_daily.py"),
        ("生成HTML", "scripts/generate_html_v21.py"),
    ]
    
    for name, path in scripts:
        success = run_script(name, WORK_DIR / path)
        if not success:
            print(f"\n⚠️ {name} 失败，继续执行后续步骤")
    
    # 部署
    print(f"\n{'='*60}")
    print("▶ 部署到 GitHub")
    print(f"{'='*60}")
    
    result = subprocess.run(
        [sys.executable, str(WORK_DIR / "scripts/deploy_website.py")],
        cwd=str(WORK_DIR),
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    print("\n✓ 完成!")

if __name__ == "__main__":
    main()
```

---

## 五、文件结构

### 5.1 GitHub 仓库最终结构

**master 分支**：
```
dailynews/
├── scripts/
│   ├── news_pipeline.py
│   ├── podcast_daily.py
│   ├── youtube_daily.py
│   ├── generate_html_v21.py
│   ├── deploy_website.py     ← 已修复路径 bug
│   ├── daily_update.py       ← 新建，统一调度
│   └── minimax_utils.py
├── config/
│   ├── sources.json
│   ├── keywords.json
│   └── weights.json
├── memory/
│   └── podcast-tracker.json
├── gh-pages/                  ← 参考目录，不在 master 根
├── .gitignore
└── README.md
```

**gh-pages 分支**：
```
/  (根目录 = Cloudflare 构建输出目录)
├── index.html
├── news.json
├── podcast-data.json
├── youtube-data.json
└── data/
    └── 2026-04-12/
        ├── news.json
        ├── podcasts.json
        └── youtube.json
```

---

## 六、现有脚本代码评审

### 6.1 deploy_website.py（需修复）

| 问题 | 严重性 | 修复 |
|:---|:---:|:---|
| WORK_DIR 路径错误 | 🔴 致命 | 改为 `workspace-dailynews` |
| deploy_to_cloudflare() 直接 wrangler deploy | 🟡 中等 | 改为 git push |
| deploy_to_github() 用了错误的 WORK_DIR | 🔴 致命 | 随上一条一起修 |
| main() 同时调用 cloudflare + github | 🟡 中等 | 改为只调用 github |

### 6.2 daily_update.py（需新建）

| 需求 | 说明 |
|:---|:---|
| 串起 4 个采集脚本 | news → podcast → youtube → generate_html |
| 错误处理 | 单个失败不中断整个流程 |
| 最后调用 deploy | 统一部署 |

### 6.3 其他脚本（暂不修改）

- `news_pipeline.py` - 暂不需要改
- `podcast_daily.py` - 暂不需要改
- `youtube_daily.py` - 暂不需要改
- `generate_html_v21.py` - 暂不需要改

---

## 七、验证检查清单

| # | 检查项 | 验证方式 | 负责人 |
|:---:|:---|:---|:---:|
| 1 | GitHub 仓库 `dailynews` 已创建 | github.com 确认 | 老板 |
| 2 | Cloudflare Pages 已连接 GitHub | Cloudflare Dashboard 确认 | 老板 |
| 3 | git init 完成 | `git remote -v` 确认 | 我 |
| 4 | .gitignore 已创建 | 文件存在确认 | 我 |
| 5 | gh-pages orphan 分支已推送 | `git log gh-pages` 确认 | 我 |
| 6 | deploy_website.py 路径已修复 | 代码检查 | 我 |
| 7 | deploy_website.py 逻辑已修改 | 代码检查 | 我 |
| 8 | daily_update.py 已创建 | 文件存在确认 | 我 |
| 9 | 手动触发成功 | 运行脚本 + 检查输出 | 我 |
| 10 | GitHub commit 存在 | github.com 确认 | 我 |
| 11 | Cloudflare 构建成功 | Cloudflare Dashboard 确认 | 老板 |
| 12 | 网站可访问 | 浏览器打开 dailynews.pages.dev | 老板 |

---

## 八、执行顺序

```
【Phase 0 - 准备】（老板操作）
Step 0.1: GitHub 创建空仓库
Step 0.2: Cloudflare 连接 GitHub
         ↓
【Phase 1 - 初始化】（我操作）
Step 1.1: git init + remote + push
Step 1.2: 创建 .gitignore
Step 1.3: 创建 gh-pages orphan 分支
         ↓
【Phase 2 - 代码修复】（我操作）
Step 2.1: 修复 deploy_website.py 路径 bug
Step 2.2: 修改 deploy_website.py 部署逻辑
Step 2.3: 修改 main() 函数
Step 2.4: 创建 daily_update.py
         ↓
【Phase 3 - 验证】（我操作）
Step 3.1: 手动触发完整流程
Step 3.2: 检查清单验证
         ↓
【Phase 4 - Cron】（我操作）
配置每日 6:00 定时任务
```
