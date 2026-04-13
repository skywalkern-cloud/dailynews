#!/usr/bin/env python3
"""修复版generate_html_v2"""
import json
import os
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("~/.openclaw/workspace-dailynews").expanduser()
GH_PAGES = WORKSPACE / "gh-pages"
DATA_DIR = GH_PAGES / "data"

def get_available_dates():
    dates = []
    if DATA_DIR.exists():
        for d in sorted(DATA_DIR.iterdir(), reverse=True):
            if d.is_dir():
                try:
                    dates.append(d.name)
                except:
                    pass
    return dates[:7]

def load_json(name, date):
    f = DATA_DIR / date / name
    if f.exists():
        with open(f) as fp:
            return json.load(fp)
    return None

def escape(text):
    if not text:
        return ""
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))

def gen_html(date=None):
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    available_dates = get_available_dates()
    if date not in available_dates and available_dates:
        date = available_dates[0]
    
    news_data = load_json('news.json', date) or {}
    podcasts = load_json('podcasts.json', date) or []
    youtube = load_json('youtube.json', date) or []
    
    if isinstance(news_data, list):
        news_data = {'must-read': news_data}
    
    total = sum(len(v) for v in news_data.values() if isinstance(v, list))
    
    # 生成must-read卡片 - 摘要收起状态，展开显示完整
    mr_html = ''
    for i, item in enumerate(news_data.get('must-read', [])[:10]):
        s = item.get('summary','') or item.get('ai_summary','')
        s_short = escape(s[:100]) if s else ''
        s_escaped = escape(s) if s else ''
        mr_html += f'''<div class="must-read-card"><div class="rank">{i+1}</div><div class="must-read-content"><span class="source-tag">{escape(item.get('source','新闻'))}</span><h4>{escape(item.get('title',''))}</h4><p class="summary" data-full="{s_escaped}">{s_short}</p><a class="expand-btn" href="javascript:void(0)" onclick="toggleSummary(this)">展开阅读 ▾</a><a href="{escape(item.get('url','#'))}" target="_blank" class="link">阅读原文 →</a></div></div>'''
    
    # 播客 - 摘要收起，展开显示完整
    pod_html = ''
    for p in podcasts[:10]:
        s = p.get('summary','')
        s_short = escape(s[:100]) if s else ''
        s_escaped = escape(s) if s else ''
        pod_html += f'''<div class="card"><span class="source-tag">🎧 {escape(p.get('source','播客'))}</span><h3>{escape(p.get('title',''))}</h3><p class="summary" data-full="{s_escaped}">{s_short}</p><a class="expand-btn" href="javascript:void(0)" onclick="toggleSummary(this)">展开阅读 ▾</a><a href="{escape(p.get('url','#'))}" target="_blank" class="link">收听 →</a></div>'''
    
    # YouTube - 摘要收起，展开显示完整
    yt_html = ''
    for y in youtube[:20]:
        s = y.get('summary','')
        s_short = escape(s[:100]) if s else ''
        s_escaped = escape(s) if s else ''
        yt_html += f'''<div class="card"><span class="source-tag">📺 {escape(y.get('channel', y.get('source','YouTube')))}</span><h3>{escape(y.get('title',''))}</h3><p class="summary" data-full="{s_escaped}">{s_short}</p><a class="expand-btn" href="javascript:void(0)" onclick="toggleSummary(this)">展开阅读 ▾</a><a href="{escape(y.get('url','#'))}" target="_blank" class="link">观看 →</a></div>'''
    
    # CSS
    css = '''
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; }
        .header-content { max-width: 1200px; margin: 0 auto; padding: 1rem; display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.5rem; font-weight: 700; }
        .date-selector select { padding: 0.5rem; border-radius: 8px; border: 1px solid #ddd; font-size: 0.9rem; }
        .tab-nav { background: white; border-bottom: 1px solid #e0e0e0; position: sticky; top: 56px; z-index: 99; }
        .tab-nav-inner { max-width: 1200px; margin: 0 auto; display: flex; flex-wrap: wrap; }
        .tab-btn { padding: 0.8rem 1.2rem; border: none; background: none; font-size: 0.9rem; cursor: pointer; border-bottom: 2px solid transparent; color: #666; }
        .tab-btn.active { color: #1a1a2e; border-bottom-color: #1a1a2e; font-weight: 600; }
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
        .summary { color: #494949; font-size: 0.85rem; margin: 0.4rem 0; line-height: 1.5; max-height: 3em; overflow: hidden; }
        .summary.expanded { max-height: none; }
        .expand-btn { color: #007aff; cursor: pointer; font-size: 0.8rem; margin-right: 0.5rem; }
        .link { color: #007aff; text-decoration: none; font-size: 0.82rem; }
        .link:hover { text-decoration: underline; }
        .empty-state { text-align: center; padding: 3rem; color: #999; }
        footer { text-align: center; padding: 2rem; color: #666; font-size: 0.85rem; }
    '''
    
    opts = ''.join(f'<option value="{d}" {"selected" if d==date else ""}>{d}</option>' for d in available_dates)
    
    # JS - 展开/收起功能，从data-full获取完整内容
    js = f'''
        var currentTab = 'must-read';
        var newsData = {json.dumps(news_data, ensure_ascii=False)};
        function toggleSummary(btn) {{
            var p = btn.previousElementSibling.previousElementSibling;
            var fullText = p.getAttribute('data-full');
            if (p.classList.contains('expanded')) {{
                p.classList.remove('expanded');
                p.textContent = fullText ? fullText.substring(0, 100) : '';
                btn.textContent = '展开阅读 ▾';
            }} else {{
                p.classList.add('expanded');
                p.textContent = fullText || '';
                btn.textContent = '收起 △';
            }}
        }}
        document.querySelectorAll('.tab-btn').forEach(function(btn) {{
            btn.addEventListener('click', function() {{
                var tab = this.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
                this.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(function(c) {{ c.classList.remove('active'); }});
                document.getElementById('tab-' + tab).classList.add('active');
                currentTab = tab;
            }});
        }});
        document.getElementById('datePicker').addEventListener('change', function() {{
            window.location.href = '?date=' + this.value;
        }});
    '''
    
    empty = '<div class="empty-state">暂无资讯</div>' if not mr_html else mr_html
    empty_pod = '<div class="empty-state">今日暂无播客更新</div>' if not pod_html else pod_html
    empty_yt = '<div class="empty-state">今日暂无YouTube更新</div>' if not yt_html else yt_html
    
    tabs = '''
<button class="tab-btn active" data-tab="must-read">📌 今日必读</button>
<button class="tab-btn" data-tab="AI前沿">📡 AI前沿</button>
<button class="tab-btn" data-tab="大国博弈">🌍 大国博弈</button>
<button class="tab-btn" data-tab="产业趋势">🏭 产业趋势</button>
<button class="tab-btn" data-tab="投资参考">📈 投资参考</button>
<button class="tab-btn" data-tab="podcast">🎧 播客</button>
<button class="tab-btn" data-tab="youtube">📺 YouTube</button>'''
    
    html = f'''<!DOCTYPE html>
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
<div class="date-selector"><select id="datePicker">{opts}</select></div>
</div>
</header>
<nav class="tab-nav">
<div class="tab-nav-inner">{tabs}
</div>
</nav>
<div class="container">
<div id="tab-must-read" class="tab-content active"><div class="must-read-scroll">{empty}</div></div>
<div id="tab-AI前沿" class="tab-content"><div class="card-grid"></div></div>
<div id="tab-大国博弈" class="tab-content"><div class="card-grid"></div></div>
<div id="tab-产业趋势" class="tab-content"><div class="card-grid"></div></div>
<div id="tab-投资参考" class="tab-content"><div class="card-grid"></div></div>
<div id="tab-podcast" class="tab-content"><div class="card-grid">{empty_pod}</div></div>
<div id="tab-youtube" class="tab-content"><div class="card-grid">{empty_yt}</div></div>
</div>
<footer><p>每日资讯 · 更新于 {datetime.now().strftime('%H:%M')}</p></footer>
<script>{js}</script>
</body>
</html>'''
    
    with open(GH_PAGES / 'index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'✅ index.html v2.0 已生成')
    print(f'   日期: {date}')
    print(f'   新闻: {total} 条')
    print(f'   播客: {len(podcasts)} 条')
    print(f'   YouTube: {len(youtube)} 条')

if __name__ == '__main__':
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    dates = get_available_dates()
    date = arg if arg in dates else (dates[0] if dates else datetime.now().strftime('%Y-%m-%d'))
    gen_html(date)
