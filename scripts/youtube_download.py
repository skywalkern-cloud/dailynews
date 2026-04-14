#!/usr/bin/env python3
"""
YouTube音频下载脚本 - youtube_download.py
功能：下载待处理YouTube视频的音频
"""
import os
import sys
import json
import time
import yt_dlp
from pathlib import Path
from datetime import datetime

# 设置路径
SCRIPT_DIR = Path(__file__).parent
WORKSPACE = SCRIPT_DIR.parent
PENDING_FILE = WORKSPACE / "memory" / "youtube-pending.json"
AUDIO_DIR = Path("/tmp/youtube_audio")

# yt-dlp配置
YDLP_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': str(AUDIO_DIR / '%(id)s.%(ext)s'),
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

def ensure_dir():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def download_audio(episode, output_dir=AUDIO_DIR):
    """下载单个YouTube视频音频"""
    video_url = episode.get("url", "")
    if not video_url:
        return None
    
    video_id = episode.get("id", "unknown")
    audio_path = output_dir / f"{video_id}.mp3"
    
    if audio_path.exists():
        print(f"    ✓ 已存在，跳过: {audio_path.name}")
        return str(audio_path)
    
    opts = YDLP_OPTS.copy()
    opts['outtmpl'] = str(output_dir / f'{video_id}.%(ext)s')
    
    try:
        print(f"    📥 下载: {video_url[:60]}...")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])
        print(f"    ✅ 完成: {video_id}")
        
        # 检查下载的文件
        for ext in ['mp3', 'm4a', 'webm', 'wav']:
            possible_path = output_dir / f"{video_id}.{ext}"
            if possible_path.exists():
                return str(possible_path)
        return str(audio_path)
        
    except Exception as e:
        print(f"    ❌ 失败: {e}")
        return None

def main():
    print("=" * 60)
    print("YouTube音频下载脚本")
    print("=" * 60)
    
    if not PENDING_FILE.exists():
        print("❌ 没有待处理的YouTube，请先运行 youtube_daily.py")
        return
    
    with open(PENDING_FILE, encoding='utf-8') as f:
        pending = json.load(f)
    
    if not pending:
        print("✓ 没有待下载的视频")
        return
    
    print(f"\n待处理: {len(pending)} 条")
    ensure_dir()
    
    for i, ep in enumerate(pending):
        print(f"\n[{i+1}/{len(pending)}] {ep.get('title', '')[:50]}...")
        audio_path = download_audio(ep)
        if audio_path:
            ep["audio_path"] = audio_path
        time.sleep(2)  # 避免请求过快
    
    # 保存结果
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ YouTube音频下载完成")

if __name__ == "__main__":
    main()