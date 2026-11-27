"""Exercise public entrypoints with real Git and agent-rollback in isolated homes."""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import subprocess
import tempfile
import termios
import time
import unittest

REPO = Path(__file__).resolve().parents[1]


class EnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prefix = os.environ.get('CODING_AGENTS_TEST_ARB_PREFIX', '/tmp/coding-agents-test-deps')
        cls.arb_package = Path(prefix) / 'node_modules/agent-rollback'
        if not cls.arb_package.is_dir():
            raise RuntimeError('Install agent-rollback@1.1.1 into CODING_AGENTS_TEST_ARB_PREFIX; see README development instructions')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='coding agents test ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.user = self.root / 'user'
        self.system = self.root / 'system'
        self.system.mkdir()
        self.mock = self.root / 'mock'
        self.mock.mkdir()
        self.env = dict(os.environ)
        self.env.pop('CODEX_HOME', None)
        self.env.pop('CODING_AGENTS_FEATURE_VERSION', None)
        self.env.update(CODING_AGENTS_USER_DIR=str(self.user), CODING_AGENTS_SYSTEM_DIR=str(self.system),
                        PATH=str(self.mock) + os.pathsep + os.environ['PATH'],
                        ARB_TEST_PACKAGE=str(self.arb_package), ARB_TEST_LOG=str(self.root / 'npm-calls'))
        self.script = REPO / 'bin/coding-agents'
        self.create_mock_npm()
        self.workspace = self.root / 'workspace'
        self.call(['git', 'init', '-q', self.workspace])
        (self.workspace / 'file.txt').write_text('initial\n')
        (self.workspace / 'subdir').mkdir()

    def create_mock_npm(self):
        mock = self.mock / 'npm'
        mock.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['ARB_TEST_LOG'], 'a') as stream: stream.write(json.dumps(args) + '\\n')
if args[0] == 'view':
    if os.environ.get('ARB_TEST_OFFLINE'): sys.exit(1)
    print('"9.8.7"')
    sys.exit(0)
assert args[0] == 'install', args
prefix = pathlib.Path(args[args.index('--prefix') + 1])
modules = prefix / 'node_modules'
(modules / '.bin').mkdir(parents=True, exist_ok=True)
if args[-1].startswith('agent-rollback@'):
    package = pathlib.Path(os.environ['ARB_TEST_PACKAGE'])
    (modules / 'agent-rollback').symlink_to(package)
    for name in ['arb', 'agent-rollback']:
        (modules / '.bin' / name).symlink_to(package / 'bin' / (name + '.js'))
else:
    assert args[-1] == '@openai/codex@9.8.7', args
    package = modules / '@openai/codex'
    package.mkdir(parents=True, exist_ok=True)
    (package / 'package.json').write_text(json.dumps({'version': '9.8.7'}))
    (package / 'codex.js').write_text('console.log("codex-cli 9.8.7");')
    (modules / '.bin/codex').symlink_to(package / 'codex.js')
