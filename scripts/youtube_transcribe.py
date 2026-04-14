#!/usr/bin/env python3
"""
YouTube转录脚本 - youtube_transcribe.py
分批处理第3步：Whisper转录
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# 设置路径
SCRIPT_DIR = Path(__file__).parent
WORKSPACE = SCRIPT_DIR.parent
PENDING_FILE = WORKSPACE / "memory" / "youtube-pending.json"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# 懒加载faster-whisper模型
_faster_whisper_model = None

def get_faster_whisper_model():
    global _faster_whisper_model
    if _faster_whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            print("    🔄 加载faster-whisper模型...")
            _faster_whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            print("    ✅ 模型加载完成")
        except Exception as e:
            print(f"    ⚠️ faster-whisper加载失败: {e}")
            _faster_whisper_model = False
    return _faster_whisper_model if _faster_whisper_model else None

def transcribe_with_whisper(audio_path: str) -> Optional[str]:
    """转录音频"""
    if not audio_path or not Path(audio_path).exists():
        return None
    
    # 优先用faster-whisper
    model = get_faster_whisper_model()
    if model:
        try:
            print(f"    🎤 faster-whisper转录中...")
            segments, _ = model.transcribe(audio_path)
            full_text = " ".join([s.text for s in segments])
            print(f"    ✅ 转录完成: {len(full_text)}字")
            return full_text
        except Exception as e:
            print(f"    ⚠️ faster-whisper失败: {e}")
    
    # Fallback到OpenAI Whisper
    if OPENAI_API_KEY:
        try:
            import openai
            print(f"    🎤 OpenAI Whisper转录中...")
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            with open(audio_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            full_text = transcript.text
            print(f"    ✅ 转录完成: {len(full_text)}字")
            return full_text
        except Exception as e:
            print(f"    ⚠️ OpenAI Whisper失败: {e}")
    
    return None

def main():
    print("=" * 60)
    print("YouTube转录脚本")
    print("=" * 60)
    
    if not PENDING_FILE.exists():
        print("❌ 没有待处理的YouTube视频")
        return
    
    with open(PENDING_FILE, encoding='utf-8') as f:
        pending = json.load(f)
    
    # 只处理有audio_path但没有transcript的
    to_transcribe = [p for p in pending if p.get("audio_path") and not p.get("transcript")]
    
    if not to_transcribe:
        print("✓ 没有待转录的YouTube视频")
        return
    
    print(f"\n待转录: {len(to_transcribe)} 条")
    
    for i, ep in enumerate(to_transcribe):
        print(f"\n[{i+1}/{len(to_transcribe)}] {ep.get('title', '')[:50]}...")
        audio_path = ep.get("audio_path", "")
        transcript = transcribe_with_whisper(audio_path)
        if transcript:
            ep["transcript"] = transcript
            ep["transcript_time"] = datetime.now().isoformat()
    
    # 保存结果
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 转录完成")

if __name__ == "__main__":
    main()
