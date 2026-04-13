#!/usr/bin/env python3
"""
YouTube检测脚本 - youtube_daily.py
功能：检测12个YouTube频道更新 + AI摘要生成 + 输出到gh-pages/youtube-data.json
"""
import os
import sys
import json
import time
import uuid
import yt_dlp
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from minimax_utils import generate_youtube_summary, translate_to_chinese

# 配置
WORK_DIR = Path(os.path.expanduser("~/.openclaw/workspace-dailynews"))
CONFIG_DIR = WORK_DIR / "config"
GHPAGES_DIR = WORK_DIR / "gh-pages"
MEMORY_DIR = WORK_DIR / "memory"
DATA_DIR = GHPAGES_DIR / "data"

def load_config():
    with open(CONFIG_DIR / "sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)
    return sources.get("youtube_channels", [])

def load_tracker():
    """加载YouTube追踪器"""
    tracker_path = MEMORY_DIR / "youtube-tracker.json"
    if tracker_path.exists():
        with open(tracker_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channels": {}, "last_update": ""}

def save_tracker(tracker):
    """保存YouTube追踪器"""
    tracker_path = MEMORY_DIR / "youtube-tracker.json"
    tracker["last_update"] = datetime.now().isoformat()
    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)

def fetch_channel_videos(channel_name, handle):
    """通过yt-dlp获取频道最新视频"""
    try:
        # 使用/videos子路径 + extract_flat=True 获取视频列表
        url = f"https://www.youtube.com/{handle}/videos"
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,  # 获取完整metadata以便提取description
            'playlistend': 5,       # 最多取5个
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and 'entries' in info:
                videos = []
                for entry in info['entries']:
                    if entry:
                        video_id = entry.get('id', '')
                        videos.append({
                            "title": entry.get('title', ''),
                            "upload_date": entry.get('upload_date', ''),
                            "description": entry.get('description', '')[:500] if entry.get('description') else "",
                            "url": f"https://www.youtube.com/watch?v={video_id}"
                        })
                return videos
    except Exception as e:
        print(f"    ✗ 获取失败: {e}")
    
    return []

def check_updates(channels, tracker):
    """检查频道更新 - 核心逻辑：
    - tracker 保存的是「截止点」（上次抓取时最旧的 video 的 title）
    - 迭代方向：从最新到最旧，遇到 last_title 就 break（不包含它本身）
    - 首次运行（tracker 为空）：只取最新 3-5 个作为兜底保护
    """
    updates = []
    
    for channel in channels:
        name = channel["name"]
        handle = channel["handle"]
        
        print(f"  检查 {name} ({handle})...")
        
        videos = fetch_channel_videos(name, handle)
        
        if not videos:
            print(f"    ⚠️ 无视频或获取失败")
            continue
        
        # 从 tracker 读取截止标记
        channel_state = tracker.get("channels", {}).get(handle, {})
        last_title = channel_state.get("last_title", "")
        
        new_videos = []
        if not last_title:
            # 首次运行：取最新 3-5 个作为兜底保护
            new_videos = videos[:5]
            print(f"    ⚡ 首次运行，取最新 {len(new_videos)} 个")
        else:
            # 正常更新：从最新到最旧迭代，遇到 last_title 就 break
            for v in videos:
                if v.get("title") == last_title:
                    break
                new_videos.append(v)
        
        if new_videos:
            print(f"    ✓ 发现 {len(new_videos)} 个新视频: {[v['title'][:30] for v in new_videos]}")
            updates.append({
                "channel_name": name,
                "channel_handle": handle,
                "videos": new_videos
            })
            
            # 保存截止点 = 这次抓到的最旧的 video（用于下次识别边界）
            oldest_v = videos[-1]
            if "channels" not in tracker:
                tracker["channels"] = {}
            tracker["channels"][handle] = {
                "name": name,
                "last_url": oldest_v.get("url", ""),
                "last_title": oldest_v.get("title", ""),
                "last_upload_date": oldest_v.get("upload_date", "")
            }
        else:
            print(f"    - 无新视频")
        
        time.sleep(2)
    
    return updates

def generate_summaries(updates):
    """为更新的视频生成AI摘要"""
    results = []
    now = datetime.now().isoformat()
    
    for update in updates:
        channel_name = update["channel_name"]
        videos = update["videos"]
        
        for video in videos:
            title = video.get("title", "")
            # 翻译标题
            title_cn = translate_to_chinese(title)
            desc = video.get("description", "")
            upload_date = video.get("upload_date", "")
            url = video.get("url", "")
            
            print(f"  生成摘要: {title_cn[:40]}...")
            
            # 调用AI生成摘要（800字+，带分段）
            summary = generate_youtube_summary(desc)
            
            # P0-1: 统一Schema - UUID/published_at/fetched_at/status
            results.append({
                "id": str(uuid.uuid4()),
                "title": title_cn if title_cn != title else title,
                "source": channel_name,
                "url": url,
                "upload_date": upload_date,
                "published_at": upload_date,
                "fetched_at": now,
                "summary": summary,
                "status": "summarized"
            })
            
            time.sleep(0.5)
    
    return results

def save_output(youtube_data):
    """保存输出文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = DATA_DIR / today
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存youtube.json
    youtube_path = date_dir / "youtube.json"
    with open(youtube_path, "w", encoding="utf-8") as f:
        json.dump(youtube_data, f, ensure_ascii=False, indent=2)
    
    # 同时保存到根目录
    root_path = GHPAGES_DIR / "youtube-data.json"
    with open(root_path, "w", encoding="utf-8") as f:
        json.dump(youtube_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 已保存到 {youtube_path}")
    return str(youtube_path)

def main():
    print("=" * 60)
    print("YouTube检测脚本 v1.0")
    print("=" * 60)
    
    start_time = time.time()
    
    # 加载配置
    print("\n[1/4] 加载配置...")
    channels = load_config()
    print(f"  已加载 {len(channels)} 个YouTube频道")
    
    # 加载追踪器
    tracker = load_tracker()
    print(f"  已加载追踪器")
    
    # 检查更新
    print("\n[2/4] 检查频道更新...")
    updates = check_updates(channels, tracker)
    print(f"\n  共发现 {len(updates)} 个频道有更新")
    
    # 【重要】检查完更新立即保存tracker，不管后面的摘要是否成功
    save_tracker(tracker)
    
    # 生成AI摘要
    print("\n[3/4] 生成AI摘要...")
    summaries = generate_summaries(updates)
    
    # 加载历史数据
    existing_data = []
    root_path = GHPAGES_DIR / "youtube-data.json"
    if root_path.exists():
        with open(root_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except:
                existing_data = []
    
    # 合并数据 (保留历史)
    all_videos = summaries + existing_data[:30]  # 保留最近30条
    
    # 保存输出
    print("\n[4/4] 保存输出...")
    output_path = save_output(all_videos)
    
    elapsed = time.time() - start_time
    print(f"\n✓ 完成! 耗时: {elapsed:.1f}秒")
    print(f"  新增 {len(summaries)} 条摘要")
    
    return output_path

if __name__ == "__main__":
    main()