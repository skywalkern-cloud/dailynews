#!/usr/bin/env python3
"""index.html v2.1 生成脚本 - 可展开卡片版"""
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
    
    dates = get_available_dates()
    today = datetime.now().strftime('%Y-%m-%d')
    
    opts = ''
    for d in sorted(dates, reverse=True):
        sel = ' selected' if d == date else ''
        label = '今天' if d == today else d
        opts += '<option value="{}"{}>{}</option>'.format(d, sel, label)
    
    must_read = news.get('must-read', [])[:10]
    ai_news = news.get('AI前沿', [])
    geo_news = news.get('大国博弈', [])
    industry_news = news.get('产业趋势', [])
    invest_news = news.get('投资参考', [])
    
    all_news = []
    for cat in ['must-read', 'AI前沿', '大国博弈', '产业趋势', '投资参考']:
        if cat in news and isinstance(news[cat], list):
            all_news.extend(news[cat])
    
    total = len(all_news)
    
    tabs = [
        ('must-read', '📌', '每日必读'),
        ('ai', '🤖', 'AI前沿'),
        ('geo', '🌍', '大国博弈'),
        ('industry', '🏭', '产业趋势'),
        ('invest', '📈', '投资参考'),
        ('all', '📰', '全部新闻'),
        ('podcast', '🎧', '播客晨读'),
        ('youtube', '📺', 'YouTube总结'),
    ]
    
    tab_btns = ''
    for tab_id, icon, label in tabs:
        tab_btns += '<button class="tab-btn" data-tab="{}">{} {}</button>'.format(tab_id, icon, label)
    
    must_read_html = ''
    if must_read:
        top = must_read[0]
        must_read_html += '<div class="top-article" onclick="window.open(\'{}\', \'_blank\')"><span class="top-badge">🟠 置顶头条</span><h3>{}</h3><div class="meta"><span>{}</span><span>{}</span></div></div>'.format(
            escape(top.get('url','#')), escape(top.get('title','')),
            escape(top.get('source','新闻')), escape(top.get('published_at','')[:10] if top.get('published_at') else ''))
        if len(must_read) > 1:
            must_read_html += '<div class="card-grid">'
            for item in must_read[1:9]:
            html += '<div class="news-card" onclick="window.open('{}', '_blank')"><div class="card-tag">{}</div><h4>{}</h4>{}<div class="meta">{} · {}</div></div>'.format(
                escape(item.get('url','#')), escape(item.get('source','新闻')),
                escape(item.get('title','')), summary_html,
                escape(item.get('source','')), escape(item.get('published_at','')[:10] if item.get('published_at') else ''))
                    escape(item.get('url','#')), escape(item.get('source','新闻')),
                    escape(item.get('title','')), escape(item.get('source','')), escape(item.get('published_at','')[:10] if item.get('published_at') else ''))
            must_read_html += '</div>'
    else:
        must_read_html = '<div class="empty-state">暂无必读内容</div>'
    
    def news_cards(items):
        if not items:
            return '<div class="empty-state">暂无相关资讯</div>'
        html = '<div class="card-grid">'
        for item in items[:12]:
            ai_summary = escape(item.get('ai_summary', '')[:200]) if item.get('ai_summary') else ''
            summary_html = f'<p class="news-summary">{ai_summary}</p>' if ai_summary else ''
            html += '<div class="news-card" onclick="window.open(\'{}\', \'_blank\')"><div class="card-tag">{}</div><h4>{}</h4><div class="meta">{} · {}</div>{}</div>'.format(
                escape(item.get('url','#')), escape(item.get('source','新闻')),
                escape(item.get('title','')), escape(item.get('source','')), escape(item.get('published_at','')[:10] if item.get('published_at') else ''))
        html += '</div>'
        return html
    
    ai_html = news_cards(ai_news)
    geo_html = news_cards(geo_news)
    industry_html = news_cards(industry_news)
    invest_html = news_cards(invest_news)
    all_html = news_cards(all_news)
    
    # 播客卡片 - 可展开摘要
    podcast_html = ''
    if podcasts:
        podcast_html = '<div class="podcast-list">'
        for i, p in enumerate(podcasts[:10]):
            summary = p.get('summary', '')
            summary_short = summary  # Use full summary
            podcast_html += '<div class="podcast-card">'
            podcast_html += '<div class="podcast-header"><span class="podcast-icon">🎙</span><h3>{}</h3><button class="play-btn" onclick="window.open(\'{}\', \'_blank\')">🔊 播放</button></div>'.format(
                escape(p.get('source','播客')), escape(p.get('link','') or p.get('url','#')))
            podcast_html += '<div class="podcast-body"><p class="podcast-title">{}</p><div class="summary-content collapsed" id="psummary-{}"><p class="podcast-summary">{}</p></div><button class="expand-btn" onclick="toggleSummary({})">展开阅读 ▼</button></div>'.format(
                escape(p.get('title','')), i, escape(summary_short), i)
            podcast_html += '<div class="podcast-meta">🕐 {} · 🎧 {} · 📅 {}</div></div>'.format(
                escape(p.get('duration','')), escape(str(p.get('plays',''))), date)
        podcast_html += '</div>'
    else:
        podcast_html = '<div class="empty-state">🎧 今日暂无播客更新</div>'
    
    # YouTube卡片
    youtube_html = ''
    if youtube:
        youtube_html = '<div class="card-grid youtube-grid">'
        for i, y in enumerate(youtube[:20]):
            summary = y.get('summary', '')
            summary_short = summary  # Use full summary
            youtube_html += '<div class="youtube-card">'
            youtube_html += '<div class="video-thumb" onclick="window.open(\'{}\', \'_blank\')"><div class="play-overlay">▶</div></div>'.format(
                escape(y.get('url','') or y.get('link','#')))
            youtube_html += '<div class="video-info"><h4 onclick="window.open(\'{}\', \'_blank\')">{}</h4><div class="meta">📺 {} · 🕐 {}</div><p class="summary" id="ysummary-{}">{}</p><button class="expand-btn" onclick="toggleSummary(\'y{}\')">展开 ▼</button></div>'.format(
                escape(y.get('url','') or y.get('link','#')),
                escape(y.get('title','')), escape(y.get('channel', y.get('source','YouTube'))),
                escape(y.get('duration','')), i, escape(summary_short), i)
            youtube_html += '</div>'
        youtube_html += '</div>'
    else:
        youtube_html = '<div class="empty-state">📺 今日暂无YouTube更新</div>'
    
    news_js = json.dumps(news, ensure_ascii=False)
    
    css = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8f9fa; color: #202124; line-height: 1.6; }
        .header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 1rem; position: sticky; top: 0; z-index: 100; }
        .header-content { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; }
        .logo { font-size: 1.3rem; font-weight: 600; }
        .date-selector select { padding: 0.4rem 0.8rem; border-radius: 8px; border: none; font-size: 0.9rem; cursor: pointer; }
        .tab-nav { background: white; border-bottom: 1px solid #e8eaed; position: sticky; top: 56px; z-index: 99; }
        .tab-nav-inner { max-width: 1200px; margin: 0 auto; display: flex; overflow-x: auto; scrollbar-width: none; }
        .tab-nav-inner::-webkit-scrollbar { display: none; }
        .tab-btn { padding: 0.8rem 1rem; border: none; background: none; font-size: 0.85rem; cursor: pointer; white-space: nowrap; border-bottom: 2px solid transparent; color: #5f6368; flex-shrink: 0; }
        .tab-btn.active { color: #1a73e8; border-bottom-color: #1a73e8; font-weight: 500; background: #e8f0fe; }
        .container { max-width: 1200px; margin: 0 auto; padding: 1rem; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .top-article { background: linear-gradient(135deg, #fef7e0 0%, #fff9e6 100%); border-left: 4px solid #f57c00; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; cursor: pointer; }
        .top-article:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .top-badge { display: inline-block; background: #f57c00; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-bottom: 0.5rem; }
        .top-article h3 { font-size: 1.1rem; color: #202124; margin: 0.3rem 0; }
        .card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
        .news-card { background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); cursor: pointer; transition: all 0.2s ease; }
        .news-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.12); }
        .news-card .card-tag { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; background: #e8f0fe; color: #1a73e8; margin-bottom: 0.5rem; }
        .news-summary { font-size: 0.85rem; color: #5f6368; margin: 0.3rem 0; line-height: 1.4; }
        .news-card h4 { font-size: 1rem; font-weight: 600; color: #202124; margin-bottom: 0.5rem; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .meta { font-size: 0.75rem; color: #5f6368; }
        .meta span { margin-right: 0.5rem; }
        .podcast-list { display: flex; flex-direction: column; gap: 1rem; }
        .podcast-card { background: #fff; border-radius: 8px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        .podcast-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; }
        .podcast-icon { font-size: 1.5rem; margin-right: 0.5rem; }
        .podcast-header h3 { font-size: 1rem; font-weight: 600; display: flex; align-items: center; }
        .play-btn { background: #1a73e8; color: white; border: none; padding: 0.4rem 0.8rem; border-radius: 20px; font-size: 0.8rem; cursor: pointer; }
        .play-btn:hover { background: #1557b0; }
        .podcast-body { border-top: 1px solid #e8eaed; padding-top: 0.8rem; }
        .podcast-title { font-weight: 600; color: #202124; margin-bottom: 0.5rem; }
        .summary-content { position: relative; overflow: hidden; transition: max-height 0.4s ease; }
        .summary-content.collapsed { max-height: 150px; }
        .summary-content.expanded { max-height: none; }
        .summary-content.collapsed::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 40px;
            background: linear-gradient(transparent, #fff);
        }
        .summary-content.expanded::after { display: none; }
        .expand-btn { background: none; border: none; color: #1a73e8; font-size: 0.85rem; cursor: pointer; padding: 0.3rem 0; margin-top: 0.5rem; }
        .expand-btn:hover { text-decoration: underline; }
        .podcast-meta { margin-top: 0.8rem; font-size: 0.8rem; color: #5f6368; display: flex; gap: 1rem; }
        .youtube-grid { grid-template-columns: repeat(2, 1fr); }
        .youtube-card { background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.12); transition: all 0.2s ease; }
        .youtube-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.12); }
        .video-thumb { position: relative; padding-top: 56.25%; background: #000; cursor: pointer; }
        .play-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 50px; height: 50px; background: rgba(255,255,255,0.9); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; }
        .video-info { padding: 1rem; }
        .video-info h4 { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.3rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; cursor: pointer; }
        .video-info .summary { font-size: 0.8rem; color: #5f6368; margin-top: 0.3rem; white-space: pre-wrap; word-break: break-word; }
        .empty-state { text-align: center; padding: 4rem 2rem; color: #5f6368; background: #fff; border-radius: 8px; }
        @media (max-width: 1023px) { .card-grid { grid-template-columns: repeat(2, 1fr); } .youtube-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 767px) { .card-grid { grid-template-columns: 1fr; } .youtube-grid { grid-template-columns: 1fr; } .container { padding: 0.75rem; } }
    """
    
    js = """
        var newsData = %s;
        var currentTab = 'must-read';

        document.querySelectorAll('.tab-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var tab = this.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
                this.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
                document.getElementById('tab-' + tab).classList.add('active');
                currentTab = tab;
            });
        });

        function toggleSummary(id) {
            var sid = String(id);
            var el = document.getElementById(sid.startsWith('y') ? 'ysummary-' + sid.slice(1) : 'psummary-' + sid);
            var btn = el.nextElementSibling;
            if (el.classList.contains('collapsed')) {
                el.classList.remove('collapsed');
                btn.textContent = '收起 ▲';
            } else {
                el.classList.add('collapsed');
                btn.textContent = '展开阅读 ▼';
            }
        }
    """ % news_js
    
    html = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>📰 每日资讯 %s</title>\n<style>%s</style>\n</head>\n<body>\n<header class="header">\n<div class="header-content">\n<div class="logo">📰 每日资讯</div>\n<div class="date-selector"><select id="datePicker">%s</select></div>\n</div>\n</header>\n\n<nav class="tab-nav">\n<div class="tab-nav-inner">%s</div>\n</nav>\n\n<div class="container">\n<div id="tab-must-read" class="tab-content active">%s</div>\n<div id="tab-ai" class="tab-content">%s</div>\n<div id="tab-geo" class="tab-content">%s</div>\n<div id="tab-industry" class="tab-content">%s</div>\n<div id="tab-invest" class="tab-content">%s</div>\n<div id="tab-all" class="tab-content">%s</div>\n<div id="tab-podcast" class="tab-content">%s</div>\n<div id="tab-youtube" class="tab-content">%s</div>\n</div>\n\n<script>%s</script>\n</body>\n</html>' % (
        date, css, opts, tab_btns,
        must_read_html, ai_html, geo_html, industry_html, invest_html, all_html,
        podcast_html, youtube_html, js
    )
    
    out = WORKSPACE / 'gh-pages' / 'index.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print('✅ index.html v2.1 (可展开卡片) 已生成')
    print('   日期: %s' % date)
    print('   播客: %d 条 (支持展开/收起)' % len(podcasts))
    print('   YouTube: %d 条 (支持展开/收起)' % len(youtube))

if __name__ == '__main__':
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    dates = get_available_dates()
    date = arg if arg in dates else (dates[0] if dates else datetime.now().strftime('%Y-%m-%d'))
    gen_html(date)
