#!/usr/bin/env python3
"""只翻译标题，不生成摘要"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from minimax_utils import translate_to_chinese

DATA_FILE = Path(__file__).parent.parent / "gh-pages" / "data" / "2026-04-27" / "news.json"

def main():
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    
    total = 0
    translated = 0
    for cat, items in data.items():
        for item in items:
            total += 1
            title = item.get('title', '')
            if not title:
                continue
            if not item.get('title_cn'):
                item['title_cn'] = translate_to_chinese(title)
                translated += 1
                print(f"  {translated}/{total}: {title[:35]} -> {item['title_cn'][:25]}")
            if translated % 5 == 0:
                with open(DATA_FILE, 'w') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"   [已保存]")
    
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n完成! 翻译了 {translated}/{total} 个标题")

if __name__ == '__main__':
    main()
