# DailyNews 项目状态报告

**更新时间**: 2026-04-12 22:30

---

## 项目概述

DailyNews 是一个新闻聚合网站，从多个来源抓取新闻、播客、YouTube内容，生成带AI摘要的HTML页面。

**项目目录**: ~/.openclaw/workspace-dailynews/

---

## 当前状态

### 数据文件

| 文件 | 大小 | 更新时间 |
|------|------|----------|
| gh-pages/index.html | 572KB | 2026-04-12 21:49 |
| gh-pages/data/2026-04-12/news.json | 35KB | 2026-04-12 22:12 |
| gh-pages/data/2026-04-12/podcasts.json | 334KB | 2026-04-12 19:05 |
| gh-pages/data/2026-04-12/youtube.json | 451KB | 2026-04-12 16:10 |

### 统计数据
- 新闻: 31条
- 播客: 86条
- YouTube: 70条
- 标签: 8个一级标签

---

## 功能特性

### 8个一级标签
1. 今日必读
2. AI前沿
3. 大国博弈
4. 产业趋势
5. 投资参考
6. 全部新闻
7. 播客
8. YouTube

### 摘要收起/展开
- 所有摘要默认收起
- 点击"展开阅读"按钮显示完整内容
- 使用data-full属性存储完整摘要内容

### 标题翻译
- 使用minimax_utils.py中的translate_to_chinese函数
- maxOutputTokens已从150增加到500
- 确保完整翻译不截断

---

## 脚本说明

### 核心脚本

| 脚本 | 功能 |
|------|------|
| news_pipeline.py | 抓取新闻数据并翻译标题和摘要 |
| podcast_daily.py | 抓取播客RSS并生成AI摘要 |
| youtube_daily.py | 抓取YouTube视频并生成AI摘要 |
| generate_html_v2.py | 生成HTML页面 |

### Tracker文件
- memory/podcast-tracker.json - 记录上次抓取的最新播客
- memory/youtube-tracker.json - 记录上次抓取的最新视频

**Tracker逻辑**: 保存episodes[-1]（最旧的）作为cutoff，下次运行遇到该标题就停止

---

## 已修复的Bug

### Bug 1: 标题翻译截断
- **问题**: maxOutputTokens=150太小，翻译被截断（如"中"、"两艘超级油"）
- **修复**: 增加到500
- **文件**: scripts/minimax_utils.py

### Bug 2: 摘要收起功能
- **问题**: toggleSummary只切换class，不切换内容
- **修复**: 添加data-full属性存储完整内容，toggle时用data-full内容替换显示
- **文件**: scripts/generate_html_v2.py

### Bug 3: 每日必读筛选
- **问题**: 所有新闻都被放进must-read
- **修复**: 按score排序取前10条
- **文件**: scripts/generate_html_v2.py

---

## 邮件配置

**发件邮箱**: fiveloong5@163.com
**授权码**: BGVqCuAUzCc3cmnT
**SMTP服务器**: smtp.163.com:465 (SSL)
**收件人**: vincent_nie@foxmail.com

---

## 本地测试

- **本地服务**: `cd gh-pages && python3 -m http.server 8080`
- **测试URL**: http://localhost:8080

---

## 团队成员

| 成员 | 角色 |
|------|------|
| 龙五（我） | 项目经理 |
| 龙六 | 设计+验收 |
| 扣钉 | 前端开发 |
| 泰斯特 | 测试 |

---

## 待办事项

- [ ] 龙六编写设计文档
- [ ] 设计文档评审
- [ ] 代码评审
- [ ] 部署方案
- [ ] cron定时任务

---

## 经验教训

1. **测试在部署前**: 本地npm run dev预览确认正常后才能部署
2. **正确平台**: 当前项目部署在Cloudflare Pages，不是Vercel
3. **龙五不写代码**: 只分配和验收
4. **翻译token设置**: maxOutputTokens要足够大，避免截断
5. **Tracker立即保存**: check_updates后就保存，避免被kill丢失进度
6. **邮箱配置要记住**: fiveloong5@163.com + 授权码
