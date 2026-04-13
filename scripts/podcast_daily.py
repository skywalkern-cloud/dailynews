#!/usr/bin/env python3
"""
播客检测脚本 - podcast_daily.py
功能：检测12个播客更新 + AI摘要生成 + 输出到gh-pages/podcast-data.json
"""
import os
import sys
import json
import time
import uuid
import re
import feedparser
import requests
import urllib.request
from datetime import datetime
from typing import Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from minimax_utils import generate_podcast_summary

# 配置
WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
CONFIG_DIR = WORK_DIR / "config"
GHPAGES_DIR = WORK_DIR / "gh-pages"
MEMORY_DIR = WORK_DIR / "memory"
DATA_DIR = GHPAGES_DIR / "data"

# Whisper转录配置
USE_WHISPER = os.environ.get("USE_WHISPER", "false").lower() == "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TEMP_AUDIO_DIR = Path("/tmp/podcast_audio")

def ensure_temp_dir():
    TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# 预加载faster-whisper模型（全局一次）
_faster_whisper_model = None

def get_faster_whisper_model():
    """懒加载faster-whisper模型"""
    global _faster_whisper_model
    if _faster_whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            print("    ⚡ 加载faster-whisper模型...")
            # device="cuda" 如果有GPU，否则用cpu
            _faster_whisper_model = WhisperModel("tiny", device="cpu")
            print("    ✅ 模型加载完成")
        except ImportError:
            print("    ⚠️ faster-whisper未安装，将使用OpenAI Whisper")
            _faster_whisper_model = False
    return _faster_whisper_model if _faster_whisper_model else None

def transcribe_with_whisper(audio_url: str, timeout: int = 300) -> Optional[str]:
    """
    转录音频，返回完整文本。
    优先级：faster-whisper(免费) > OpenAI Whisper > None(fallback)
    """
    ensure_temp_dir()
    audio_path = TEMP_AUDIO_DIR / f"{uuid.uuid4().hex[:8]}.mp3"
    
    try:
        print(f"    📥 下载音频: {audio_url[:60]}...")
        urllib.request.urlretrieve(audio_url, audio_path)
        
        # 方案1: faster-whisper（免费，本地）
        model = get_faster_whisper_model()
        if model:
            print(f"    ⚡ 使用faster-whisper转录...")
            segments, _ = model.transcribe(str(audio_path), language="zh")
            full_text = " ".join([s.text for s in segments])
            print(f"    ✅ 转录完成，字数: {len(full_text)}字")
            return full_text
        
        # 方案2: OpenAI Whisper（付费）
        if OPENAI_API_KEY:
            print(f"    🎤 使用OpenAI Whisper转录...")
            import openai
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            with open(audio_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            full_text = transcript.text
            print(f"    ✅ 转录完成，字数: {len(full_text)}字")
            return full_text
        
        print("    ⚠️ 未配置任何转录方式，跳过")
        return None
        
    except Exception as e:
        print(f"    ⚠️ 转录失败: {e}")
        return None
    finally:
        if audio_path.exists():
            audio_path.unlink()

def load_config():
    with open(CONFIG_DIR / "sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)
    return sources.get("podcast_sources", [])

def load_tracker():
    """加载播客追踪器"""
    tracker_path = MEMORY_DIR / "podcast-tracker.json"
    if tracker_path.exists():
        with open(tracker_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"podcasts": {}, "last_update": ""}

def parse_pub_date(pub_date_str):
    """解析RSS pubDate为datetime对象，用于多集检测"""
    if not pub_date_str:
        return None
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",      # RFC 2822 (e.g. Mon, 01 Jan 2024 12:00:00 +0000)
        "%a, %d %b %Y %H:%M:%S GMT",     # RFC 2822 variant
        "%Y-%m-%dT%H:%M:%S%z",           # ISO 8601
        "%Y-%m-%dT%H:%M:%SZ",            # ISO 8601 UTC
        "%Y-%m-%d %H:%M:%S",             # Simple date
    ]
    for fmt in formats:
        try:
            return datetime.strptime(pub_date_str.strip(), fmt).replace(tzinfo=None)
        except:
            pass
    return None

def save_tracker(tracker):
    """保存播客追踪器"""
    tracker_path = MEMORY_DIR / "podcast-tracker.json"
    tracker["last_update"] = datetime.now().isoformat()
    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)

