import hashlib
from pathlib import Path
import tempfile
import unittest

from directory_files import read,MAX_BYTES
from access_policy import Policy,using


class DirectoryFileTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.grants={'inventory_root':str(self.root)}

    def test_text_pages_and_hash_identify_exact_bytes(self):
        raw='hello résumé'.encode();(self.root/'note.md').write_bytes(raw)
        result=read(self.grants,{'relative_path':'note.md','offset':6,'limit':3})
        self.assertEqual(result['text'],'rés');self.assertEqual(result['next_offset'],9)
        self.assertEqual(result['sha256'],hashlib.sha256(raw).hexdigest())

    def test_scope_traversal_absolute_paths_and_mounts_are_rejected(self):
        for path in ('../outside','/outside','C:/outside','a\\b','a/../b','a//b'):
            with self.subTest(path=path),self.assertRaises(ValueError):read(self.grants,{'relative_path':path})
        with self.assertRaises(ValueError):read({}, {'relative_path':'x'})

    def test_binary_secret_and_oversize_files_are_not_read(self):
        for name,raw in [('file.bin',b'x\x00x'),('credentials.json',b'private'),('.env.local',b'private'),('x.txt',b'a'*(MAX_BYTES+1))]:
            (self.root/name).write_bytes(raw)
            with self.subTest(name=name),self.assertRaises(ValueError):read(self.grants,{'relative_path':name})

    def test_application_policy_is_enforced_for_the_exact_file(self):
        (self.root/'denied.txt').write_text('private')
        policy=Policy({'schema_version':1,'locations':[{'id':'test','name':'test','path':str(self.root),'enabled':True,
            'read':True,'write':False,'execute':False,'operations':[],'exclusions':['denied.txt']}]})
        with using(policy),self.assertRaises(ValueError):read(self.grants,{'relative_path':'denied.txt'})

    def test_invalid_pagination_and_arbitrary_arguments_are_rejected(self):
        for extra in ({'offset':True},{'limit':16001},{'limit':0},{'command':'cmd'}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):read(self.grants,{'relative_path':'x',**extra})


if __name__=='__main__':unittest.main()
