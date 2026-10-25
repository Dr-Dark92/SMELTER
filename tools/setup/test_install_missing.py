"""install_missing.ps1 completion: truthful exit status and post-run recheck (R07).

The real script probes and installs, so these tests extract its functions with the
PowerShell parser and run them against fixtures. Nothing is installed or probed.
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('install_missing.ps1')
POWERSHELL = shutil.which('powershell') or shutil.which('pwsh')

LOADER = r'''
$ErrorActionPreference = 'Stop'
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile('%s', [ref]$null, [ref]$errors)
if ($errors.Count) { throw 'parse errors' }
foreach ($f in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)) {
    if ($f.Name -in 'Get-InstallOutcome', 'Complete-Install') { . ([scriptblock]::Create($f.Extent.Text)) }
}
function Write-Host { }
'''


@unittest.skipUnless(POWERSHELL, 'PowerShell is required')
class InstallCompletionTests(unittest.TestCase):
    def run_ps(self, body):
        with tempfile.TemporaryDirectory() as folder:
            harness = Path(folder) / 'harness.ps1'
            harness.write_text(LOADER % str(SCRIPT).replace("'", "''") + body, encoding='utf-8')
            return subprocess.run([POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(harness)],
                                  capture_output=True, text=True, timeout=60)

    def outcome(self, results='@()', tools='@()', setup='@()', planned=False):
        done = self.run_ps('Get-InstallOutcome %s %s %s%s | ConvertTo-Json -Compress' % (results, tools, setup, ' -Planned' if planned else ''))
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    ready_tool = "@([pscustomobject]@{Tool='node'; Status='installed'; Ready=$true})"
    missing_tool = "@([pscustomobject]@{Tool='docker'; Status='missing'; Ready=$false})"
    done_step = "@([pscustomobject]@{Step='mcp_sdk'; State='done'; Detail=''})"
    blocked_step = "@([pscustomobject]@{Step='image_opencode'; State='blocked'; Detail='Docker engine is not running'})"

    def test_complete_profile_exits_zero(self):
        result = self.outcome("@([pscustomobject]@{Item='mcp_sdk'; Result='done'})", self.ready_tool, self.done_step)
        self.assertEqual((result['Outcome'], result['ExitCode']), ('complete', 0))

    def test_blocked_required_step_without_failures_is_incomplete_not_success(self):
        result = self.outcome('@()', self.ready_tool, self.blocked_step)
        self.assertEqual((result['Outcome'], result['ExitCode']), ('incomplete', 2))
        self.assertEqual(result['Blocked'], ['image_opencode (blocked)'])

    def test_missing_tool_or_unrun_step_after_recheck_is_incomplete(self):
        self.assertEqual(self.outcome('@()', self.missing_tool, self.done_step)['ExitCode'], 2)
        todo = "@([pscustomobject]@{Step='ollama_model'; State='todo'; Detail=''})"
        self.assertEqual(self.outcome('@()', self.ready_tool, todo)['ExitCode'], 2)

    def test_skipped_action_is_incomplete(self):
        skipped = "@([pscustomobject]@{Item='opencode'; Result='skipped: npm not found (install Node.js first)'})"
        result = self.outcome(skipped, self.ready_tool, self.done_step)
        self.assertEqual((result['ExitCode'], result['Skipped']), (2, ['opencode']))

    def test_failed_action_takes_precedence(self):
        failed = "@([pscustomobject]@{Item='image_node'; Result='failed (exit 1)'})"
        result = self.outcome(failed, self.missing_tool, self.blocked_step)
        self.assertEqual((result['Outcome'], result['ExitCode'], result['Failed']), ('failed', 1, ['image_node']))

    def test_dry_run_stays_informational_but_reports_blocked(self):
        result = self.outcome('@()', self.missing_tool, self.blocked_step, planned=True)
        self.assertEqual((result['Outcome'], result['ExitCode']), ('planned', 0))
        self.assertEqual(result['Missing'], ['docker'])

    def test_completion_exits_with_code_and_writes_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            summary = Path(folder) / 'summary.json'
            done = self.run_ps(r'''
$SummaryPath = '%s'; $DryRun = $false; $ProfileName = @('qwen35b_agent'); $Only = $null
function Get-ToolReport { return ,%s }
function Get-SetupReport { throw 'Recheck must reuse the supplied report' }
Complete-Install @() %s
''' % (str(summary).replace("'", "''"), self.ready_tool, self.blocked_step))
            self.assertEqual(done.returncode, 2, done.stderr)
            data = json.loads(summary.read_text(encoding='utf-8-sig'))
        self.assertEqual((data['outcome'], data['exit_code'], data['dry_run']), ('incomplete', 2, False))
        self.assertEqual(data['profiles'], ['qwen35b_agent'])
        self.assertEqual(data['setup'][0]['state'], 'blocked')

    def test_completion_after_actions_probes_again(self):
        done = self.run_ps(r'''
$SummaryPath = $null; $DryRun = $false
function Get-ToolReport { return ,%s }
function Get-SetupReport { return ,%s }
Complete-Install @([pscustomobject]@{Item='mcp_sdk'; Result='done'})
''' % (self.ready_tool, self.done_step))
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_every_exit_after_planning_goes_through_completion(self):
        text = SCRIPT.read_text(encoding='utf-8-sig')
        tail = text[text.index('# ---- Plan'):]
        # Only the cancellation path exits directly; success can no longer bypass the recheck.
        statement = re.compile(r'(^|[;{])\s*exit\b')
        exits = [line.strip() for line in tail.splitlines()
                 if statement.search(line.strip()) and not line.strip().startswith('#') and 'ExitCode' not in line]
        self.assertEqual(exits, ["if ($answer -ne 'yes') { Write-Host 'Cancelled. Nothing was changed.'; exit 1 }"])
        self.assertIn('Complete-Install $results', text)


if __name__ == '__main__':
    unittest.main()
