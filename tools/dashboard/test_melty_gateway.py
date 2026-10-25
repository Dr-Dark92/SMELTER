import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import melty_connection as melty


class MeltyGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.env=patch.dict(os.environ,{'SMELTER_MELTY_TOKEN':'fixture-private-token'})
        self.env.start();self.addCleanup(self.env.stop)

    def test_status_does_not_connect_or_disclose_host_secret(self):
        with patch.object(melty,'_exchange') as remote:
            result=melty.status(self.root)
        self.assertEqual(result['status'],'configured')
        self.assertFalse(result['connected']);remote.assert_not_called()
        self.assertNotIn('fixture-private-token',json.dumps(result))

    def test_grant_and_allowlist_fail_before_remote_connection(self):
        with patch.object(melty,'exchange') as remote:
            for grants,name,args in [({},'melty_whoami',{}),({'melty_read':True},'publish',{}),
                                     ({'melty_read':True},'melty_search_games',{'query':'x','token':'x'}),
                                     ({'melty_read':True},'melty_search_games',{'query':'bad\nquery'})]:
                with self.subTest(name=name),self.assertRaises(ValueError):melty.run_melty(self.root,grants,name,args)
        remote.assert_not_called()

    def test_remote_echo_cannot_disclose_host_bearer(self):
        remote=AsyncMock(return_value={'content':[{'text':'Bearer fixture-private-token'}]})
        with patch.object(melty,'_exchange',remote):result=melty.exchange(self.root,'whoami',{})
        self.assertNotIn('fixture-private-token',json.dumps(result))

    def test_private_transport_error_is_not_reflected(self):
        with patch.object(melty,'_exchange',AsyncMock(side_effect=ValueError('fixture-private-token'))):
            with self.assertRaises(ValueError) as error:melty.exchange(self.root,'whoami',{})
        self.assertNotIn('fixture-private-token',str(error.exception))

    def test_lookup_maps_only_fixed_read_tool_and_returns_service_errors(self):
        with patch.object(melty,'exchange',return_value={'isError':True,'content':[]}) as remote:
            result=melty.run_melty(self.root,{'melty_read':True},'melty_search_games',{'query':'skyrim'})
        remote.assert_called_once_with(self.root,'search_games',{'query':'skyrim'})
        self.assertEqual(result['status'],'mcp_failed')

    def test_existing_signin_requires_explicit_reference_and_exact_endpoint(self):
        config=self.root/'.smelter/melty-connection.json';config.parent.mkdir()
        config.write_text(json.dumps({'schema_version':1,'credential_source':'existing-codex-melty'}))
        source=self.root/'.codex/config.toml';source.parent.mkdir()
        source.write_text('[mcp_servers.melty]\nurl="https://attacker.invalid/mcp"\n[mcp_servers.melty.http_headers]\nAuthorization="Bearer fixture"\n')
        with patch.dict(os.environ,{'SMELTER_MELTY_TOKEN':''}),patch.object(Path,'home',return_value=self.root):
            with self.assertRaisesRegex(ValueError,'endpoint'):melty._authorization(self.root)
        self.assertNotIn('fixture-private-token',config.read_text())
