#!/usr/bin/env python3
"""index.html v2.0 生成脚本 - 修复版
8个一级标签：今日必读、AI前沿、大国博弈、产业趋势、投资参考、全部新闻、播客、YouTube
"""
import json
import os
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
DATA_DIR = WORKSPACE / "gh-pages" / "data"

def get_available_dates():
    dates = []
    if DATA_DIR.exists():
        for d in sorted(DATA_DIR.iterdir(), reverse=True):
            if d.is_dir():
                try:
                    datetime.strptime(d.name, '%Y-%m-%d')
                    dates.append(d.name)
                except:
                    pass
    return dates

def load_json(filename, date):
    fpath = DATA_DIR / date / filename
    if fpath.exists():
        with open(fpath, encoding='utf-8') as f:
            return json.load(f)
    return None

def escape(text):
    if not text:
        return ''
    return text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'",'&#39;')

def gen_html(date):
    news = load_json('news.json', date) or {}
    podcasts = load_json('podcasts.json', date) or []
    youtube = load_json('youtube.json', date) or []
    
    # ====== 只显示最近7天的播客 ======
    from datetime import datetime
    now = datetime.now()
    def is_recent(item):
        fa = item.get('fetched_at', '')
        if not fa:
            return True
        try:
            dt = datetime.fromisoformat(fa.replace('Z', '+00:00')[:19])
            return (now - dt).days <= 6
        except:
            return True
    
    podcasts = [p for p in podcasts if is_recent(p)]
    youtube = [y for y in youtube if is_recent(y)]

    if isinstance(news, list):
        news = {'must-read': news}

    total = sum(len(v) for v in news.values() if isinstance(v, list))
    dates_avail = get_available_dates()
    today = datetime.now().strftime('%Y-%m-%d')

    refresh_time = now.strftime('%H:%M')

    # 今日必读 - 只取评分最高的前10条，改用垂直卡片列表
    all_items = []
    for cat, items in news.items():
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    item['_cat'] = cat
                    all_items.append(item)
    all_items.sort(key=lambda x: x.get('score', 0), reverse=True)
    top10 = all_items[:10]
    mr_html = ''
    for i, item in enumerate(top10):
        s = escape(item.get('summary_cn','') or item.get('ai_summary','') or item.get('summary',''))
        mr_html += (
            f'<div class="card must-read-card">'
            f'<span class="source-tag">{escape(item.get("source","新闻"))}</span>'
            f'<h4>{escape(item.get("title_cn") or item.get("title") or "")}</h4>'
            f'<p class="summary collapsed" data-full="{s}" onclick="toggleSummary(this)">{s}</p>'
            f'<a href="{escape(item.get("url","#"))}" target="_blank" class="link">阅读原文 →</a>'
            f'</div>'
        )

    # 播客卡片 - 摘要默认收起
    pod_html = ''
    for p in podcasts:
        s = escape(p.get('summary',''))
        pod_html += (
            f'<div class="card">'
            f'<span class="source-tag">🎧 {escape(p.get("source","播客"))}</span>'
            f'<h3>{escape(p.get("title",""))}</h3>'
            f'<p class="summary collapsed" data-full="{s}" onclick="toggleSummary(this)">{s}</p>'
            f'<a href="{escape(p.get("link","") or p.get("url","#"))}" target="_blank" class="link">收听 →</a>'
            f'</div>'
        )

    # YouTube卡片 - 摘要默认收起
    yt_html = ''
    for y in youtube:
        s = escape(y.get('summary',''))
        yt_html += (
            f'<div class="card">'
            f'<span class="source-tag">📺 {escape(y.get("channel", y.get("source","YouTube")))}</span>'
            f'<h3>{escape(y.get("title",""))}</h3>'
            f'<p class="summary collapsed" data-full="{s}" onclick="toggleSummary(this)">{s}</p>'
            f'<a href="{escape(y.get("url","") or y.get("link","#"))}" target="_blank" class="link">观看 →</a>'
            f'</div>'
        )

    news_js = json.dumps(news, ensure_ascii=False)

    css = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; line-height: 1.6; }
        header { background: linear-gradient(135deg, #1a1a2e 0pct, #16213e 100pct); color: white; padding: 0.8rem 1rem; position: sticky; top: 0; z-index: 100; }
        .header-content { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.2rem; font-weight: 700; }
        .refresh-time { font-size: 0.8rem; color: rgba(255,255,255,0.75); white-space: nowrap; }
        .tab-nav { background: white; border-bottom: 1px solid #e0e0e0; position: sticky; top: 56px; z-index: 99; }
        .tab-nav-inner { max-width: 1200px; margin: 0 auto; display: flex; flex-wrap: wrap; }
        .tab-btn { padding: 0.8rem 1.2rem; border: none; background: none; font-size: 0.9rem; cursor: pointer; border-bottom: 2px solid transparent; color: #666; }
        .tab-btn.active { color: #1a1a2e; border-bottom-color: #1a1a2e; font-weight: 600; }
        .container { max-width: 1200px; margin: 0 auto; padding: 1rem; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .must-read-card { }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
        .card { background: white; border-radius: 12px; padding: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
        .card h3, .card h4 { font-size: 0.95rem; margin-bottom: 0.4rem; line-height: 1.4; }
        .source-tag { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; background: #f0f0f5; color: #666; margin-bottom: 0.4rem; }
        .summary { color: #494949; font-size: 0.85rem; margin: 0.4rem 0; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
        .summary.collapsed { cursor: pointer; max-height: 3.6em; overflow: hidden; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }
        .summary.expanded { max-height: none; overflow: visible; display: block; }
        .summary.collapsed::after { content: '... 点击展开'; color: #007aff; display: block; margin-top: 0.2rem; font-size: 0.78rem; }
        .link { color: #007aff; text-decoration: none; font-size: 0.82rem; }
        .link:hover { text-decoration: underline; }
        .empty-state { text-align: center; padding: 3rem; color: #999; }
        footer { text-align: center; padding: 2rem; color: #666; font-size: 0.85rem; }
    """.replace('0pct','0%').replace('100pct','100%')

    # JS用普通字符串拼接，避免f-string与JS braces冲突
    js_parts = []
    js_parts.append("""
        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
        function toggleSummary(el) {
            if (el.classList.contains('collapsed')) {
                el.classList.remove('collapsed');
                el.classList.add('expanded');
                var full = el.getAttribute('data-full');
                if (full) { el.textContent = full; }
            } else {
                el.classList.remove('expanded');
                el.classList.add('collapsed');
                var full = el.getAttribute('data-full');
                if (full) { el.textContent = full; }
            }
        }
    """)
    js_parts.append(f"var newsData = {news_js};")
    js_parts.append("var currentTab = 'must-read';")
    js_parts.append("""
        function renderCategory(catId, items) {
            var container = document.getElementById(catId + 'Grid');
            if (!container) return;
            if (!items || items.length === 0) {
                container.innerHTML = '<div class="empty-state">暂无该分类内容</div>';
                return;
            }
            container.innerHTML = items.slice(0, 20).map(function(item) {
                var fullText = item.summary_cn || item.ai_summary || item.summary || '';
                var displayText = item.title_cn || item.title || '';
                var source = item.source || '新闻';
                var url = item.url || '#';
                return '<div class="card">' +
                    '<span class="source-tag">' + escapeHtml(source) + '</span>' +
                    '<h4>' + escapeHtml(displayText) + '</h4>' +
                    '<p class="summary collapsed" data-full="' + escapeHtml(fullText) + '" onclick="toggleSummary(this)">' + escapeHtml(fullText) + '</p>' +
                    '<a href="' + escapeHtml(url) + '" target="_blank" class="link">阅读原文 →</a>' +
                    '</div>';
            }).join('');
        }
    """)
    js_parts.append("""
        function renderSemiconductor() {
            var keywords = ['芯片','半导体','晶圆','台积电','英伟达','算力','光刻','刻蚀','封装','存储器','HBM','DRAM','先进制程','成熟制程','处理器','processor','晶圆厂','代工','制程','GPU','ASIC','FPGA','Chiplet','SoC','Silicon','Foundry','Wafer','Chip','AI chip'];
            var container = document.getElementById('semiconductorGrid');
            var seen = {};
            var items = [];
            for (var cat in newsData) {
                if (Array.isArray(newsData[cat])) {
                    newsData[cat].forEach(function(item) {
                        if (!item || !item.title) return;
                        if (seen[item.id]) return;
                        var title = (item.title || '').toLowerCase();
                        var matched = keywords.some(function(kw) { return title.indexOf(kw.toLowerCase()) !== -1; });
                        if (matched) {
                            seen[item.id] = true;
                            items.push(item);
                        }
                    });
                }
            }
            if (!items || items.length === 0) {
                container.innerHTML = '<div class="empty-state">暂无该分类内容</div>';
                return;
            }
            container.innerHTML = items.slice(0, 20).map(function(item) {
                var fullText = item.summary_cn || item.ai_summary || item.summary || '';
                var displayText = item.title_cn || item.title || '';
                var source = item.source || '新闻';
                var url = item.url || '#';
                return '<div class="card">' +
                    '<span class="source-tag">' + escapeHtml(source) + '</span>' +
                    '<h4>' + escapeHtml(displayText) + '</h4>' +
                    '<p class="summary collapsed" data-full="' + escapeHtml(fullText) + '" onclick="toggleSummary(this)">' + escapeHtml(fullText) + '</p>' +
                    '<a href="' + escapeHtml(url) + '" target="_blank" class="link">阅读原文 →</a>' +
                    '</div>';
            }).join('');
        }

        function renderAllNews() {
            var container = document.getElementById('allNewsGrid');
            var items = [];
            for (var cat in newsData) { if (Array.isArray(newsData[cat])) { items = items.concat(newsData[cat]); } }
            if (!items || items.length === 0) {
                container.innerHTML = '<div class="empty-state">暂无新闻</div>';
                return;
            }
            container.innerHTML = items.slice(0, 50).map(function(item) {
                var fullText = item.summary_cn || item.ai_summary || item.summary || '';
                var displayText = item.title_cn || item.title || '';
                var source = item.source || '新闻';
                var url = item.url || '#';
                return '<div class="card">' +
                    '<span class="source-tag">' + escapeHtml(source) + '</span>' +
                    '<h4>' + escapeHtml(displayText) + '</h4>' +
                    '<p class="summary collapsed" data-full="' + escapeHtml(fullText) + '" onclick="toggleSummary(this)">' + escapeHtml(fullText) + '</p>' +
                    '<a href="' + escapeHtml(url) + '" target="_blank" class="link">阅读原文 →</a>' +
                    '</div>';
            }).join('');
        }
    """)
    js_parts.append("""
        document.querySelectorAll('.tab-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var tab = this.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
                this.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
                document.getElementById('tab-' + tab).classList.add('active');
                currentTab = tab;
                if (tab === 'all-news') { renderAllNews(); }
                else if (tab === 'AI') { renderCategory('AI', newsData['AI前沿'] || []); }
                else if (tab === 'geo') { renderCategory('geo', newsData['大国博弈'] || []); }
                else if (tab === 'industry') { renderCategory('industry', newsData['产业趋势'] || []); }
                else if (tab === 'invest') { renderCategory('invest', newsData['投资参考'] || []); }
                else if (tab === 'semiconductor') { renderSemiconductor(); }
            });
        });
        window.addEventListener('DOMContentLoaded', function() {
            document.getElementById('tab-must-read').classList.add('active');
        });
    """)
    js = '\n'.join(js_parts)

    empty = '<div class="empty-state">暂无必读内容</div>' if not mr_html else mr_html
    empty_pod = '<div class="empty-state">今日暂无播客更新</div>' if not pod_html else pod_html
    empty_yt = '<div class="empty-state">今日暂无YouTube更新</div>' if not yt_html else yt_html

    tabs = """
<button class="tab-btn active" data-tab="must-read">📌 今日必读</button>
<button class="tab-btn" data-tab="AI">📡 AI前沿</button>
<button class="tab-btn" data-tab="geo">🌍 大国博弈</button>
<button class="tab-btn" data-tab="industry">🏭 产业趋势</button>
<button class="tab-btn" data-tab="invest">📈 投资参考</button>
<button class="tab-btn" data-tab="semiconductor">🔬 半导体</button>
<button class="tab-btn" data-tab="all-news">📰 全部新闻</button>
<button class="tab-btn" data-tab="podcast">🎧 播客</button>
<button class="tab-btn" data-tab="youtube">📺 YouTube</button>"""

    update_time = datetime.now().strftime('%H:%M')

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📰 每日资讯 {date}</title>
<style>{css}</style>
</head>
<body>
<header>
<div class="header-content">
<div class="logo">📰 每日资讯</div>
<div class="refresh-time">📅 {date} · 刷新 {refresh_time}</div>
</div>
</header>

<nav class="tab-nav">
<div class="tab-nav-inner">{tabs}
</div>
</nav>

<div class="container">
<div id="tab-must-read" class="tab-content active"><div class="card-grid">{empty}</div></div>
<div id="tab-AI" class="tab-content"><div class="card-grid" id="AIGrid"></div></div>
<div id="tab-geo" class="tab-content"><div class="card-grid" id="geoGrid"></div></div>
<div id="tab-industry" class="tab-content"><div class="card-grid" id="industryGrid"></div></div>
<div id="tab-invest" class="tab-content"><div class="card-grid" id="investGrid"></div></div>
<div id="tab-semiconductor" class="tab-content"><div class="card-grid" id="semiconductorGrid"></div></div>
<div id="tab-all-news" class="tab-content"><div class="card-grid" id="allNewsGrid"></div></div>
<div id="tab-podcast" class="tab-content"><div class="card-grid">{empty_pod}</div></div>
<div id="tab-youtube" class="tab-content"><div class="card-grid">{empty_yt}</div></div>
</div>

<footer><p>每日资讯 · 更新于 {update_time}</p></footer>
<script>{js}</script>
</body>
</html>"""

    out = WORKSPACE / 'gh-pages' / 'index.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)

    print('✅ index.html v2.0 已生成')
    print(f'   日期: {date}')
    print(f'   新闻: {total} 条')
    print(f'   播客: {len(podcasts)} 条')
    print(f'   YouTube: {len(youtube)} 条')
    print('   9个一级标签: 今日必读、AI前沿、大国博弈、产业趋势、投资参考、🔬半导体、全部新闻、播客、YouTube')

if __name__ == '__main__':
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    dates = get_available_dates()
    date = arg if arg in dates else (dates[0] if dates else datetime.now().strftime('%Y-%m-%d'))
    gen_html(date)
