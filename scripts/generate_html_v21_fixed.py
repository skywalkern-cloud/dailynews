#!/usr/bin/env python3
"""index.html v2.0 生成脚本"""
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
    
    if isinstance(news, list):
        news = {'must-read': news}
    
    total = sum(len(v) for v in news.values() if isinstance(v, list))
    dates = get_available_dates()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 日期选项
    opts = ''
    for d in sorted(dates, reverse=True):
        sel = ' selected' if d == date else ''
        label = '今天' if d == today else d
        opts += '<option value="{}"{}>{}</option>'.format(d, sel, label)
    
    # 今日必读
    mr_html = ''
    for i, item in enumerate(news.get('must-read', [])[:10]):
        mr_html += '<div class="must-read-card"><div class="rank">{}</div><div class="must-read-content"><span class="source-tag">{}</span><h4>{}</h4><p class="summary">{}</p><a href="{}" target="_blank" class="link">阅读原文 →</a></div></div>'.format(
            i+1, escape(item.get('source','新闻')), escape(item.get('title','')),
            escape(item.get('summary','') or item.get('ai_summary','')), escape(item.get('url','#')))
    
    # 播客
    pod_html = ''
    for p in podcasts[:20]:
        s = p.get('summary','')
        pod_html += '<div class="card"><span class="source-tag">🎧 {}</span><h3>{}</h3><p class="summary">{}</p><a href="{}" target="_blank" class="link">收听 →</a></div>'.format(
            escape(p.get('source','播客')), escape(p.get('title','')),
            escape(s[:200] if len(s)>200 else s), escape(p.get('link','') or p.get('url','#')))
    
    # YouTube
    yt_html = ''
    for y in youtube[:20]:
        s = y.get('summary','')
        yt_html += '<div class="card"><span class="source-tag">📺 {}</span><h3>{}</h3><p class="summary">{}</p><a href="{}" target="_blank" class="link">观看 →</a></div>'.format(
            escape(y.get('channel', y.get('source','YouTube'))), escape(y.get('title','')),
            escape(s[:150] if len(s)>150 else s), escape(y.get('url','') or y.get('link','#')))
    
    news_js = json.dumps(news, ensure_ascii=False)
    
    css = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; line-height: 1.6; }
        header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 0.8rem 1rem; position: sticky; top: 0; z-index: 100; }
        .header-content { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.2rem; font-weight: 700; }
        .date-selector select { padding: 0.3rem 0.6rem; border-radius: 6px; border: none; font-size: 0.85rem; cursor: pointer; }
        .tab-nav { background: white; border-bottom: 1px solid #e0e0e0; position: sticky; top: 56px; z-index: 99; }
        .tab-nav-inner { max-width: 1200px; margin: 0 auto; display: flex; }
        .tab-btn { padding: 0.8rem 1.2rem; border: none; background: none; font-size: 0.9rem; cursor: pointer; border-bottom: 2px solid transparent; color: #666; }
        .tab-btn.active { color: #1a1a2e; border-bottom-color: #1a1a2e; font-weight: 600; }
        .sub-filter { background: #f8f8fa; padding: 0.6rem 1rem; display: none; gap: 0.5rem; }
        .sub-filter.show { display: flex; }
        .sub-filter-btn { padding: 0.3rem 0.8rem; border: 1px solid #ddd; background: white; border-radius: 20px; font-size: 0.8rem; cursor: pointer; }
        .sub-filter-btn.active { background: #1a1a2e; color: white; border-color: #1a1a2e; }
        .container { max-width: 1200px; margin: 0 auto; padding: 1rem; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .must-read-scroll { display: flex; gap: 1rem; overflow-x: auto; padding-bottom: 0.5rem; scroll-snap-type: x mandatory; }
        .must-read-card { flex: 0 0 320px; background: white; border-radius: 12px; padding: 1rem; scroll-snap-align: start; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        .must-read-card .rank { font-size: 2rem; font-weight: 800; color: #ffd700; line-height: 1; margin-bottom: 0.5rem; }
        .must-read-card h4 { font-size: 0.95rem; margin: 0.3rem 0; line-height: 1.4; }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
        .card { background: white; border-radius: 12px; padding: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
        .card h3, .card h4 { font-size: 0.95rem; margin-bottom: 0.4rem; line-height: 1.4; }
        .source-tag { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; background: #f0f0f5; color: #666; margin-bottom: 0.4rem; }
        .summary { color: #494949; font-size: 0.85rem; margin: 0.4rem 0; line-height: 1.5; }
        .link { color: #007aff; text-decoration: none; font-size: 0.82rem; }
        .link:hover { text-decoration: underline; }
        .empty-state { text-align: center; padding: 3rem; color: #999; }
        .stats-bar { background: white; padding: 0.6rem 1rem; display: flex; justify-content: center; gap: 1.5rem; border-bottom: 1px solid #e0e0e0; font-size: 0.85rem; color: #666; }
        footer { text-align: center; padding: 2rem; color: #666; font-size: 0.85rem; }
    """
    
    js = """
        var newsData = %s;
        var currentTab = 'must-read';
        var currentSubCat = 'all';

        document.querySelectorAll('.tab-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var tab = this.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
                this.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
                document.getElementById('tab-' + tab).classList.add('active');
                var subFilter = document.getElementById('newsSubFilter');
                if (tab === 'news') { subFilter.classList.add('show'); renderNews(); }
                else { subFilter.classList.remove('show'); }
                if (tab === 'all') { renderAllNews(); }
                currentTab = tab;
            });
        });

        document.querySelectorAll('.sub-filter-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var cat = this.dataset.cat;
                document.querySelectorAll('.sub-filter-btn').forEach(function(b) { b.classList.remove('active'); });
                this.classList.add('active');
                currentSubCat = cat;
                renderNews();
            });
        });

        function renderNews() {
            var container = document.getElementById('newsGrid');
            var items = [];
            if (currentSubCat === 'all') {
                for (var cat in newsData) { if (Array.isArray(newsData[cat])) { items = items.concat(newsData[cat]); } }
            } else { items = newsData[currentSubCat] || []; }
            items = items.slice(0, 20);
            if (items.length === 0) { container.innerHTML = '<div class=\\'empty-state\\'>暂无资讯</div>'; return; }
            container.innerHTML = items.map(function(item) {
                return '<div class=\\'card\\'>' +
                    '<span class=\\'source-tag\\'>' + (item.source || '新闻') + '</span>' +
                    '<h4>' + (item.title || '') + '</h4>' +
                    '<p class=\\'summary\\'>' + (item.summary || item.ai_summary || '') + '</p>' +
                    '<a href=\\'' + (item.url || '#') + '\\' target=\\'_blank\\' class=\\'link\\'>阅读原文 →</a>' +
                    '</div>';
            }).join('');
        }

        function renderAllNews() {
            var container = document.getElementById('allNews');
            var items = [];
            for (var cat in newsData) { if (Array.isArray(newsData[cat])) { items = items.concat(newsData[cat]); } }
            items = items.slice(0, 30);
            if (items.length === 0) { container.innerHTML = '<div class=\\'empty-state\\'>暂无资讯</div>'; return; }
            container.innerHTML = items.map(function(item) {
                return '<div class=\\'card\\'>' +
                    '<span class=\\'source-tag\\'>' + (item.source || '新闻') + '</span>' +
                    '<h4>' + (item.title || '') + '</h4>' +
                    '<p class=\\'summary\\'>' + (item.summary || item.ai_summary || '') + '</p>' +
                    '<a href=\\'' + (item.url || '#') + '\\' target=\\'_blank\\' class=\\'link\\'>阅读原文 →</a>' +
                    '</div>';
            }).join('');
        }
    """ % news_js
    
    empty = '<div class="empty-state">暂无必读内容</div>' if not mr_html else mr_html
    empty_pod = '<div class="empty-state">今日暂无播客更新</div>' if not pod_html else pod_html
    empty_yt = '<div class="empty-state">今日暂无YouTube更新</div>' if not yt_html else yt_html
    
    html = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>📰 每日资讯 %s</title>\n<style>%s</style>\n</head>\n<body>\n<header>\n<div class="header-content">\n<div class="logo">📰 每日资讯</div>\n<div class="date-selector"><select id="datePicker">%s</select></div>\n</div>\n</header>\n\n<nav class="tab-nav">\n<div class="tab-nav-inner">\n<button class="tab-btn active" data-tab="must-read">📌 今日必读</button>\n<button class="tab-btn" data-tab="news">📰 新闻</button>\n<button class="tab-btn" data-tab="podcast">🎧 播客</button>\n<button class="tab-btn" data-tab="youtube">📺 YouTube</button>\n<button class="tab-btn" data-tab="all">📋 全部</button>\n</div>\n</nav>\n\n<div class="sub-filter" id="newsSubFilter">\n<button class="sub-filter-btn active" data-cat="all">全部</button>\n<button class="sub-filter-btn" data-cat="AI前沿">📡 AI前沿</button>\n<button class="sub-filter-btn" data-cat="大国博弈">🌍 大国博弈</button>\n<button class="sub-filter-btn" data-cat="产业趋势">🏭 产业趋势</button>\n<button class="sub-filter-btn" data-cat="投资参考">📈 投资参考</button>\n</div>\n\n<div class="stats-bar">\n<span>📰 %d 条新闻</span>\n<span>🎧 %d 期播客</span>\n<span>📺 %d 个视频</span>\n</div>\n\n<div class="container">\n<div id="tab-must-read" class="tab-content active"><div class="must-read-scroll">%s</div></div>\n<div id="tab-news" class="tab-content"><div class="card-grid" id="newsGrid"></div></div>\n<div id="tab-podcast" class="tab-content"><div class="card-grid">%s</div></div>\n<div id="tab-youtube" class="tab-content"><div class="card-grid">%s</div></div>\n<div id="tab-all" class="tab-content">\n<h3 style="margin-bottom:1rem;">📰 新闻</h3>\n<div class="card-grid" id="allNews"></div>\n<h3 style="margin:1.5rem 0 1rem;">🎧 播客</h3>\n<div class="card-grid">%s</div>\n<h3 style="margin:1.5rem 0 1rem;">📺 YouTube</h3>\n<div class="card-grid">%s</div>\n</div>\n</div>\n\n<footer><p>每日资讯 · 更新于 %s</p></footer>\n<script>%s</script>\n</body>\n</html>' % (
        date, css, opts, total, len(podcasts), len(youtube),
        empty, empty_pod, empty_yt, empty_pod, empty_yt,
        datetime.now().strftime('%H:%M'), js
    )
    
    out = WORKSPACE / 'gh-pages' / 'index.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print('✅ index.html v2.0 已生成')
    print('   日期: %s' % date)
    print('   新闻: %d 条' % total)
    print('   播客: %d 条' % len(podcasts))
    print('   YouTube: %d 条' % len(youtube))

if __name__ == '__main__':
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    dates = get_available_dates()
    date = arg if arg in dates else (dates[0] if dates else datetime.now().strftime('%Y-%m-%d'))
    gen_html(date)
