"""One reconciliation path for installation, lifecycle events and manual repair."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]
USER = Path(os.environ.get('CODING_AGENTS_USER_DIR', str(Path.home())))
CODEX = Path(os.environ.get('CODEX_HOME', str(USER / '.codex'))).resolve()
SYSTEM = Path(os.environ.get('CODING_AGENTS_SYSTEM_DIR', '/etc/codex'))
STATE = USER / '.local/state/coding-agents'
TOOLS = USER / '.local/share/coding-agents-tools'
BIN = USER / '.local/bin'
INTERVAL = 3600


def say(message):
    print(f'coding-agents: {message}', file=sys.stderr)


def run(args, *, cwd=None, input=None, check=True, timeout=120):
    result = subprocess.run([str(x) for x in args], cwd=cwd, input=input,
                            text=True, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f'{args[0]} failed: {result.stderr.strip()}')
    return result


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        path.chmod(mode)
        return
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    temporary.chmod(mode)
    temporary.replace(path)


def save_json(path, data):
    write(path, json.dumps(data, indent=2, ensure_ascii=False) + '\n')


@contextlib.contextmanager
def lock(name):
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / (name + '.lock')).open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def git_root(directory):
    result = run(['git', '-C', directory, 'rev-parse', '--show-toplevel'], check=False)
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def refresh_source():
    status = run(['git', 'status', '--porcelain'], cwd=REPO).stdout
    if status.strip():
        say('共有リポジトリに未コミットの変更があるため、取得を省略して手元の内容を反映します。')
        return False
    before = run(['git', 'rev-parse', 'HEAD'], cwd=REPO).stdout
    run(['git', '-c', 'credential.interactive=false', 'pull', '--ff-only', '--quiet'], cwd=REPO, timeout=30)
    run(['git', 'submodule', 'update', '--init', '--recursive', '--quiet'], cwd=REPO, timeout=60)
    return before != run(['git', 'rev-parse', 'HEAD'], cwd=REPO).stdout


def runtime_environment():
    runtime = read_json(STATE / 'runtime.json', {})
    node = runtime.get('node')
    if not node or not Path(node).is_file():
        raise RuntimeError('Node.js の導入が未完了です。coding-agents sync を実行してください。')
    os.environ['PATH'] = str(Path(node).parent) + os.pathsep + os.environ.get('PATH', '')
    return node


def ensure_tools(check_latest):
    problems = []
    wanted = read_json(REPO / 'tools.json', {})
    node_info = json.loads(run(['bash', REPO / 'lib/ensure-node.sh', wanted['node'], wanted['nvm']], timeout=180).stdout)
    save_json(STATE / 'runtime.json', node_info)
    node = runtime_environment()
    npm = node_info['npm']
    resolved = read_json(STATE / 'versions.json', {})
    for package, requested in wanted['packages'].items():
        manifest = TOOLS / 'node_modules' / package / 'package.json'
        package_info = read_json(manifest, {})
        installed = package_info.get('version')
        version = requested
        if requested == 'latest':
            if check_latest or package not in resolved:
                try:
                    version = run([npm, 'view', package, 'version', '--json', '--fetch-retries=0', '--fetch-timeout=15000'], timeout=20).stdout
                    version = json.loads(version)
                    resolved[package] = version
                    save_json(STATE / 'versions.json', resolved)
                except (RuntimeError, subprocess.TimeoutExpired):
                    if not installed:
                        raise
                    problems.append(f'{package}: 最新版を取得できないため導入済みの {installed} を利用します。')
                    version = installed
            else:
                version = resolved[package]
        executables = package_info.get('bin', {})
        if isinstance(executables, str):
            executables = {package.rsplit('/', 1)[-1]: executables}
        broken = any(not (TOOLS / 'node_modules/.bin' / name).is_file() for name in executables)
        if installed != version or broken:
            say(f'{package}@{version} を導入します。')
            run([npm, 'install', '--prefix', TOOLS, '--no-audit', '--no-fund', '--fetch-retries=0', '--fetch-timeout=15000', f'{package}@{version}'], timeout=180)
        actual = read_json(manifest, {}).get('version')
        if actual != version:
            raise RuntimeError(f'{package}: requested {version}, installed {actual}')
    for command in ('codex', 'arb', 'agent-rollback'):
        executable = TOOLS / 'node_modules/.bin' / command
        if not executable.is_file():
            raise RuntimeError(f'{executable} is missing')
        target = BIN / command
        if target.is_symlink() or (target.exists() and not target.read_bytes().startswith(b'#!/bin/sh\n# Managed by coding-agents\n')):
            backup = STATE / 'bin-backups' / (command + '-' + str(time.time_ns()))
            backup.parent.mkdir(parents=True, exist_ok=True)
            target.replace(backup)
            say(f'{target} の従来の入口を {backup} に保存しました。')
        write(target, '#!/bin/sh\n# Managed by coding-agents\nexec ' + shlex.quote(node) + ' ' + shlex.quote(str(executable)) + ' "$@"\n', 0o755)
    run([BIN / 'codex', '--version'])
    run([BIN / 'arb', '--help'])
    return problems


def link(source, target, privileged=False, automatic=False, previous=None):
    if target.is_symlink():
        current = Path(os.path.abspath(target.parent / os.readlink(target)))
        if current == source:
            return
        if current != previous:
            raise RuntimeError(f'{target} points elsewhere; existing link was preserved')
    elif target.exists():
        raise RuntimeError(f'{target} already exists; existing file was preserved')
    command = []
    if privileged and not os.access(target.parent if target.parent.exists() else target.parent.parent, os.W_OK):
        command = ['sudo'] + (['-n'] if automatic else [])
    run(command + ['mkdir', '-p', target.parent])
    run(command + ['ln', '-sfnT', source, target])


def shell_entry(path):
    content = path.read_text() if path.exists() else ''
    # Remove the earlier installer-owned update line, not arbitrary shell commands.
    content = '\n'.join(line for line in content.splitlines()
                        if not (line.startswith('{ git -C ') and 'submodule update --init --recursive --quiet; } >/dev/null 2>&1 || true' in line and str(REPO) in line))
    content = re.sub(r'(?ms)^# BEGIN coding-agents\n.*?^# END coding-agents\n?', '', content).rstrip()
    entry = shlex.quote(str(BIN / 'coding-agents'))
    block = f'\n\n# BEGIN coding-agents\nexport PATH={shlex.quote(str(BIN))}:"$PATH"\n{entry} sync --automatic\n# END coding-agents\n'
    write(path, content + block, 0o644)


def migrate_mcp():
    path = CODEX / 'config.toml'
    if not path.exists():
        return
    content = path.read_text()
    pattern = r'(?ms)^\[mcp_servers\.agent-rollback\][^\n]*\n(.*?)(?=^\[|\Z)'
    match = re.search(pattern, content)
    if not match:
        return
    # Only migrate the exact configuration written by the former setup command.
    lines = [line.strip() for line in match[1].splitlines() if line.strip() and not line.lstrip().startswith('#')]
    normal = '\n'.join(lines)
    if not (re.search(r'^command\s*=\s*"(?:arb|agent-rollback)"$', normal, re.M)
            and re.search(r'^args\s*=\s*\[\s*"mcp"\s*\]$', normal, re.M) and len(lines) == 2):
        raise RuntimeError('ローカルの mcp_servers.agent-rollback が共通設定を上書きしています。独自設定を保護して停止しました。')
    write(path.with_name(f'config.toml.before-coding-agents-{time.time_ns()}'), content)
    write(path, content[:match.start()] + content[match.end():])


def ensure_configuration(automatic):
    link(REPO / 'bin/coding-agents', BIN / 'coding-agents')
    link(REPO / 'codex/AGENTS.md', CODEX / 'AGENTS.md', previous=REPO / 'AGENTS.md')
    link(REPO / 'codex/skills', USER / '.agents/skills')
    link(CODEX / 'secrets/github-pat', USER / '.config/coding-agents/github-pat')
    # The initial administrative setup gives this personal environment's user
    # ownership, so future feature additions do not repeatedly require sudo.
    if not SYSTEM.exists() or not os.access(SYSTEM, os.W_OK):
        command = [] if os.geteuid() == 0 else ['sudo'] + (['-n'] if automatic else [])
        run(command + ['install', '-d', '-m', '0755', '-o', str(os.getuid()), '-g', str(os.getgid()), SYSTEM])
    for filename in ('config.toml', 'github-mcp-headers', 'hooks.json', 'rollback-hook', 'agent-rollback-mcp'):
        link(REPO / 'codex' / filename, SYSTEM / filename, privileged=True, automatic=automatic)
    migrate_mcp()
    shell_entry(USER / '.bashrc')
    shell_entry(USER / '.profile')


def migrate_hooks(root):
    path = root / '.codex/hooks.json'
    if not path.exists():
        return
    config = read_json(path, {})
    changed = False
    for event, groups in config.get('hooks', {}).items():
        kept_groups = []
        for group in groups:
            hooks = group.get('hooks', [])
            kept = [hook for hook in hooks if not (hook.get('type') == 'command' and re.search(r'(?:^|/)agent-rollback\.js["\x27]?\s+hook\s*$', hook.get('command', '')))]
            changed |= len(kept) != len(hooks)
            if kept or not hooks:
                kept_groups.append({**group, 'hooks': kept})
        config['hooks'][event] = kept_groups
    if changed:
        backup = STATE / 'hook-backups' / (hashlib.sha256(str(root).encode()).hexdigest() + '.json')
        if not backup.exists():
            write(backup, path.read_text())
        write(path, json.dumps(config, indent=2) + '\n', 0o644)
        say(f'{root}: 旧 agent-rollback hooks を共通 hooks に移行しました。Codex を再起動してください。')


def ensure_workspace(directory, event=None):
    root = git_root(directory)
    if root is None:
        return
    key = hashlib.sha256(str(root).encode()).hexdigest()
    with lock('workspace-' + key):
        tracked = run(['git', 'ls-files', '--', '.agent-rollback'], cwd=root).stdout
        if tracked.strip():
            raise RuntimeError(f'{root}: .agent-rollback contains tracked files')
        exclude = Path(run(['git', 'rev-parse', '--git-path', 'info/exclude'], cwd=root).stdout.strip())
        if not exclude.is_absolute():
            exclude = root / exclude
        existing = exclude.read_text() if exclude.exists() else ''
        if '/.agent-rollback/' not in existing.splitlines():
            write(exclude, existing.rstrip('\n') + '\n/.agent-rollback/\n', 0o644)
        migrate_hooks(root)
        marker = root / '.agent-rollback/coding-agents.json'
        if not marker.exists() or not (root / '.agent-rollback/checkpoints').is_dir():
            run([BIN / 'arb', '--cwd', root, 'init'])
            checkpoints = json.loads(run([BIN / 'arb', '--cwd', root, 'list', '--json']).stdout)['checkpoints']
            if not checkpoints:
                run([BIN / 'arb', '--cwd', root, 'checkpoint', 'before-agent-work'])
            save_json(marker, {'initialized': True})
        # Each workspace gets its own registry file, so concurrent hooks cannot lose entries.
        save_json(STATE / 'workspaces' / (key + '.json'), {'path': str(root)})
        if event:
            event['cwd'] = str(root)
            run([BIN / 'arb', '--cwd', root, 'hook'], input=json.dumps(event), timeout=25)


def pat_status(automatic, replace=False):
    result = run([REPO / 'codex/github-mcp-headers', '--check'], check=False)
    if result.returncode == 0 and not replace:
        return 'registered (local check only)'
    if not automatic and sys.stdin.isatty():
        say('GitHub PAT を登録します。発行先: https://github.com/settings/personal-access-tokens/new')
        result = subprocess.run([str(REPO / 'codex/set-github-pat')])
        if result.returncode == 0:
            return 'registered (local check only)'
        raise RuntimeError('GitHub PAT の登録が完了しませんでした。既存のPATは保持しています。')
    elif replace:
        raise RuntimeError('PAT の入力には対話端末で coding-agents sync --github-pat を実行してください。')
    say('GitHub PAT は未登録または読み取り不可です。対話端末で coding-agents sync を実行してください。その他の設定は反映します。')
    return 'needs input'


def sync(args):
    with lock('environment'):
        status = read_json(STATE / 'status.json', {})
        due = not args.automatic or time.time() - status.get('last_update', 0) >= INTERVAL
        problems = []
        if due and not args.no_update:
            try:
                changed = refresh_source()
                if changed:
                    # Release the lock and restart from the updated implementation.
                    return 75
                status['last_update'] = time.time()
            except (RuntimeError, subprocess.TimeoutExpired) as error:
                problems.append('更新取得失敗: ' + str(error))
        for label, operation in (
            ('tools', lambda: ensure_tools(due and not args.no_update)),
            ('configuration', lambda: ensure_configuration(args.automatic)),
        ):
            try:
                problems.extend(operation() or [])
            except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
                problems.append(label + ': ' + str(error))
        workspace = args.workspace or (None if args.automatic else str(Path.cwd()))
        directories = {x['path'] for x in (read_json(p, {}) for p in (STATE / 'workspaces').glob('*.json'))}
        if workspace:
            directories.add(workspace)
        for directory in sorted(directories):
            if not Path(directory).exists():
                continue
            try:
                ensure_workspace(directory)
            except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
                problems.append('workspace: ' + str(error))
        try:
            status['github_pat'] = pat_status(args.automatic, args.github_pat)
        except (RuntimeError, OSError) as error:
            problems.append('PAT: ' + str(error))
        expected_feature = read_json(REPO / 'tools.json', {}).get('devcontainer_feature')
        feature = os.environ.get('CODING_AGENTS_FEATURE_VERSION')
        status['container_rebuild_required'] = bool((feature or str(CODEX) == '/var/lib/codex-home') and feature != expected_feature)
        if status['container_rebuild_required']:
            say(f'コンテナの構成更新が必要です。Feature {expected_feature} を取得して Dev Container を再ビルドしてください。')
        if problems:
            status.pop('last_update', None)
        status.update(last_apply=time.time(), problems=problems)
        save_json(STATE / 'status.json', status)
        for problem in problems:
            say(problem)
        if problems:
            say(f'反映は未完了です。coding-agents sync で再試行できます。詳細: {STATE / "status.json"}')
        elif not args.automatic:
            say('設定を反映しました。読み込み済みの Codex 設定は再起動後に有効になります。')
        # Automatic entrypoints must not prevent the IDE/shell from starting.
        # Failures remain visible on stderr and in status.json; manual sync fails.
        return 1 if problems and not args.automatic else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['sync', 'hook', 'mcp'])
    parser.add_argument('--automatic', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--no-update', action='store_true', help='use the checked-out source and cached tool versions')
    parser.add_argument('--workspace', help='workspace to register and reconcile')
    parser.add_argument('--github-pat', action='store_true', help='replace the GitHub PAT through hidden input')
    args = parser.parse_args()
    os.environ['GIT_TERMINAL_PROMPT'] = '0'
    if args.automatic and args.github_pat:
        parser.error('--github-pat requires an interactive sync')
    if args.command == 'sync':
        result = sync(args)
        if result == 75:
            os.execv(sys.executable, [sys.executable, str(REPO / 'lib/environment.py'), *sys.argv[1:], '--no-update'])
        return result
    if args.command == 'mcp':
        runtime_environment()
        root = git_root(str(Path.cwd())) or Path.cwd()
        os.execv(str(BIN / 'arb'), [str(BIN / 'arb'), '--cwd', str(root), 'mcp'])
    event = json.load(sys.stdin)
    directory = event.get('cwd') or str(Path.cwd())
    if event.get('hook_event_name') == 'SessionStart':
        # Hook stdout is reserved for the Codex protocol. All sync diagnostics use stderr.
        result = run([REPO / 'bin/coding-agents', 'sync', '--automatic', '--workspace', directory], check=False, timeout=150)
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
    runtime_environment()
    ensure_workspace(directory, event)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        say(str(error))
        sys.exit(1)
