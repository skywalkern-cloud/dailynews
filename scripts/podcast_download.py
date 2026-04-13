#!/usr/bin/env python3
"""
播客音频下载脚本 - podcast_download.py
分批处理第2步：下载待处理播客的音频
"""
import os
import sys
import json
import time
import urllib.request
from pathlib import Path
from datetime import datetime

# 设置路径
SCRIPT_DIR = Path(__file__).parent
WORKSPACE = SCRIPT_DIR.parent
DATA_DIR = WORKSPACE / "gh-pages" / "data"
PENDING_FILE = WORKSPACE / "memory" / "podcast-pending.json"
AUDIO_DIR = Path("/tmp/podcast_audio")

def ensure_dir():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def download_audio(episode, output_dir=AUDIO_DIR):
    """下载单个播客音频"""
    audio_url = episode.get("audio_url", "")
    if not audio_url:
        return None
    
    episode_id = episode.get("id", "unknown")
    audio_path = output_dir / f"{episode_id}.mp3"
    
    if audio_path.exists():
        print(f"    ✓ 已存在，跳过: {audio_path.name}")
        return str(audio_path)
    
    try:
        print(f"    📥 下载: {audio_url[:60]}...")
        urllib.request.urlretrieve(audio_url, audio_path)
        print(f"    ✅ 完成: {audio_path.name}")
        return str(audio_path)
    except Exception as e:
        print(f"    ❌ 失败: {e}")
        return None

def main():
    print("=" * 60)
    print("播客音频下载脚本")
    print("=" * 60)
    
    if not PENDING_FILE.exists():
        print("❌ 没有待处理的播客，请先运行 podcast_fetch.py")
        return
    
    with open(PENDING_FILE, encoding='utf-8') as f:
        pending = json.load(f)
    
    if not pending:
        print("✓ 没有待下载的音频")
        return
    
    print(f"\n待处理: {len(pending)} 条")
    ensure_dir()
    
    for i, ep in enumerate(pending):
        print(f"\n[{i+1}/{len(pending)}] {ep.get('title', '')[:50]}...")
        audio_path = download_audio(ep)
        if audio_path:
            ep["audio_path"] = audio_path
        time.sleep(1)  # 避免请求过快
    
    # 保存结果
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 音频下载完成")

if __name__ == "__main__":
    main()
