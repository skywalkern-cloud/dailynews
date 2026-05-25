#!/usr/bin/env python3
"""
Minimax Utils - AI摘要生成工具
"""
import os
import re
import time
import json
import logging
import requests
from pathlib import Path

# 配置日志
_log_dir = Path(__file__).parent.parent / 'logs'
_log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(_log_dir / 'minimax.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 从环境变量读取API Key
# 从配置文件读取API Key
_config_path = Path(__file__).parent / 'config' / 'api_config.json'
if _config_path.exists():
    with open(_config_path) as f:
        _config = json.load(f)
        MINIMAX_API_KEY = _config.get("MINIMAX_API_KEY", os.environ.get("MINIMAX_API_KEY", ""))
else:
    MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")

def call_minimax(prompt, max_words=200):
    """调用MiniMax API"""
    if not MINIMAX_API_KEY:
        logger.warning("[MiniMax] API Key未设置")
        return None, "API_KEY_MISSING"

    url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "MiniMax-M2.7",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_words * 10
    }

    for attempt in range(3):
        try:
            r = requests.post(url, json=data, headers=headers, timeout=60)
            logger.info(f"[MiniMax] 请求状态: {r.status_code}, attempt={attempt+1}")

            if r.status_code == 200:
                result = r.json()
                msg = result.get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "") or ""
                reasoning = msg.get("reasoning_content", "") or ""
                # 优先用content，否则从reasoning提取最终答案
                if content.strip():
                    text = content.strip()
                elif reasoning:
                    import re
                    m = re.search(r'(?:final\s+answer:?|thus,?\s+)(["\']?)([^"\n]+)\1?\s*$', reasoning, re.IGNORECASE)
                    if m:
                        text = m.group(2).strip('" ' + "' ")
                    else:
                        text = reasoning.strip()
                if text:
                    logger.info(f"[MiniMax] 成功, 输出长度: {len(text)}")
                    return text, "SUCCESS"
            elif r.status_code == 429:
                # Rate limit - 等待后重试
                wait_time = (attempt + 1) * 10
                logger.warning(f"[MiniMax] Rate limit, 等待 {wait_time}s 后重试 (attempt {attempt+1}/3)")
                time.sleep(wait_time)
                continue
            elif r.status_code == 400:
                # Bad request - 可能是内容问题，不再重试
                err_info = r.text[:200]
                logger.error(f"[MiniMax] Bad request: {err_info}")
                return None, f"BAD_REQUEST: {err_info}"
            elif r.status_code == 401:
                logger.error(f"[MiniMax] 认证失败")
                return None, "AUTH_FAILED"
            else:
                err_info = r.text[:200]
                logger.error(f"[MiniMax] API错误 {r.status_code}: {err_info}")
                if attempt < 2:
                    time.sleep(2)
                    continue
                return None, f"HTTP_{r.status_code}: {err_info}"
        except Exception as e:
            logger.error(f"[MiniMax] 请求异常: {e}, attempt={attempt+1}/3")
            if attempt < 2:
                time.sleep(2)

    logger.error("[MiniMax] 3次尝试全部失败")
    return None, "ALL_ATTEMPTS_FAILED"

def generate_summary(content, max_words=200, prompt=None):
    """通用摘要生成函数（MiniMax）
    返回: (摘要文本, 状态字符串)
    """
    if not content:
        return "[内容为空]", "EMPTY_CONTENT"

    if not MINIMAX_API_KEY:
        logger.warning("[generate_summary] MiniMax API Key未设置")
        return "[API Key未设置]", "API_KEY_MISSING"

    if prompt is None:
        prompt = "请用中文，约" + str(max_words) + "字总结以下内容：\n" + content[:1500]

    result, status = call_minimax(prompt, max_words)
    if result:
        return result, status
    return "[摘要生成失败]", status

def generate_news_summary(content):
    """新闻摘要（200字）"""
    result, status = generate_summary(content, 200)
    logger.info(f"[generate_news_summary] status={status}, len={len(result)}")
    return clean_news_summary(result)


def clean_news_summary(text):
    """从MiniMax返回的文本中提取真正的中文摘要"""
    if not text or len(text) < 20:
        return text
    
    if '请用中文' not in text and 'The user asks' not in text:
        return text
    
    import re
    
    # 策略1: 提取双引号中的中文内容（找最长的）
    quotes = re.findall(r'"([^"]+)"', text)
    chinese_quotes = [q for q in quotes if len(q) > 50 and re.search(r'[一-￿]{10,}', q)]
    if chinese_quotes:
        for q in chinese_quotes:
            if '周一' in q or '企业' in q or '市场' in q or len(q) > 100:
                return q.strip()
        return max(chinese_quotes, key=len).strip()
    
    # 策略2: 直接找以周一开头的中文段落
    m = re.search(r'(周一.{50,}?[。？！])', text)
    if m:
        return m.group(1).strip()
    
    # 策略3: 找包含企业的开头段落
    m = re.search(r'(企业.{50,}?[。？！])', text)
    if m:
        return m.group(1).strip()
    
    return text


