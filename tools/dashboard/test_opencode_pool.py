"""Persistent OpenCode session: reuse, replacement and detachment (no Docker)."""
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import opencode_pool

RUNTIME = {'context_tokens': 32768, 'max_output_tokens': 1024, 'timeout_seconds': 300,
           'opencode_timeout_seconds': 900, 'thinking': False}


class FakeClient:
    created = []

    def __init__(self, root, policy, configuration, control, allow_inference=False, bridge=None, lifetime=None):
        self.model, self.lifetime, self.allow_inference = configuration['model'], lifetime, allow_inference
        self.closed, self.error, self.name = False, None, 'smelter-opencode-fake%d' % len(FakeClient.created)
        self.control = self.bridge = None
        self.refreshes = 0
        FakeClient.created.append(self)

    def attach(self, control, bridge):
        self.control, self.bridge = control, bridge

    def detach(self):
        self.control = self.bridge = None

    def refresh(self, policy):
        self.refreshes += 1

    def close(self):
        self.closed = True
        return True


class PoolTests(unittest.TestCase):
    def setUp(self):
        FakeClient.created = []
        opencode_pool._state.update(client=None, key=None, status='stopped', error=None, started=None, tasks=0)
        self.root = Path(tempfile.mkdtemp())
        self.policy = SimpleNamespace(revision='r1')

    def config(self, model='qwen3.5:4b'):
        return {'model': model, 'runtime': dict(RUNTIME)}

    def acquire(self, model='qwen3.5:4b', control=None, policy=None):
        return opencode_pool.acquire(self.root, policy or self.policy, self.config(model), control, None, factory=FakeClient)

    def test_session_is_reused_and_refreshed_between_tasks(self):
        control = object()
        first = self.acquire(control=control)
        self.assertIs(first.control, control)
        self.assertTrue(first.allow_inference)
        self.assertEqual(first.lifetime, opencode_pool.LIFETIME)
        self.assertEqual(opencode_pool.status()['status'], 'busy')
        self.assertTrue(opencode_pool.release(first))
        self.assertIsNone(first.control)  # nothing is bound between tasks
        self.assertEqual(opencode_pool.status()['status'], 'ready')
        second = self.acquire()
        self.assertIs(second, first)
        self.assertEqual(first.refreshes, 1)
        self.assertEqual(len(FakeClient.created), 1)

    def test_model_or_policy_change_replaces_the_container(self):
        first = self.acquire();opencode_pool.release(first)
        second = self.acquire(model='qwen3.5:9b')
        self.assertIsNot(second, first)
        self.assertTrue(first.closed)
        opencode_pool.release(second)
        third = self.acquire(model='qwen3.5:9b', policy=SimpleNamespace(revision='r2'))
        self.assertIsNot(third, second)

    def test_unhealthy_release_or_relay_error_discards(self):
        first = self.acquire()
        self.assertTrue(opencode_pool.release(first, healthy=False))
        self.assertTrue(first.closed)
        self.assertEqual(opencode_pool.status()['status'], 'stopped')
        second = self.acquire();opencode_pool.release(second)
        second.error = 'Confined model relay failed'
        third = self.acquire()
        self.assertIsNot(third, second)
        self.assertTrue(second.closed)

    def test_failed_replacement_cleanup_retains_owner_and_blocks_new_client(self):
        first=self.acquire();opencode_pool.release(first)
        first.close=lambda:False
        with self.assertRaisesRegex(ValueError,'cleanup is pending'):
            self.acquire(model='qwen3.5:9b')
        self.assertIs(opencode_pool._state['client'],first)
        self.assertEqual(len(FakeClient.created),1)
        self.assertEqual(opencode_pool.status()['status'],'failed')
        first.close=lambda:True
        second=self.acquire(model='qwen3.5:9b')
        self.assertIsNot(first,second)

    def test_unhealthy_release_closes_with_bridge_still_attached(self):
        client=self.acquire(control=object());bridge=object();client.bridge=bridge
        observed=[]
        def close():
            observed.append(client.bridge);client.closed=True;return True
        client.close=close
        self.assertTrue(opencode_pool.release(client,healthy=False))
        self.assertEqual(observed,[bridge])

    def test_failed_quiescence_discards_instead_of_reusing_client(self):
        client=self.acquire();client.detach=lambda:False
        self.assertTrue(opencode_pool.release(client))
        self.assertTrue(client.closed)
        self.assertEqual(opencode_pool.status()['status'],'stopped')

    def test_failed_start_is_reported(self):
        def broken(*args, **kwargs):
            raise ValueError('Confined OpenCode unavailable: no image')
        with self.assertRaisesRegex(ValueError, 'no image'):
            opencode_pool.acquire(self.root, self.policy, self.config(), None, None, factory=broken)
        self.assertEqual(opencode_pool.status()['status'], 'failed')
        self.assertIn('no image', opencode_pool.status()['error'])

    def test_stop_refuses_while_busy_then_removes(self):
        client = self.acquire()
        with self.assertRaisesRegex(ValueError, 'task is running'):
            opencode_pool.stop()
        opencode_pool.release(client)
        self.assertEqual(opencode_pool.stop()['status'], 'stopped')
        self.assertTrue(client.closed)

    def test_dashboard_exit_forces_removal_even_while_busy(self):
        client = self.acquire()
        self.assertEqual(opencode_pool.stop(force=True)['status'], 'stopped')
        self.assertTrue(client.closed)

    def test_a_busy_session_cannot_be_shared(self):
        first = self.acquire(control='task-1')
        with self.assertRaisesRegex(ValueError, 'already using'):
            self.acquire(control='task-2')
        self.assertEqual(first.control, 'task-1')

    def test_background_start_warms_without_binding_a_task(self):
        from database import select_database
        select_database(self.root, str(self.root.parent / (self.root.name + '-data')))
        opencode_pool.start(self.root, factory=FakeClient)
        for _ in range(100):
            if opencode_pool.status()['status'] != 'starting':break
            threading.Event().wait(0.02)
        self.assertEqual(opencode_pool.status()['status'], 'ready')
        self.assertIsNone(FakeClient.created[0].control)
        self.assertEqual(opencode_pool.start(self.root, factory=FakeClient)['status'], 'ready')
        self.assertEqual(len(FakeClient.created), 1)

    def test_background_start_respects_stopped_component(self):
        from database import select_database
        from config_store import save_config
        select_database(self.root, str(self.root.parent / (self.root.name + '-data')))
        save_config(self.root, 'component_controls.json', {'schema_version': 1, 'opencode': False, 'mcp': True})
        with self.assertRaisesRegex(ValueError, 'opencode is stopped'):
            opencode_pool.start(self.root, factory=FakeClient)
        self.assertEqual(FakeClient.created, [])
        self.assertEqual(opencode_pool.status()['status'], 'stopped')

    def test_delayed_warmup_cannot_detach_a_task_that_acquired_first(self):
        with patch('opencode_pool.threading.Thread') as thread:
            report = opencode_pool.start(self.root, factory=FakeClient)
            self.assertEqual(report['status'], 'starting')
            warmup = thread.call_args.kwargs['target']
            client = self.acquire(control='active-task')
            warmup()
        self.assertEqual(opencode_pool.status()['status'], 'busy')
        self.assertEqual(client.control, 'active-task')
        self.assertEqual(len(FakeClient.created), 1)
        self.assertEqual(opencode_pool.status()['tasks'], 1)

    def test_concurrent_acquire_creates_one_container(self):
        results = []
        def worker():
            # Tasks are serialized by the job queue; retry while another holds the session.
            while True:
                try:
                    client = self.acquire();break
                except ValueError:
                    threading.Event().wait(0.005)
            results.append(client);opencode_pool.release(client)
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(len(FakeClient.created), 1)


if __name__ == '__main__':
    unittest.main()
