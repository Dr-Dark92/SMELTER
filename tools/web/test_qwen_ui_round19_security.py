#!/usr/bin/env python3
"""Round 19 deterministic HTML security gate tests; no Ollama or browser required."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).with_name("test_qwen_ui_round19.py")
spec=importlib.util.spec_from_file_location("round19",p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
GOOD="""<!doctype html><html><head><style>body{color:#fff;background:#000}</style></head>
<body><nav>SMELTER</nav><main><section>Overview</section><section>GitHub</section>
<section>Skills &amp; Tools</section><section>OpenCode</section>
<section>Research</section><article>"""+"Example dashboard content. "*65+"""</article></main></body></html>"""
class Tests(unittest.TestCase):
    def test_good(self):self.assertEqual(mod.validate(GOOD),[])
    def test_script(self):self.assertTrue(mod.validate(GOOD.replace("</main>","<script>alert(1)</script></main>")))
    def test_remote_css(self):self.assertTrue(mod.validate(GOOD.replace("color:#fff","background:url(https://evil.test/a)")))
    def test_event_handler(self):self.assertTrue(mod.validate(GOOD.replace("<nav>","<nav onclick='evil()'>")))
    def test_external_link(self):self.assertTrue(mod.validate(GOOD.replace("<nav>","<nav><a href='https://evil.test'>x</a>")))
    def test_missing_sections(self):self.assertTrue(mod.validate(GOOD.replace("OpenCode","Editor")))
    def test_network_api(self):self.assertTrue(mod.validate(GOOD.replace("</main>","fetch('/api/token')</main>")))
if __name__=="__main__":unittest.main(verbosity=2)
