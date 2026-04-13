"""检查Chroma中的数据"""
from __future__ import annotations

import sys
sys.path.insert(0, 'c:/Users/19148/PycharmProjects/my-agent')

from tests.rebuild_whoosh_index import get_chroma_all_data

data = get_chroma_all_data()
print(f"共读取 {len(data)} 个文档")
print("\n前10个文档:")
for i, d in enumerate(data[:10]):
    title = d['metadata'].get('title', 'N/A')
    content_preview = d['content'][:50] if d['content'] else 'N/A'
    print(f"  {i+1}. {d['chroma_id'][:20]}... | {title[:30]} | {content_preview}...")
