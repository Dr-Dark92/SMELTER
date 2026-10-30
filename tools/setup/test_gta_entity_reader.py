"""Operator-reviewed C# reader against fake SDK types; never loads RPH or a game."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import build_managed_mod as managed

ROOT=Path(__file__).resolve().parents[2]
SUBJECTS=['mods/gta-ark/common/managed/EntityRegistry.cs',
          'mods/gta-ark/common/managed/EntitySnapshot.cs','mods/gta-ark/gta/rph/GtaEntityReader.cs']
FIXTURE='tools/setup/fixtures/GtaEntityReaderFixture.cs'


def exercise(target,reviewed_hashes):
    target=Path(target)
    snapshots={p:(target/p).read_bytes() for p in SUBJECTS}
    hashes={p:hashlib.sha256(raw).hexdigest() for p,raw in snapshots.items()}
    if hashes!=reviewed_hashes or any(len(raw)>131072 for raw in snapshots.values()):
        raise ValueError('Exact reviewed source hashes required')
    with tempfile.TemporaryDirectory(prefix='smelter-reader-fixture-') as temporary:
        folder=Path(temporary);sources=[]
        for relative,raw in snapshots.items():
            path=folder/Path(relative).name;path.write_bytes(raw);sources.append(path)
        fixture=ROOT/FIXTURE;(folder/fixture.name).write_bytes(fixture.read_bytes());sources.append(folder/fixture.name)
        compiler,refs,release=managed.compiler();output=folder/'ReaderFixture.exe'
        args=[str(compiler),*[f for f in managed.FLAGS if f!='/target:library'],'/target:exe','/out:'+str(output),
              *['/reference:'+str(p) for p in refs],*map(str,sources)]
        options={'cwd':folder,'capture_output':True,'creationflags':subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0}
        built=subprocess.run(args,timeout=30,**options)
        if built.returncode:raise AssertionError((built.stdout+built.stderr).decode(errors='replace'))
        ran=subprocess.run([str(output)],timeout=10,**options)
        log=(ran.stdout+ran.stderr).decode(errors='replace')
        summaries=[line for line in log.splitlines() if line.startswith('READER_RESULT|')]
        summary=re.fullmatch(r'READER_RESULT\|checks=([1-9][0-9]*);failures=0',summaries[0]) if len(summaries)==1 else None
        passed=sum(line.startswith('[READER PASS] ') for line in log.splitlines())
        if ran.returncode or summary is None or int(summary.group(1))!=passed:raise AssertionError(log)
        if any((target/p).read_bytes()!=raw for p,raw in snapshots.items()):raise ValueError('Source changed during fixture')
        return {'stage':'GREEN','checks':passed,'source_sha256':hashes,'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'output':log,
                'log_sha256':hashlib.sha256(log.encode()).hexdigest(),'framework_release':release,
                'scope':'fake SDK C# reader fixture only','game_runtime_verified':False,'rph_loaded':False}


class NativeReaderTests(unittest.TestCase):
    def test_unreviewed_source_never_invokes_compiler(self):
        with tempfile.TemporaryDirectory(prefix='smelter-reader-review-') as temporary:
            root=Path(temporary)
            for relative in SUBJECTS:
                path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('unreviewed')
            with patch.object(managed,'compiler') as compiler,self.assertRaisesRegex(ValueError,'reviewed source'):
                exercise(root,{p:'0'*64 for p in SUBJECTS})
            compiler.assert_not_called()

    @unittest.skipUnless(os.name=='nt' and all((ROOT/p).is_file() for p in SUBJECTS),'Promoted reviewed reader and Windows compiler required')
    def test_promoted_reader_with_fake_sdk(self):
        self.assertEqual(exercise(ROOT,{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SUBJECTS})['stage'],'GREEN')


if __name__=='__main__':unittest.main()
