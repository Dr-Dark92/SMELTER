"""Prompt-size estimate must never fall below measured Qwen token counts."""
import json
import unittest
from context_budget import bounded, estimate_tokens

# Real prompt_eval_count from qwen3.5:4b on 2026-10-24 for one user message
# holding each text (includes the chat template's 13-token overhead).
MEASURED = {
    'dense json': (json.dumps([{'id': i, 'k': f'v{i}', 'x': [i, i * 2]} for i in range(300)]), 8629),
    'chinese': ('本地开发和资产检查工作台。仪表板在环回地址上运行，并在第一次使用时选择存储目录。' * 40, 892),
    'japanese': ('ローカル開発とアセット検査のワークベンチです。初回起動時に保存先を選択します。' * 40, 892),
    'arabic': ('منصة عمل محلية للتطوير وفحص الأصول. اختر مجلد التخزين عند أول استخدام.' * 40, 772),
    'emoji': ('✅ ⚠️ → — · ✓ 🚀 🧪 📦 ' * 120, 2172),
    'base64': ('QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVphYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ejAxMjM0NTY3ODk' * 60, 3312),
    'hex hashes': (' '.join(f'{i:064x}' for i in range(1, 120)), 7746),
}


class ContextEstimateTests(unittest.TestCase):
    def estimate(self, text):
        # Same serialization and per-message reserve as bounded().
        _, meta = bounded([{'role': 'user', 'content': text}], [], 131072, 128)
        return meta['estimated_prompt_tokens']

    def test_estimate_is_never_below_measured_tokens(self):
        for name, (text, tokens) in MEASURED.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(self.estimate(text), tokens)

    def test_dense_json_is_no_longer_under_counted(self):
        text, tokens = MEASURED['dense json']
        old = (len(json.dumps({'messages': [{'role': 'user', 'content': text}], 'tools': []},
                              ensure_ascii=False).encode()) + 1) // 2 + 32
        self.assertLess(old, tokens)
        self.assertGreaterEqual(self.estimate(text), tokens)

    def test_english_is_not_double_counted(self):
        text = ('SMELTER is a local-first development and asset-inspection workbench. '
                'Its active interface is the Python dashboard. ') * 80
        # About 20 words per sentence pair; real Qwen use is near one token per word.
        self.assertLess(estimate_tokens(text), len(text.encode()) / 3)
