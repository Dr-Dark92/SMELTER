from pathlib import Path
import io
import stat
import tarfile
import tempfile
import unittest
import zipfile

from install_engine_cli import extract


class EngineInstallerTests(unittest.TestCase):
    def test_zip_preflight_rejects_traversal_links_collisions_and_reserved_names(self):
        bad = [['../escape'],['x','X'],['a','a/b'],['CON.txt'],['link'],['a\\b'],['x\nfile']]
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            for n,names in enumerate(bad):
                archive=base/(str(n)+'.zip');destination=base/('out'+str(n))
                with zipfile.ZipFile(archive,'w') as z:
                    for name in names:
                        info=zipfile.ZipInfo(name)
                        info.filename=name  # ZipInfo normalizes backslashes on Windows during construction.
                        if name=='link':info.external_attr=(stat.S_IFLNK|0o777)<<16
                        z.writestr(info,b'fixture')
                with self.subTest(names=names), self.assertRaises(ValueError):extract(archive,destination)
                self.assertFalse(destination.exists())

    def test_tar_hard_links_refused_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);archive=base/'fixture.tar.xz';destination=base/'out'
            with tarfile.open(archive,'w:xz') as z:
                info=tarfile.TarInfo('release/file');info.size=3;z.addfile(info,io.BytesIO(b'abc'))
                link=tarfile.TarInfo('release/link');link.type=tarfile.LNKTYPE;link.linkname='release/file';z.addfile(link)
            with self.assertRaises(ValueError):extract(archive,destination,'release/')
            self.assertFalse(destination.exists())

    def test_release_prefix_and_existing_output_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);archive=base/'fixture.zip';destination=base/'out'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('release/tool',b'abc')
            with self.assertRaises(ValueError):extract(archive,destination,'other/')
            extract(archive,destination,'release/')
            self.assertEqual((destination/'tool').read_bytes(),b'abc')
            with self.assertRaises(ValueError):extract(archive,destination,'release/')


if __name__=='__main__':unittest.main()
