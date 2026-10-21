"""Offline lifecycle and shared-catalog regressions. No model or Docker calls."""
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from chat_jobs import Jobs,Control
from chats import create_chat,read_chat
from database import select_database,chosen_database
from execution_store import finalize
from job_store import admit,read,list_jobs
from skills_catalog import catalog_skills
from skill_manager import set_skill_enabled
from skill_runtime import initialize

MANIFEST='# Fixture\n\n## Purpose\nInspect synthetic data.\n'


class OfficeRepairs(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.base=Path(temp.name);self.root=self.base/'SMELTER';self.root.mkdir()
        select_database(self.root,str(self.base/'data'));self.cid=create_chat(self.root,'Office fixture')['id']

    def manifest(self,relative):
        folder=self.root/relative;folder.mkdir(parents=True);(folder/'SKILL.md').write_text(MANIFEST);return folder

    def test_namespaced_same_basename_skills_are_all_visible(self):
        for relative in ('skills/fixture','.agents/skills/fixture','agents/skills/fixture'):self.manifest(relative)
        skills={s['id']:s for s in catalog_skills(self.root)['skills']}
        self.assertEqual(set(skills),{'fixture','legacy/fixture','contract/fixture'})
        self.assertFalse(skills['legacy/fixture']['enabled']);self.assertFalse(skills['contract/fixture']['enabled'])
        set_skill_enabled(self.root,'legacy/fixture',True,True)
        monitor=initialize(self.root)
        self.assertEqual(next(s for s in monitor.status()['skills'] if s['id']=='legacy/fixture')['activation'],'enabled')

    def test_real_identity_collision_is_disabled_and_explained(self):
        self.manifest('skills/fixture');self.manifest('.smelter/managed-skills/fixture')
        skill=catalog_skills(self.root)['skills'][0]
        self.assertEqual(skill['status'],'identity_conflict');self.assertFalse(skill['enabled'])
        self.assertEqual(skill['conflicting_sources'],['bundled','managed'])
        with self.assertRaisesRegex(ValueError,'not ready'):set_skill_enabled(self.root,'fixture',True,True)

    def test_linked_collection_ancestor_is_never_discovered(self):
        external=self.base/'external';external.mkdir();(external/'fixture').mkdir();(external/'fixture/SKILL.md').write_text(MANIFEST)
        parent=self.root/'.smelter/managed-skills/collections';parent.mkdir(parents=True)
        try:(parent/'external').symlink_to(external,target_is_directory=True)
        except OSError:self.skipTest('Symlink privilege unavailable')
        self.assertEqual(catalog_skills(self.root)['count'],0)

    def test_atomic_finalization_is_durable_before_worker_returns(self):
        jobs=Jobs();committed=threading.Event();release=threading.Event()
        def worker(*args,control,**kwargs):
            result=finalize(self.root,self.cid,'fixture','saved answer',{'engine':'fixture'},control=control)
            committed.set();release.wait(3);return result
        try:
            job=jobs.start(self.root,{'id':self.cid,'content':'fixture'},worker)
            self.assertTrue(committed.wait(2))
            record=Jobs().status(job['id'],root=self.root)
            self.assertEqual(record['state'],'done')
            messages=read_chat(self.root,self.cid)['messages'];self.assertEqual(len(messages),2)
            self.assertEqual(messages[-1]['execution']['job_id'],job['id'])
            with patch('job_store.alive',return_value=False):
                self.assertEqual(read(self.root,job['id'])['state'],'done')
        finally:release.set()
        self.wait_finished(jobs,job['id'])

    def test_late_worker_failure_cannot_relabel_committed_success(self):
        jobs=Jobs()
        def worker(*args,control,**kwargs):
            finalize(self.root,self.cid,'fixture','saved answer',{},control=control)
            raise RuntimeError('fixture post-commit failure')
        job=jobs.start(self.root,{'id':self.cid,'content':'fixture'},worker)
        self.wait_finished(jobs,job['id'])
        self.assertEqual(jobs.status(job['id'])['state'],'done')
        self.assertEqual(read(self.root,job['id'])['state'],'done')
        self.assertEqual(read_chat(self.root,self.cid)['messages'][-1]['execution']['outcome'],'completed')

    def test_failed_atomic_job_update_rolls_back_transcript_too(self):
        control=Control();control.job_id='fixture';control.admitted_at=time.monotonic()
        admit(self.root,{'id':'fixture','conversation_id':self.cid,'engine':'fixture','state':'running'})
        with patch('job_store.finalize_in_transaction',side_effect=sqlite3.OperationalError('fixture storage full')):
            with self.assertRaises(sqlite3.Error):finalize(self.root,self.cid,'fixture','must roll back',{},control=control)
        self.assertEqual(read_chat(self.root,self.cid)['messages'],[])
        self.assertEqual(read(self.root,'fixture')['state'],'running')
        self.assertFalse(control.completed);self.assertFalse(control.journal_committed)

    def test_failed_journal_retry_never_reexecutes_worker(self):
        jobs=Jobs();actions=[];failed=threading.Event()
        import job_store
        real_save=job_store.save
        def save(root,payload,**kwargs):
            if kwargs.get('admitting'):return real_save(root,payload,**kwargs)
            failed.set();raise sqlite3.OperationalError('fixture storage full')
        def worker(*args,**kwargs):actions.append('once');return {'status':'completed'}
        with patch('job_store.save',side_effect=save):
            job=jobs.start(self.root,{'id':self.cid,'content':'fixture'},worker)
            self.assertTrue(failed.wait(2));status=jobs.status(job['id'])
            self.assertEqual(status['state'],'done');self.assertTrue(status['persistence_pending'])
            self.assertIsNone(status['error']);self.assertIn('not saved',status['persistence_error'])
            self.assertEqual(read(self.root,job['id'])['state'],'running')
        status=jobs.status(job['id']);self.assertFalse(status['persistence_pending'])
        self.assertEqual(read(self.root,job['id'])['state'],'done');self.assertEqual(actions,['once'])

    def test_worker_start_failure_has_terminal_record_and_no_action(self):
        jobs=Jobs();actions=[]
        with patch('chat_jobs.threading.Thread.start',side_effect=RuntimeError('fixture unavailable')):
            with self.assertRaisesRegex(ValueError,'no action'):jobs.start(self.root,{'id':self.cid,'content':'fixture'},lambda *a,**kw:actions.append(True))
        self.assertEqual(actions,[]);records=list_jobs(self.root)
        self.assertEqual(records[0]['state'],'error');self.assertIn('could not start',records[0]['error'])

    def wait_finished(self,jobs,jid):
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            if jobs.status(jid)['state']!='running':return
            time.sleep(.01)
        self.fail('Fixture worker did not finish')


if __name__=='__main__':unittest.main()
