#!/usr/bin/env python3
"""MiniMax/Gemini API 工具"""
import os
import re
import requests

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyCxutEEieDJapzHi2-9H8FfEJgpAR1cDAc")

def generate_summary(content, max_words=200, prompt=None):
    if not GOOGLE_API_KEY:
        return "[摘要生成失败]"
    
    if prompt is None:
        prompt = "请用约" + str(max_words) + "字总结：" + content[:500]
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    data = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": max_words * 4}}
    params = {"key": GOOGLE_API_KEY}
    
    try:
        r = requests.post(url, json=data, params=params, timeout=60)
        if r.status_code == 200:
            return r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    except:
        pass
    return "[失败]"

def generate_news_summary(content):
    return generate_summary(content, 200)

def generate_podcast_summary(content):
    """生成播客摘要，800字以上中文"""
    prompt = (
        "你是一个专业的播客内容摘要专家。请为以下播客内容生成一段详细的中文摘要，要求：\n"
        "1. 字数800字以上\n"
        "2. 必须用 **标题** 格式（Markdown二级标题）开头，标题使用播客的核心主题\n"
        "3. 按内容逻辑分段，每段用 **小标题** 开头\n"
        "4. 全面覆盖播客的主要观点、关键论据、重要细节\n"
        "5. 最后给出总结和核心启示\n"
        "6. 只输出摘要内容，不要任何解释或引导语\n\n"
        "播客内容：\n" + content[:3000]
    )
    return generate_summary(content, 2000, prompt)

def generate_youtube_summary(content):
    """生成YouTube视频摘要，800字+，带分段"""
    if not content or len(content.strip()) < 50:
        return "[内容不足，无法生成摘要]"
    
    prompt = "你是一个专业的视频内容摘要专家。请为以下视频内容生成一段详细的中文摘要，要求：\n1. 字数800字以上\n2. 必须用 **标题** 格式（Markdown二级标题）开头，标题使用视频的核心主题\n3. 按内容逻辑分段，每段用 **小标题** 开头\n4. 全面覆盖视频的主要观点、关键论据、重要细节\n5. 最后给出总结和核心启示\n6. 只输出摘要内容，不要任何解释或引导语\n\n视频内容：\n" + content[:3000]
    
    return generate_summary(content, 2000, prompt)

def translate_to_chinese(text):
    """将英文标题翻译为中文，确保翻译完整"""
    if not text:
        return text
    
    # 检查是否有英文字母
    has_en = any("A" <= c <= "Z" or "a" <= c <= "z" for c in text)
    if not has_en:
        return text
    
    # 如果中文占比超过50%，认为已是中文
    if sum(1 for c in text if "\u4e00" <= c <= "\u9fff") > len(text) * 0.5:
        return text
    
    # 检查是否包含太多数字、符号等（可能是代码或专有名词）
    alpha_count = sum(1 for c in text if c.isalpha())
    en_count = sum(1 for c in text if "A" <= c <= "Z" or "a" <= c <= "z")
    if alpha_count > 0 and en_count / alpha_count < 0.3:
        return text
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    # 使用system instruction强制只输出翻译
    data = {
        "systemInstruction": {"parts": [{"text": "你是一个翻译助手，只输出翻译结果，不要任何解释、注释或额外内容。只输出翻译后的中文标题，不要加引号或任何格式符号。"}]},
        "contents": [{"parts": [{"text": f"请将以下标题翻译成中文，只输出翻译结果：{text}"}]}],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.3}
    }
    params = {"key": GOOGLE_API_KEY}
    
    try:
        r = requests.post(url, json=data, params=params, timeout=30)
        if r.status_code == 200:
            t = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            # 清理可能的引号或格式
            t = t.strip('"\'"\'\n ')
            if t and len(t) >= 3:
                return t
    except:
        pass
    return text
