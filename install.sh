#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
codex_home="${CODEX_HOME:-$HOME/.codex}"

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

  if [ -L "$target_path" ]; then
    return
  fi

  mkdir -p "$(dirname -- "$target_path")"
  ln -s "$source_path" "$target_path"
  printf 'coding-agents: linked %s -> %s\n' "$target_path" "$source_path"
}

check_link "$repo_dir/AGENTS.md" "$codex_home/AGENTS.md"
check_link "$repo_dir/codex/skills" "$HOME/.agents/skills"

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
