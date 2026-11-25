#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
codex_home="${CODEX_HOME:-$HOME/.codex}"
system_config="/etc/codex/config.toml"
system_github_headers="/etc/codex/github-mcp-headers"

check_link() {
  local source_path="$1"
  local target_path="$2"

  if [ -L "$target_path" ]; then
    local current_target
    current_target="$(readlink -- "$target_path")"
    if [ "$current_target" = "$source_path" ]; then
      return
    fi
    printf 'coding-agents: %s already points to %s\n' "$target_path" "$current_target" >&2
    exit 1
  fi

  if [ -e "$target_path" ]; then
    printf 'coding-agents: %s already exists and was not changed\n' "$target_path" >&2
    exit 1
  fi
}

create_link() {
  local source_path="$1"
  local target_path="$2"
  shift 2

  if [ -L "$target_path" ]; then
    return
  fi

  "$@" mkdir -p "$(dirname -- "$target_path")"
  "$@" ln -sT -- "$source_path" "$target_path"
  printf 'coding-agents: linked %s -> %s\n' "$target_path" "$source_path"
}

check_link "$repo_dir/AGENTS.md" "$codex_home/AGENTS.md"
check_link "$repo_dir/codex/skills" "$HOME/.agents/skills"
check_link "$repo_dir/codex/config.toml" "$system_config"
check_link "$repo_dir/codex/github-mcp-headers" "$system_github_headers"

# /etc への初回配置だけ管理者権限を使う
if [ ! -L "$system_config" ] || [ ! -L "$system_github_headers" ]; then
  system_command=()
  if [ "$EUID" -ne 0 ]; then
    if ! command -v sudo >/dev/null 2>&1; then
      printf 'coding-agents: sudo is required to install links in /etc/codex\n' >&2
      exit 1
    fi
    system_command=(sudo)
  fi
  create_link "$repo_dir/codex/github-mcp-headers" "$system_github_headers" "${system_command[@]}"
  create_link "$repo_dir/codex/config.toml" "$system_config" "${system_command[@]}"
fi

create_link "$repo_dir/AGENTS.md" "$codex_home/AGENTS.md"
create_link "$repo_dir/codex/skills" "$HOME/.agents/skills"

# bash 開始時に内容を更新する
bashrc="$HOME/.bashrc"
repo_dir_escaped="$(printf '%q' "$repo_dir")"
update_command="{ git -C $repo_dir_escaped pull --ff-only --quiet && git -C $repo_dir_escaped submodule update --init --recursive --quiet; } >/dev/null 2>&1 || true"

touch "$bashrc"
if ! grep -Fqx "$update_command" "$bashrc"; then
  printf '\n%s\n' "$update_command" >>"$bashrc"
  printf 'coding-agents: added the update command to %s\n' "$bashrc"
fi

# GitHub MCP の登録状態を確認し、必要なら登録コマンドを表示する
if ! "$system_github_headers" --check; then
  printf 'coding-agents: GitHub MCPのPAT登録状態を確認してください。\n' >&2
  printf 'coding-agents: PATを登録・更新するコマンド: %q\n' \
    "$repo_dir/codex/set-github-pat" >&2
fi