def fetch_xiaoyuzhou(podcast_id):
    """通过小宇宙网页抓取获取播客信息"""
    try:
        url = f"https://www.xiaoyuzhoufm.com/podcast/{podcast_id}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            # 从<script>标签解析JSON
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', response.text, re.DOTALL)
            for s in scripts:
                if 'episode' in s.lower() and len(s) > 1000:
                    try:
                        data = json.loads(s)
                        # 必须检查是否有props结构
                        if 'props' not in data:
                            continue
                        podcast = data.get('props', {}).get('pageProps', {}).get('podcast', {})
                        episodes_list = podcast.get('episodes', [])[:5]
                        if episodes_list:
                            return [{"title": e.get("title", ""),
                                     "link": e.get("shareUrl", ""),
                                     "description": e.get("description", "")[:500],
                                     "pubDate": e.get("pubTime", ""),
                                     "audio_url": e.get("enclosure", {}).get("url", "")}
                                    for e in episodes_list]
                    except:
                        pass
    except Exception as e:
        print(f"  ✗ 小宇宙网页抓取失败: {e}")
    return []

def fetch_rss_feed(rss_url):
    """通过RSS获取播客信息"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        response = requests.get(rss_url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        feed = feedparser.parse(response.text)
        if feed.entries:
            episodes = []
            for entry in feed.entries[:5]:
                desc = entry.get("description", "")
                if desc:
                    desc = re.sub(r'<[^>]+>', '', desc)[:500]
                pub_date = entry.get("published", "") or ""
                # 获取音频URL（用于Whisper转录）
                audio_url = ""
                if hasattr(entry, 'enclosures') and entry.enclosures:
                    audio_url = entry.enclosures[0].get('url', '')
                episodes.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "description": desc,
                    "pubDate": pub_date,
                    "pubDate_parsed": entry.get("published_parsed"),
                    "audio_url": audio_url
                })
            return episodes
    except Exception as e:
        print(f"  ✗ RSS解析失败: {e}")
    return []

def fetch_podcast(podcast):
    """获取单个播客的最新 episodes"""
    name = podcast["name"]
    ptype = podcast.get("type", "rss")
    rss = podcast.get("rss")
    
    print(f"  获取 {name}...")
    
    # 优先使用RSS
    if rss:
        return fetch_rss_feed(rss)
    
    # 使用小宇宙API
    if ptype == "xiaoyuzhou":
        return fetch_xiaoyuzhou(podcast["id"])
    
    return []

def check_updates(podcasts, tracker):
    """检查播客更新 - 核心逻辑：
    - tracker 保存的是「截止点」（上次抓取时最旧的 episode 的 title）
    - 迭代方向：从最新到最旧，遇到 last_title 就 break（不包含它本身）
    - 首次运行（tracker 为空）：只取最新 3-5 个作为兜底保护
    """
    updates = []
    
    for podcast in podcasts:
        name = podcast["name"]
        podcast_id = podcast["id"]
        
        # 获取所有 episodes（返回顺序：[最新, ..., 最旧]）
        episodes = fetch_podcast(podcast)
        if not episodes:
            print(f"    ⚠️ 无 episodes")
            continue
        
        # 从 tracker 读取截止标记
        podcast_state = tracker.get("podcasts", {}).get(podcast_id, {})
        last_title = podcast_state.get("last_title", "")
        
        new_episodes = []
        if not last_title:
            # 首次运行：取最新 3-5 个作为兜底保护
            new_episodes = episodes[:5]
            print(f"    ⚡ 首次运行，取最新 {len(new_episodes)} 个")
        else:
            # 正常更新：从最新到最旧迭代，遇到 last_title 就 break
            for ep in episodes:
                if ep.get("title") == last_title:
                    break
                new_episodes.append(ep)
        
        if new_episodes:
            print(f"    ✓ 发现 {len(new_episodes)} 个新 episode: {[e['title'][:30] for e in new_episodes]}")
            updates.append({
                "podcast_name": name,
                "podcast_id": podcast_id,
                "episodes": new_episodes
            })
            
            # 保存截止点 = 这次抓到的最旧的 episode（用于下次识别边界）
            oldest_ep = episodes[-1]
            if "podcasts" not in tracker:
                tracker["podcasts"] = {}
            tracker["podcasts"][podcast_id] = {
                "name": name,
                "last_link": oldest_ep.get("link", ""),
                "last_title": oldest_ep.get("title", ""),
                "last_pub_date": oldest_ep.get("pubDate", "")
            }
        else:
            print(f"    - 无新 episode")
        
        time.sleep(1)
    
    return updates

def generate_summaries(updates):
    """为更新的播客生成AI摘要"""
    results = []
    now = datetime.now().isoformat()
    MAX_EPISODES_PER_PODCAST = 3
    
    for update in updates:
        podcast_name = update["podcast_name"]
        episodes = update["episodes"][:MAX_EPISODES_PER_PODCAST]  # 最多3个
        
        for ep in episodes:
            title = ep.get("title", "")
            desc = ep.get("description", "")
            pub_date = ep.get("pubDate", "")
            audio_url = ep.get("audio_url", "")
            
            print(f"  生成摘要: {title[:40]}...")
            
            # 优先使用Whisper转录（如果启用）
            full_text = None
            if USE_WHISPER and audio_url:
                full_text = transcribe_with_whisper(audio_url)
            
            # 根据输入内容生成摘要
            input_text = full_text if full_text else desc
            summary = generate_podcast_summary(input_text)
            
            # 标记摘要来源
            source_note = "(Whisper转录)" if full_text else "(RSS描述)"
            
            # P0-1: 统一Schema - UUID/published_at/fetched_at/status
            results.append({
                "id": str(uuid.uuid4()),
                "title": title,
                "source": podcast_name,
                "link": ep.get("link", ""),
                "summary": summary,
                "pubDate": pub_date,
                "published_at": pub_date,
                "fetched_at": now,
                "status": "summarized",
                "summary_source": "whisper" if full_text else "rss_description",
                "word_count": len(summary)
            })
            
            time.sleep(0.5)
    
    return results

def save_output(podcast_data):
    """保存输出文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = DATA_DIR / today
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存podcast-data.json
    podcast_path = date_dir / "podcasts.json"
    with open(podcast_path, "w", encoding="utf-8") as f:
        json.dump(podcast_data, f, ensure_ascii=False, indent=2)
    
    # 同时保存到根目录
    root_path = GHPAGES_DIR / "podcast-data.json"
    with open(root_path, "w", encoding="utf-8") as f:
        json.dump(podcast_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 已保存到 {podcast_path}")
    return str(podcast_path)

def main():
    print("=" * 60)
    print("播客检测脚本 v1.0")
    print("=" * 60)
    
    start_time = time.time()
    
    # 加载配置
    print("\n[1/4] 加载配置...")
    podcasts = load_config()
    print(f"  已加载 {len(podcasts)} 个播客")
    
    # 测试模式：只处理一个播客
    test_podcast_id = os.environ.get("TEST_PODCAST_ID", "")
    if test_podcast_id:
        podcasts = [p for p in podcasts if p["id"] == test_podcast_id]
        print(f"  ⚡ 测试模式：只处理 {podcasts[0]['name'] if podcasts else '未知'}")
    
    # 加载追踪器
    tracker = load_tracker()
    print(f"  已加载追踪器")
    
    # 检查更新
    print("\n[2/4] 检查更新...")
    updates = check_updates(podcasts, tracker)
    print(f"\n  共发现 {len(updates)} 个播客有更新")
    
    # 【重要】检查完更新立即保存tracker，不管后面的摘要是否成功
    save_tracker(tracker)
    
    # fetch only模式：只抓取不生成摘要，保存到pending文件
    fetch_only = os.environ.get("FETCH_ONLY", "false").lower() == "true"
    if fetch_only:
        pending_file = WORKSPACE / "memory" / "podcast-pending.json"
        pending = []
        for update in updates:
            for ep in update.get("episodes", []):
                pending.append({
                    "id": ep.get("id"),
                    "title": ep.get("title"),
                    "source": update.get("podcast_name"),
                    "link": ep.get("link"),
                    "pubDate": ep.get("pubDate"),
                    "audio_url": ep.get("audio_url", ""),
                })
        with open(pending_file, 'w', encoding='utf-8') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 已保存待处理列表到 {pending_file}")
        print("下一步运行: python3 scripts/podcast_download.py")
        return
    
    # 生成AI摘要
    print("\n[3/4] 生成AI摘要...")
    summaries = generate_summaries(updates)
    
    # 加载历史数据
    existing_data = []
    root_path = GHPAGES_DIR / "podcast-data.json"
    if root_path.exists():
        with open(root_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    
    # 合并数据 (去重，保留最新)
    # 按title分组，相同title保留字数多的
    merged = {}
    for p in summaries:
        merged[p['title']] = p
    for p in existing_data[:50]:
        title = p.get('title', '')
        if title not in merged or p.get('word_count', 0) > merged[title].get('word_count', 0):
            merged[title] = p
    all_podcasts = list(merged.values())[:50]
    
    # 保存输出
    print("\n[4/4] 保存输出...")
    output_path = save_output(all_podcasts)
    
    elapsed = time.time() - start_time
    print(f"\n✓ 完成! 耗时: {elapsed:.1f}秒")
    print(f"  新增 {len(summaries)} 条摘要")
    
    return output_path

if __name__ == "__main__":
    main()