def generate_podcast_summary(content):
    """播客摘要，800字以上中文"""
    if not content or len(content.strip()) < 50:
        logger.warning(f"[generate_podcast_summary] 内容不足: {len(content) if content else 0}字符")
        return "[内容不足，无法生成摘要]"

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

    result, status = generate_summary(content, 2000, prompt)
    logger.info(f"[generate_podcast_summary] status={status}, len={len(result)}")

    if len(result) < 100 and "[摘要生成失败]" not in result and "[内容不足" not in result:
        logger.error(f"[generate_podcast_summary] 输出异常短: {result[:50]}")
        return f"[摘要生成失败: {status}]"

    return result

def generate_youtube_summary(content):
    """YouTube视频摘要，800字+，带分段"""
    if not content or len(content.strip()) < 50:
        logger.warning(f"[generate_youtube_summary] 内容不足: {len(content) if content else 0}字符")
        return "[内容不足，无法生成摘要]"

    prompt = (
        "你是一个专业的视频内容摘要专家。请为以下视频内容生成一段详细的中文摘要，要求：\n"
        "1. 字数800字以上\n"
        "2. 必须用 **标题** 格式（Markdown二级标题）开头，标题使用视频的核心主题\n"
        "3. 按内容逻辑分段，每段用 **小标题** 开头\n"
        "4. 全面覆盖视频的主要观点、关键论据、重要细节\n"
        "5. 最后给出总结和核心启示\n"
        "6. 只输出摘要内容，不要任何解释或引导语\n\n"
        "视频内容：\n" + content[:3000]
    )

    result, status = generate_summary(content, 2000, prompt)
    logger.info(f"[generate_youtube_summary] status={status}, len={len(result)}")

    if len(result) < 100 and "[摘要生成失败]" not in result and "[内容不足" not in result:
        logger.error(f"[generate_youtube_summary] 输出异常短: {result[:50]}")
        return f"[摘要生成失败: {status}]"

    return result

def _split_into_sentences(text):
    """将英文文本按句号、感叹号、问号拆分成句子列表
    保留原标点符号，过滤空字符串
    """
    # 用正则按 . ! ? 拆分，同时保留分隔符
    parts = re.split(r'(?<=[.!?])\s+', text)
    sentences = []
    for p in parts:
        p = p.strip()
        if p:
            sentences.append(p)
    # 如果按句子拆失败或只有一个句子，退而按段落或最大长度拆分
    if len(sentences) <= 1 and len(text) > 2000:
        # 按段落拆
        paragraphs = re.split(r'\n\s*\n', text)
        sentences = [p.strip() for p in paragraphs if p.strip()]
    if len(sentences) <= 1 and len(text) > 1000:
        # 强行分块，每块约800-1000字符
        sentences = []
        current = []
        current_len = 0
        # 先用标点拆，拆不动则按任意空格/换行分块
        parts = re.split(r'(?<=[.,!?;:])\s*', text)
        if len(parts) <= 1:
            # 没有任何标点分隔，按空格/换行分块
            parts = re.split(r'\s+', text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if current_len + len(part) > 800 and current:
                sentences.append(' '.join(current))
                current = [part]
                current_len = len(part)
            else:
                current.append(part)
                current_len += len(part)
        if current:
            sentences.append(' '.join(current))
    return sentences


def _call_minimax_chunk(chunk):
    """翻译单个文本块（句子或段落），返回翻译结果字符串"""
    if not chunk or not chunk.strip():
        return ""
    chunk = chunk.strip()
    prompt = f"请将以下英文文本翻译成中文，只输出翻译结果，不要任何解释：\n{chunk}"
    # 根据chunk长度动态调整max_words
    est_chinese_chars = len(chunk) * 2  # 中文比英文短
    max_words = max(200, min(2000, est_chinese_chars))
    result, status = call_minimax(prompt, max_words=max_words)
    logger.info(f"[_call_minimax_chunk] status={status}, input_len={len(chunk)}, output_len={len(result) if result else 0}")
    if result:
        return result.strip()
    return chunk  # 翻译失败则返回原文


def translate_to_chinese(text):
    """将英文翻译为中文
    如果文本较长（>1000字符），自动拆分成多段分别翻译再拼接，
    避免MiniMax输出截断问题。
    """
    if not text:
        return text

    has_en = any("A" <= c <= "Z" or "a" <= c <= "z" for c in text)
    if not has_en:
        return text

    if sum(1 for c in text if "\u4e00" <= c <= "\u9fff") > len(text) * 0.5:
        return text

    # 短文本直接翻译
    if len(text) <= 1000:
        prompt = f"请将以下文本翻译成中文，只输出翻译结果，不要任何解释：\n{text}"
        result, status = call_minimax(prompt, max_words=2000)
        logger.info(f"[translate_to_chinese] status={status}, len={len(result)}, mode=direct")
        return result

    # 长文本分段翻译
    logger.info(f"[translate_to_chinese] 长文本检测: {len(text)}字符, 分段翻译")
    sentences = _split_into_sentences(text)
    logger.info(f"[translate_to_chinese] 拆分为 {len(sentences)} 段")

    translated_parts = []
    for i, sentence in enumerate(sentences):
        logger.info(f"[translate_to_chinese] 翻译第 {i+1}/{len(sentences)} 段, 长度={len(sentence)}")
        translated = _call_minimax_chunk(sentence)
        translated_parts.append(translated)
        # 短暂停顿避免API限流
        if i < len(sentences) - 1:
            time.sleep(0.5)

    result = ''.join(translated_parts)
    logger.info(f"[translate_to_chinese] 拼接完成, 总长度={len(result)}, 分段数={len(sentences)}")
    return result
