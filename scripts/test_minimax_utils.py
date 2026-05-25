#!/usr/bin/env python3
"""
minimax_utils.py 单元测试
用于验证 generate_podcast_summary, translate_to_chinese, generate_youtube_summary 等核心函数
"""
import sys
import os

# 添加 scripts 目录到路径，以便导入 minimax_utils
sys.path.insert(0, os.path.dirname(__file__))

from minimax_utils import (
    generate_podcast_summary,
    translate_to_chinese,
    generate_youtube_summary,
)


def test_generate_podcast_summary_chinese():
    """中文内容应该生成中文摘要，不是英文翻译"""
    content = "今天讨论中国经济一季度数据。数据显示GDP增长符合预期。我们邀请了三位经济学家。"
    result = generate_podcast_summary(content)
    # 验证结果
    assert result, "结果不能为空"
    assert not result.startswith("["), f"不应该是错误标记，当前: {result}"
    # 验证是中文
    chinese_ratio = sum(1 for c in result if '\u4e00' <= c <= '\u9fff') / len(result)
    assert chinese_ratio > 0.5, f"结果应该是中文，当前中文比例{chinese_ratio:.1%}"
    print(f"✅ test_generate_podcast_summary_chinese 通过")


def test_generate_podcast_summary_english():
    """英文内容应该翻译成中文"""
    content = "Today we discuss the quarterly economic data showing GDP growth meeting expectations."
    result = generate_podcast_summary(content)
    # 验证结果是中文
    assert result, f"结果不能为空，当前: {result}"
    chinese_ratio = sum(1 for c in result if '\u4e00' <= c <= '\u9fff') / len(result)
    assert chinese_ratio > 0.5, f"结果应该是中文翻译，当前比例{chinese_ratio:.1%}"
    print(f"✅ test_generate_podcast_summary_english 通过")


def test_generate_podcast_summary_empty():
    """空内容应该返回空"""
    result = generate_podcast_summary("")
    assert result == "", f"空内容应返回空字符串，当前: {result}"
    print(f"✅ test_generate_podcast_summary_empty 通过")


def test_translate_to_chinese():
    """翻译功能测试 - 英文应翻译成中文，中文应保持不变"""
    # 英文翻译测试
    en_text = "The quarterly GDP growth rate met expectations, showing resilience in the face of global challenges."
    en_result = translate_to_chinese(en_text)
    assert en_result, "翻译结果不能为空"
    assert not en_result.startswith("["), f"不应该是错误标记，当前: {en_result}"
    chinese_ratio = sum(1 for c in en_result if '\u4e00' <= c <= '\u9fff') / len(en_result)
    assert chinese_ratio > 0.5, f"英文应翻译成中文，当前中文比例{chinese_ratio:.1%}"
    print(f"✅ test_translate_to_chinese (EN→CN) 通过")

    # 中文保持不变测试
    cn_text = "这是中文内容，不需要翻译。"
    cn_result = translate_to_chinese(cn_text)
    assert cn_result, "翻译结果不能为空"
    # 中文内容应保持大部分字符不变
    chinese_ratio = sum(1 for c in cn_result if '\u4e00' <= c <= '\u9fff') / len(cn_result)
    assert chinese_ratio > 0.5, f"中文内容应保持不变，当前中文比例{chinese_ratio:.1%}"
    print(f"✅ test_translate_to_chinese (CN keep) 通过")


def test_generate_youtube_summary():
    """YouTube摘要测试 - 中文内容应直接摘要"""
    content = "本期视频介绍了最新的人工智能技术发展趋势，重点讨论了大型语言模型的最新进展和应用场景。"
    result = generate_youtube_summary(content)
    assert result, "结果不能为空"
    assert not result.startswith("["), f"不应该是错误标记，当前: {result}"
    chinese_ratio = sum(1 for c in result if '\u4e00' <= c <= '\u9fff') / len(result)
    assert chinese_ratio > 0.5, f"结果应该是中文，当前中文比例{chinese_ratio:.1%}"
    print(f"✅ test_generate_youtube_summary 通过")


if __name__ == "__main__":
    print("Running DailyNews minimax_utils tests...")
    print("-" * 40)
    test_generate_podcast_summary_chinese()
    test_generate_podcast_summary_english()
    test_generate_podcast_summary_empty()
    test_translate_to_chinese()
    test_generate_youtube_summary()
    print("-" * 40)
    print("\n✅ All tests passed!")
