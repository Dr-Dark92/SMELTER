"""Proposal-time Lua parsing: broken files are refused before they reach the copy."""
import unittest
from unittest.mock import patch

import coding_workspace as coding
import sandbox
import test_coding_workspace as base_tests
from test_lua_profile import toolchain

GOOD = 'local M = {}\nfunction M.value() return 1 end\nreturn M\n'


class LuaProposalGateTests(unittest.TestCase):
    def setUp(self):
        base_tests.CodingWorkspaceTests.setUp(self)
        ready = toolchain()
        if ready:
            configured = patch('sandbox.config', return_value={**sandbox.DEFAULT, **ready['configured']})
            configured.start(); self.addCleanup(configured.stop)
    def tearDown(self): base_tests.CodingWorkspaceTests.tearDown(self)
    prepare = base_tests.CodingWorkspaceTests.prepare

    def fixture(self, text=GOOD):
        relative = 'mods/demo/Scripts/subject.lua'
        path = self.root / relative; path.parent.mkdir(parents=True); path.write_bytes(text.encode('utf-8'))
        sid, target = self.prepare()
        return sid, target, relative

    def edit(self, sid, target, relative, old, new):
        return {'workspace_id': sid, 'changes': [{'relative_path': relative,
                'expected_sha256': coding.digest((target / relative).read_bytes()),
                'edits': [{'old_text': old, 'new_text': new}]}]}

    def proposals(self, sid):
        folder = coding.base_path(self.root) / sid / 'proposals'
        return sorted(folder.glob('*.json')) if folder.is_dir() else []

    def test_unavailable_parser_never_blocks_and_says_so(self):
        sid, target, relative = self.fixture()
        with patch('sandbox.lua_parse', return_value=None):
            result = coding.propose_edits(self.root, self.edit(sid, target, relative, 'return 1', 'return 1 +'))
        self.assertEqual(result['lua_syntax'], {'checked': False,
            'reason': 'Lua parser sandbox unavailable; run_coding_tests will still preflight syntax'})

    def test_non_lua_proposals_skip_the_parser(self):
        relative = 'mods/demo/notes.txt'; path = self.root / relative; path.parent.mkdir(parents=True); path.write_text('a\n')
        sid, target = self.prepare()
        with patch('sandbox.lua_parse') as parse:
            result = coding.propose_edits(self.root, self.edit(sid, target, relative, 'a', 'b'))
        parse.assert_not_called(); self.assertNotIn('lua_syntax', result)

    @unittest.skipUnless(toolchain(), 'Docker and smelter-cpp:2 required')
    def test_edit_that_breaks_a_parsing_file_is_refused_with_line_and_excerpt(self):
        sid, target, relative = self.fixture()
        before = (target / relative).read_bytes()
        with self.assertRaisesRegex(ValueError, r'(?s)NOT recorded: mods/demo/Scripts/subject\.lua:\d+:.*2: function M\.value'):
            coding.propose_edits(self.root, self.edit(sid, target, relative, 'return 1 end', 'do return 1 end'))
        self.assertEqual(self.proposals(sid), [])
        self.assertEqual((target / relative).read_bytes(), before)
        good = coding.propose_edits(self.root, self.edit(sid, target, relative, 'return 1', 'return 2'))
        self.assertEqual(good['lua_syntax'], {'checked': True, 'remaining_syntax_errors': []})

    @unittest.skipUnless(toolchain(), 'Docker and smelter-cpp:2 required')
    def test_new_broken_file_is_refused_but_an_already_broken_file_can_be_fixed_stepwise(self):
        sid, target, relative = self.fixture('local M = {}\nlocal a = (1\nlocal b = (2\nreturn M\n')
        with self.assertRaisesRegex(ValueError, 'NOT recorded: mods/demo/Scripts/new.lua'):
            coding.propose(self.root, {'workspace_id': sid, 'changes': [{'relative_path': 'mods/demo/Scripts/new.lua',
                'expected_sha256': None, 'content': 'x = = 1\n'}]})
        partial = coding.propose_edits(self.root, self.edit(sid, target, relative, 'local a = (1', 'local a = (1)'))
        remaining = partial['lua_syntax']['remaining_syntax_errors']
        self.assertEqual([r['relative_path'] for r in remaining], [relative])
        self.assertIn('at line 3', remaining[0]['error'])
        self.assertIn('3: local b = (2', remaining[0]['excerpt'])


if __name__ == '__main__': unittest.main()