''')
        mock.chmod(0o755)

    def call(self, args, cwd=None, ok=True, **kwargs):
        result = subprocess.run([str(a) for a in args], cwd=cwd or self.root, env=self.env,
                                text=True, capture_output=True, timeout=45, **kwargs)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stderr)
        return result

    def sync(self, *args, cwd=None, ok=True):
        return self.call([self.script, 'sync', '--no-update', *args], cwd=cwd, ok=ok)

    def checkpoints(self, root=None):
        output = self.call([self.user / '.local/bin/arb', '--cwd', root or self.workspace, 'list', '--json'])
        return json.loads(output.stdout)['checkpoints']

    def test_initial_setup_rerun_and_repair(self):
        result = self.sync('--automatic', '--workspace', self.workspace / 'subdir')
        self.assertIn('PAT', result.stderr)
        self.assertTrue((self.system / 'hooks.json').is_symlink())
        self.assertEqual((self.user / '.codex/AGENTS.md').resolve(), REPO / 'codex/AGENTS.md')
        self.assertFalse((self.workspace / 'subdir/.agent-rollback').exists())
        self.assertEqual(len(self.checkpoints()), 1)
        self.call(['git', 'check-ignore', '.agent-rollback/checkpoints'], cwd=self.workspace)
        self.assertFalse((self.workspace / '.gitignore').exists())
        self.sync('--automatic', '--workspace', self.workspace)
        self.assertEqual(len(self.checkpoints()), 1)
        self.assertEqual((self.user / '.bashrc').read_text().count('# BEGIN coding-agents'), 1)
        self.assertEqual((self.workspace / '.git/info/exclude').read_text().count('/.agent-rollback/'), 1)
        calls = (self.root / 'npm-calls').read_text().splitlines()
        self.assertEqual(sum(json.loads(c)[0] == 'install' for c in calls), 2)
        (self.system / 'hooks.json').unlink()
        (self.user / '.local/bin/arb').unlink()
        (self.workspace / '.git/info/exclude').write_text('keep-this-pattern\n')
        # Run from outside the workspace: registered repositories still get repaired.
        self.sync()
        self.assertTrue((self.system / 'hooks.json').is_symlink())
        self.assertIn('keep-this-pattern', (self.workspace / '.git/info/exclude').read_text())
        self.assertEqual(len(self.checkpoints()), 1)

    def test_ide_hook_without_bash_and_real_restore(self):
        self.local_source()
        self.sync('--automatic')
        hook = self.system / 'rollback-hook'
        event = {'hook_event_name': 'SessionStart', 'cwd': str(self.workspace / 'subdir')}
        result = self.call([hook], input=json.dumps(event))
        self.assertEqual(result.stdout, '')
        initial = self.checkpoints()[0]['id']
        (self.workspace / 'file.txt').write_text('changed\n')
        event['hook_event_name'] = 'PostToolUse'
        self.call([hook], input=json.dumps(event))
        self.assertGreaterEqual(len(self.checkpoints()), 2)
        self.assertFalse((self.workspace / 'subdir/.agent-rollback').exists())
        self.call([self.user / '.local/bin/arb', '--cwd', self.workspace, 'revert', initial, '--yes'])
        self.assertEqual((self.workspace / 'file.txt').read_text(), 'initial\n')
        outside = self.root / 'not-git'
        outside.mkdir()
        event['cwd'] = str(outside)
        self.call([hook], input=json.dumps(event))
        self.assertFalse((outside / '.agent-rollback').exists())

    def test_old_setup_migration_preserves_other_settings_and_pat(self):
        codex = self.user / '.codex'
        codex.mkdir(parents=True)
        (codex / 'AGENTS.md').symlink_to(REPO / 'AGENTS.md')
        self.sync('--workspace', self.workspace)
        self.call([self.user / '.local/bin/arb', '--cwd', self.workspace, 'init', 'codex'])
        hooks = self.workspace / '.codex/hooks.json'
        config = json.loads(hooks.read_text())
        config['hooks']['PreToolUse'].append({'hooks': [{'type': 'command', 'command': 'echo keep-me'}]})
        hooks.write_text(json.dumps(config))
        local = codex / 'config.toml'
        local.write_text('[mcp_servers.agent-rollback]\ncommand = "arb"\nargs = ["mcp"]\n\n[projects."/example"]\ntrust_level = "trusted"\n')
        pat = codex / 'secrets/github-pat'
        pat.parent.mkdir()
        pat.write_text('test_secret_must_not_appear\n')
        result = self.sync('--workspace', self.workspace)
        self.assertNotIn('test_secret_must_not_appear', result.stdout + result.stderr)
        self.assertIn('keep-me', hooks.read_text())
        self.assertNotIn('agent-rollback.js', hooks.read_text())
        self.assertNotIn('mcp_servers.agent-rollback', local.read_text())
        self.assertIn('trust_level', local.read_text())
        self.assertEqual(pat.read_text(), 'test_secret_must_not_appear\n')
        self.assertTrue(list(codex.glob('config.toml.before-coding-agents-*')))

    def test_mcp_stdio_uses_the_repository_root_from_subdirectory(self):
        self.sync('--workspace', self.workspace)
        server = subprocess.Popen([str(self.system / 'agent-rollback-mcp')],
                                  cwd=self.workspace / 'subdir', env=self.env,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def request(identifier, method, params):
            server.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': identifier, 'method': method, 'params': params}) + '\n')
            server.stdin.flush()
            self.assertTrue(select.select([server.stdout], [], [], 10)[0], 'MCP response timed out')
            response = json.loads(server.stdout.readline())
            self.assertEqual(response['id'], identifier)
            self.assertNotIn('error', response)
            return response['result']
        try:
            request(1, 'initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}})
            server.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
            server.stdin.flush()
            tools = request(2, 'tools/list', {})['tools']
            self.assertIn('create_checkpoint', [tool['name'] for tool in tools])
            result = request(3, 'tools/call', {'name': 'list_checkpoints', 'arguments': {}})
            data = json.loads(result['content'][0]['text'])
            self.assertEqual(len(data['checkpoints']), 1)
            self.assertEqual(data['checkpoints'][0]['metadata']['label'], 'before-agent-work')
        finally:
            server.terminate()
            server.communicate(timeout=5)
        self.assertFalse((self.workspace / 'subdir/.agent-rollback').exists())

    def test_worktree_and_tracked_store(self):
        self.call(['git', 'add', 'file.txt'], cwd=self.workspace)
        self.call(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture'], cwd=self.workspace)
        worktree = self.root / 'worktree'
        self.call(['git', 'worktree', 'add', '-qb', 'test-worktree', worktree], cwd=self.workspace)
        self.sync('--workspace', worktree)
        self.assertEqual(len(self.checkpoints(worktree)), 1)
        self.call(['git', 'check-ignore', '.agent-rollback/file'], cwd=worktree)
        tracked = self.workspace / '.agent-rollback/file'
        tracked.parent.mkdir(exist_ok=True)
        tracked.write_text('tracked data')
        self.call(['git', 'add', '-f', '.agent-rollback/file'], cwd=self.workspace)
        result = self.sync('--workspace', self.workspace, ok=False)
        self.assertIn('contains tracked files', result.stderr)
        self.assertEqual(tracked.read_text(), 'tracked data')

    def test_failed_update_keeps_tools_and_repairs_configuration(self):
        self.local_source()
        self.sync('--workspace', self.workspace)
        (self.system / 'config.toml').unlink()
        self.env['ARB_TEST_OFFLINE'] = '1'
        result = self.call([self.script, 'sync'], ok=False)
        self.assertIn('導入済み', result.stderr)
        self.assertTrue((self.system / 'config.toml').is_symlink())
        self.assertEqual(len(self.checkpoints()), 1)
        status = json.loads((self.user / '.local/state/coding-agents/status.json').read_text())
        self.assertTrue(status['problems'])
        # Automatic invocation reports the error without blocking the shell/IDE.
        result = self.call([self.script, 'sync', '--automatic'])
        self.assertIn('反映は未完了', result.stderr)

    def test_noninteractive_pat_replacement_fails_without_exposure(self):
        self.sync('--automatic')
        self.sync('--github-pat', ok=False)
        self.assertFalse((self.user / '.codex/secrets/github-pat').exists())

    def tty_sync(self, token, success=True):
        master, slave = pty.openpty()
        def terminal():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
        process = subprocess.Popen([str(self.script), 'sync', '--no-update', '--github-pat'],
                                   env=self.env, cwd=self.root, stdin=slave, stdout=slave, stderr=slave,
                                   preexec_fn=terminal)
        os.close(slave)
        output = b''
        sent = False
        try:
            until = time.monotonic() + 30
            while time.monotonic() < until:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output += chunk
                    if b'GitHub PAT (input hidden):' in output and not sent:
                        os.write(master, token.encode() + b'\n')
                        sent = True
                if process.poll() is not None:
                    break
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
        self.assertTrue(sent, output.decode())
        self.assertNotIn(token.encode(), output)
        self.assertEqual(process.returncode == 0, success, output.decode())

    def test_pat_hidden_input_renewal_and_preservation(self):
        self.sync('--automatic')
        self.tty_sync('test_token_one')
        pat = self.user / '.codex/secrets/github-pat'
        self.assertEqual(pat.read_text(), 'test_token_one\n')
        self.assertEqual(pat.stat().st_mode & 0o777, 0o600)
        self.assertEqual(pat.parent.stat().st_mode & 0o777, 0o700)
        self.tty_sync('invalid!token', success=False)
        self.assertEqual(pat.read_text(), 'test_token_one\n')
        self.tty_sync('test_token_two')
        link = self.user / '.config/coding-agents/github-pat'
        link.unlink()
        self.sync('--automatic')
        self.assertEqual(pat.read_text(), 'test_token_two\n')
        self.assertTrue(link.is_symlink())

    def test_foreign_config_is_not_overwritten(self):
        config = self.system / 'config.toml'
        config.write_text('personal settings')
        result = self.sync(ok=False)
        self.assertIn('existing file was preserved', result.stderr)
        self.assertEqual(config.read_text(), 'personal settings')

    def local_source(self):
        publisher = self.root / 'publisher'
        shutil.copytree(REPO, publisher, ignore=shutil.ignore_patterns('.git', 'vendor', '__pycache__'))
        self.call(['git', 'init', '-qb', 'main', publisher])
        self.commit(publisher, 'initial')
        origin = self.root / 'origin.git'
        self.call(['git', 'clone', '--bare', publisher, origin])
        installed = self.user / '.local/share/coding-agents'
        installed.parent.mkdir(parents=True)
        self.call(['git', 'clone', origin, installed])
        self.script = installed / 'bin/coding-agents'
        return publisher, origin, installed

    def commit(self, directory, message):
        self.call(['git', 'add', '.'], cwd=directory)
        self.call(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', message], cwd=directory)

    def test_source_update_uses_updated_engine_and_new_configuration(self):
        publisher, origin, installed = self.local_source()
        self.sync('--workspace', self.workspace)
        source = publisher / 'lib/environment.py'
        source.write_text(source.read_text().replace("status.update(last_apply=time.time(), problems=problems)", "status.update(last_apply=time.time(), problems=problems, updated_engine=True)"))
        config = publisher / 'codex/config.toml'
        config.write_text(config.read_text() + '\n# newly published setting\n')
        self.commit(publisher, 'new environment revision')
        self.call(['git', 'push', origin, 'main'], cwd=publisher)
        self.call([self.script, 'sync'])
        self.assertIn('newly published setting', (self.system / 'config.toml').read_text())
        status = json.loads((self.user / '.local/state/coding-agents/status.json').read_text())
        self.assertTrue(status['updated_engine'])
        self.assertEqual(status['problems'], [])

    def test_devcontainer_and_dotfiles_adapters(self):
        feature = REPO.parent / 'codex-devcontainer-feature/src/codex'
        dotfiles = REPO.parent / 'codex-devcontainer-dotfiles/install-devcontainer.sh'
        if not feature.exists() or not dotfiles.exists():
            self.skipTest('cross-repository adapters are not checked out')
        self.local_source()
        configuration = json.loads((feature / 'devcontainer-feature.json').read_text())
        for name in ('postCreateCommand', 'postStartCommand', 'postAttachCommand'):
            command = configuration[name]
            self.assertEqual(command, '/usr/local/bin/coding-agents sync --automatic --workspace .')
            self.call([feature / 'coding-agents', 'sync', '--automatic', '--workspace', '.'], cwd=self.workspace)
        self.assertEqual(len(self.checkpoints()), 1)

    def test_concurrent_fresh_bootstrap_preserves_workspace_request(self):
        feature = REPO.parent / 'codex-devcontainer-feature/src/codex/coding-agents'
        dotfiles = REPO.parent / 'codex-devcontainer-dotfiles/install-devcontainer.sh'
        if not feature.exists() or not dotfiles.exists():
            self.skipTest('cross-repository adapters are not checked out')
        _, origin, installed = self.local_source()
        shutil.rmtree(installed)
        git = shutil.which('git')
        wrapper = self.mock / 'git'
        wrapper.write_text('#!/usr/bin/env python3\nimport os, sys\nargs = [a.replace("https://github.com/NovanMondon/coding-agents.git", ' + repr('file://' + str(origin)) + ') for a in sys.argv[1:]]\nos.execv(' + repr(git) + ', [' + repr(git) + '] + args)\n')
        wrapper.chmod(0o755)
        processes = [subprocess.Popen([str(dotfiles)], cwd=self.root, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True),
                     subprocess.Popen([str(feature), 'sync', '--automatic', '--workspace', '.'], cwd=self.workspace, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)]
        for process in processes:
            stdout, stderr = process.communicate(timeout=45)
            self.assertEqual(process.returncode, 0, stderr)
        self.assertTrue((installed / '.git').exists())
        self.assertTrue((self.system / 'hooks.json').is_symlink())
        self.assertEqual(len(self.checkpoints()), 1)
        (self.system / 'hooks.json').unlink()
        self.call([dotfiles])
        self.assertTrue((self.system / 'hooks.json').is_symlink())
        self.assertEqual(len(self.checkpoints()), 1)


if __name__ == '__main__':
    unittest.main()
