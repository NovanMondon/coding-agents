#!/usr/bin/env bash
set -euo pipefail
node_version="$1"
nvm_version="$2"
user_dir="${CODING_AGENTS_USER_DIR:-$HOME}"
usable_node() {
  command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1 &&
    node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)'
}
if ! usable_node; then
  export NVM_DIR="${NVM_DIR:-$user_dir/.nvm}"
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    installer="$(mktemp)"
    trap 'rm -f -- "$installer"' EXIT
    curl --fail --location --silent --show-error --connect-timeout 10 --max-time 60 \
      "https://raw.githubusercontent.com/nvm-sh/nvm/v${nvm_version}/install.sh" -o "$installer"
    PROFILE=/dev/null bash "$installer" >&2
  fi
  # shellcheck source=/dev/null
  . "$NVM_DIR/nvm.sh" --no-use
  nvm use default >&2 2>/dev/null || true
  if ! usable_node; then
    nvm install "$node_version" >&2
    nvm alias default "$node_version" >&2
  fi
fi
node -e 'console.log(JSON.stringify({node: process.execPath, npm: process.argv[1]}))' "$(command -v npm)"
