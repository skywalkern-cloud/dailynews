#!/usr/bin/env python3
"""增量版摘要生成 - RSS新闻：中文直接用，英文翻译成中文"""
import sys
import json
import time
from pathlib import Path

# 添加scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from minimax_utils import translate_to_chinese

DATA_FILE = Path(__file__).parent.parent / "gh-pages" / "data" / "2026-04-28" / "news.json"
BACKUP_FILE = Path(__file__).parent.parent / "gh-pages" / "data" / "2026-04-28" / "news.json.bak"

def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    # 先备份
    import shutil
    shutil.copy(DATA_FILE, BACKUP_FILE)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_chinese(text):
    """判断文本是否主要是中文（中文比例>30%）"""
    if not text:
        return False
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return chinese_chars / len(text) > 0.3

def process_item(item):
    """处理单条新闻：中文直接用，英文翻译"""
    title = item.get('title', '') or ''
    summary = item.get('summary', '') or ''
    
    # 检查是否已有有效摘要（不是损坏的）
    existing = item.get('ai_summary', '')
    if existing and 'The user asks' not in existing and existing.startswith('The user'):
        existing = None
    
    # 判断语言
    text_to_check = summary if summary else title
    is_cn = is_chinese(text_to_check)
    
    if is_cn:
        # 中文：直接用summary作为ai_summary
        item['ai_summary'] = summary
        # 生成title_cn：从summary提取第一句
        if '。' in summary:
            item['title_cn'] = summary.split('。')[0] + '。'
        elif '！' in summary:
            item['title_cn'] = summary.split('！')[0] + '！'
        elif '？' in summary:
            item['title_cn'] = summary.split('？')[0] + '？'
        else:
            item['title_cn'] = summary[:50]
        return 'chinese_used'
    else:
        # 英文：翻译summary和title
        try:
            item['ai_summary'] = translate_to_chinese(summary) if summary else translate_to_chinese(title)
            item['title_cn'] = translate_to_chinese(title)
            return 'translated'
        except Exception as e:
            item['ai_summary'] = summary
            item['title_cn'] = title
            return f'failed: {e}'

def main():
    print("加载数据...")
    data = load_data()
    
    total = 0
    processed = 0
    results = {'chinese': 0, 'translated': 0, 'failed': 0, 'skipped': 0}
    
    for cat, items in data.items():
        for item in items:
            total += 1
            score = item.get('score', 0)
            if score < 1:
                item['status'] = 'skipped'
                results['skipped'] += 1
                continue
            
            # 检查是否已有有效摘要（排除损坏的）
            existing = item.get('ai_summary', '')
            is_bad = existing and ('The user asks' in existing or '请用中文' in existing)
            if existing and not is_bad:
                # 已有有效摘要，只翻译标题
                if not item.get('title_cn'):
                    try:
                        item['title_cn'] = translate_to_chinese(item.get('title', ''))
                    except:
                        pass
                print(f"  [{processed+1}/{total}] 已有有效摘要，跳过")
                results['skipped'] += 1
            else:
                title = item.get('title', '')[:40]
                result = process_item(item)
                results[result.split(':')[0]] += 1
                print(f"  [{processed+1}/{total}] {title}... → {result}")
            
            processed += 1
            time.sleep(0.5)  # 避免API限流
            
            # 每处理5条保存一次
            if processed % 5 == 0:
                save_data(data)
                print(f"    [已保存 {processed}/{total}]")
    
    # 最终保存
    save_data(data)
    print(f"\n✓ 完成! 处理 {processed}/{total} 条")
    print(f"  中文直接用: {results['chinese']}")
    print(f"  英文翻译: {results['translated']}")
    print(f"  失败: {results['failed']}")
    print(f"  跳过: {results['skipped']}")

if __name__ == '__main__':
    main()