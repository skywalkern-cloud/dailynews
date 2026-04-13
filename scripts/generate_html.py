#!/usr/bin/env python3
"""
index.html 生成脚本
根据 v1.9 设计文档生成每日资讯网页

用法:
    python3 generate_html.py [日期]
    
示例:
    python3 generate_html.py              # 生成今天
    python3 generate_html.py 2026-04-09   # 生成指定日期
"""
import json
import os
from pathlib import Path
from datetime import datetime

# 配置
WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
GH_PAGES = WORKSPACE / "gh-pages"
DATA_DIR = GH_PAGES / "data"


def get_available_dates():
    """获取可用日期列表"""
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
    """加载指定日期的数据文件"""
    fpath = DATA_DIR / date / filename
    if fpath.exists():
        with open(fpath, encoding='utf-8') as f:
            return json.load(f)
    return None


def escape_html(text):
    """转义HTML特殊字符"""
    if not text:
        return ''
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;'))


def generate_html(date=None):
    """生成 index.html"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    # 获取可用日期
    available_dates = get_available_dates()
    if not available_dates:
        print("错误: 没有找到数据目录")
        return False
    
    # 如果指定日期不存在，使用最新日期
    if date not in available_dates:
        if available_dates:
            date = available_dates[0]
            print(f"指定日期无数据，使用最新日期: {date}")
        else:
            print("错误: 没有可用数据")
            return False
    
    # 加载数据
    news_data = load_json('news.json', date)
    podcasts_data = load_json('podcasts.json', date) or []
    youtube_data = load_json('youtube.json', date) or []
    
    # 处理新闻数据格式
    if isinstance(news_data, dict):
        # 已经是分类dict格式
        pass
    elif isinstance(news_data, list):
        # 是列表格式，转换为dict
        news_data = {'must-read': news_data}
    else:
        news_data = {}
    
    # 计算新闻总数
    total_news = sum(len(v) for v in news_data.values() if isinstance(v, list))
    
    # 日期选项
    date_options = '\n'.join([
        f'<option value="{d}" {"selected" if d == date else ""}>{"今天" if d == datetime.now().strftime("%Y-%m-%d") else d}</option>'
        for d in sorted(available_dates, reverse=True)
    ])
    
    # 新闻分类映射
    category_map = {
        'AI前沿': 'ai',
        '大国博弈': 'geopolitics',
        '产业趋势': 'industry',
        '投资参考': 'investment'
    }
    
    # 新闻分类HTML
    news_sections_html = ''
    for cat_name, cat_id in category_map.items():
        items = news_data.get(cat_name, [])
        if not items:
            items_html = '<div class="empty-state">暂无资讯</div>'
        else:
            items_html = ''.join([
                f'''<div class="news-card">
                    <span class="source-tag">{escape_html(item.get('source', '新闻'))}</span>
                    <h4>{escape_html(item.get('title', ''))}</h4>
                    <p class="summary">{escape_html(item.get('summary', '') or item.get('ai_summary', ''))}</p>
                    <a href="{escape_html(item.get('url', '#'))}" target="_blank" class="link">阅读原文 →</a>
                </div>'''
                for item in items[:10]  # 最多10条
            ])
        news_sections_html += f'''
        <div class="section">
            <h2>📡 {cat_name}</h2>
            <div class="news-grid" id="news-{cat_id}">{items_html}</div>
        </div>'''
    
    # 播客HTML
    if not podcasts_data:
        podcasts_html = '<div class="empty-state">今日暂无播客更新</div>'
    else:
        podcasts_html = ''.join([
            f'''<div class="podcast-card">
                <span class="source-tag">🎧 {escape_html(p.get('source', '播客'))}</span>
                <h3>{escape_html(p.get('title', ''))}</h3>
                <p class="content-summary" data-full="{escape_html(p.get('summary', ''))}">{escape_html(p.get('summary', '')[:200] if len(p.get('summary', '')) > 200 else p.get('summary', ''))}</p>
                <a href="{escape_html(p.get('link', '#') or p.get('url', '#'))}" target="_blank" class="link">收听 →</a>
            </div>'''
            for p in podcasts_data[:20]  # 最多20条
        ])
    
    # YouTube HTML
    if not youtube_data:
        youtube_html = '<div class="empty-state">今日暂无YouTube更新</div>'
    else:
        youtube_html = ''.join([
            f'''<div class="youtube-card">
                <span class="source-tag">📺 {escape_html(y.get('channel', y.get('source', 'YouTube')))}</span>
                <h3>{escape_html(y.get('title', ''))}</h3>
                <p class="content-summary" data-full="{escape_html(y.get('summary', ''))}">{escape_html(y.get('summary', '')[:150] if len(y.get('summary', '')) > 150 else y.get('summary', ''))}</p>
                <a href="{escape_html(y.get('url', '#') or y.get('link', '#'))}" target="_blank" class="link">观看 →</a>
            </div>'''
            for y in youtube_data[:20]  # 最多20条
        ])
    
    # 组装HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📰 每日资讯 {date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; line-height: 1.6; }}
        header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 1rem; position: sticky; top: 0; z-index: 100; }}
        .header-content {{ max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; }}
        .logo {{ font-size: 1.3rem; font-weight: 700; }}
        .date-selector select {{ padding: 0.4rem 0.8rem; border-radius: 6px; border: none; font-size: 0.9rem; cursor: pointer; }}
        .stats-bar {{ background: white; padding: 0.8rem 1rem; display: flex; justify-content: center; gap: 2rem; border-bottom: 1px solid #e0e0e0; }}
        .stats-bar span {{ display: flex; align-items: center; gap: 0.3rem; font-size: 0.9rem; color: #666; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 1rem; }}
        .section {{ background: white; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
        .section h2 {{ font-size: 1.1rem; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #f0f0f0; }}
        .news-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.8rem; }}
        .news-card, .podcast-card, .youtube-card {{ padding: 1rem; border-bottom: 1px solid #f0f0f0; }}
        .news-card:last-child, .podcast-card:last-child, .youtube-card:last-child {{ border-bottom: none; }}
        .news-card h4, .podcast-card h3, .youtube-card h3 {{ font-size: 0.95rem; margin-bottom: 0.4rem; line-height: 1.4; }}
        .source-tag {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-bottom: 0.4rem; font-weight: 600; background: #f0f0f5; color: #666; }}
        .summary {{ color: #494949; font-size: 0.85rem; margin: 0.4rem 0; }}
        .link {{ color: #007aff; text-decoration: none; font-size: 0.82rem; }}
        .link:hover {{ text-decoration: underline; }}
        .content-summary {{ font-size: 0.85rem; color: #494949; line-height: 1.6; max-height: 4.5em; overflow: hidden; white-space: pre-wrap; }}
        .content-summary.expanded {{ max-height: none; }}
        .empty-state {{ text-align: center; padding: 2rem; color: #999; }}
        footer {{ text-align: center; padding: 2rem; color: #666; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <div class="logo">📰 每日资讯</div>
            <div class="date-selector">
                <select id="datePicker" onchange="loadDate(this.value)">
                    {date_options}
                </select>
            </div>
        </div>
    </header>
    
    <div class="stats-bar">
        <span>📰 <span id="newsCount">{total_news}</span> 条新闻</span>
        <span>🎧 <span id="podcastCount">{len(podcasts_data)}</span> 期播客</span>
        <span>📺 <span id="youtubeCount">{len(youtube_data)}</span> 个视频</span>
    </div>
    
    <div class="container">
        {news_sections_html}
        
        <div class="section">
            <h2>🎧 播客解读</h2>
            <div id="podcast-list">{podcasts_html}</div>
        </div>
        
        <div class="section">
            <h2>📺 YouTube</h2>
            <div id="youtube-list">{youtube_html}</div>
        </div>
    </div>
    
    <footer>
        <p>每日资讯 · 更新于 {datetime.now().strftime('%H:%M')}</p>
    </footer>

    <script>
        var currentDate = '{date}';
        
        function loadDate(dateStr) {{
            window.location.href = './?date=' + dateStr;
        }}
        
        // 从URL读取日期
        var urlParams = new URLSearchParams(window.location.search);
        var urlDate = urlParams.get('date');
        if (urlDate && urlDate !== currentDate) {{
            currentDate = urlDate;
            document.getElementById('datePicker').value = currentDate;
        }}
    </script>
</body>
</html>'''
    
    # 写入文件
    output_path = GH_PAGES / 'index.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ index.html 已生成: {output_path}")
    print(f"   日期: {date}")
    print(f"   新闻: {total_news} 条")
    print(f"   播客: {len(podcasts_data)} 条")
    print(f"   YouTube: {len(youtube_data)} 条")
    
    return True


if __name__ == '__main__':
    import sys
    
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_html(date_arg)
