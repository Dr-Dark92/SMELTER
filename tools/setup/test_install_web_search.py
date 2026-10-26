import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from install_web_search import install,ROOT


class WebSearchInstallerTests(unittest.TestCase):
    def test_installed_provider_is_declared_with_an_immutable_image_and_revision(self):
        catalog=json.loads((ROOT/'system-requirements.json').read_text());step=catalog['setup']['web_search']
        lock=json.loads((ROOT/step['requirements']).read_text())
        self.assertRegex(lock['image'],r'@sha256:[a-f0-9]{64}$');self.assertEqual(lock['version'],step['version'])
        self.assertRegex(lock['revision'],r'^[a-f0-9]{40}$');self.assertEqual(lock['bind'],'127.0.0.1:8842')

    def test_foreign_container_is_preserved_and_no_start_or_remove_is_attempted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'tools/modding';p.mkdir(parents=True)
            (p/'requirements-web.json').write_bytes((ROOT/'tools/modding/requirements-web.json').read_bytes())
            commands=[]
            def process(args,**kwargs):
                commands.append(args)
                if args[1:3]==['context','inspect']:out='npipe:////./pipe/docker_engine'
                elif args[1:3]==['image','inspect']:out='sha256:'+'a'*64
                elif args[1:3]==['container','inspect']:out=json.dumps([{'Image':'sha256:'+'a'*64,'Config':{'Labels':{'someone':'else'}},'State':{'Running':True}}])
                else:raise AssertionError('Unexpected mutation: '+str(args))
                return subprocess.CompletedProcess(args,0,out,'')
            with patch('install_web_search.shutil.which',return_value='docker'),patch('process_runner.run',side_effect=process):
                with self.assertRaisesRegex(ValueError,'different owner'):install(root,start=True)
            self.assertFalse(any(args[1] in ('run','rm','stop','kill') for args in commands))


if __name__=='__main__':unittest.main()
