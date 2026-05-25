#!/bin/bash
# Layer2 本地测试脚本
# 用于在部署前验证所有输出是否符合预期

cd ~/.openclaw/workspace-dailynews

echo "=== Step 1: 测试 minimax_utils ==="
python3 scripts/test_minimax_utils.py

echo ""
echo "=== Step 2: 验证 news.json ==="
if [ -f gh-pages/news.json ]; then
    python3 -c "
import json
with open('gh-pages/news.json') as f:
    d = json.load(f)
# 检查 title_cn
missing = sum(1 for cat in d.values() if isinstance(cat, list) for item in cat if not item.get('title_cn'))
print(f'title_cn 缺失: {missing} 条')
# 检查摘要失败
failed = sum(1 for cat in d.values() if isinstance(cat, list) for item in cat if item.get('ai_summary') == '[摘要生成失败]')
print(f'摘要失败: {failed} 条')
"
else
    echo "⚠️ gh-pages/news.json 不存在，跳过"
fi

echo ""
echo "=== Step 3: 生成 HTML ==="
python3 scripts/generate_html_v2.py

echo ""
echo "=== 完成 ==="
