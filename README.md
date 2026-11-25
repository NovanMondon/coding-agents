# coding-agents

Codexで共通利用する `AGENTS.md` 、設定、skillsをまとめたリポジトリです。

## インストール

個人用のWSL・Dev Containerを対象としています。
`/etc/codex/` への初回リンク配置には管理者権限が必要です。
通常のユーザーで実行すると、その配置処理だけに `sudo` を使います。
`install.sh` 全体を `sudo` で実行しないでください。

### WSL

各WSLディストリビューションで実行します。

```bash
git clone --recurse-submodules https://github.com/NovanMondon/coding-agents.git ~/coding-agents
~/coding-agents/install.sh
```

### Dev Container

`codex-devcontainer-dotfiles` がこのリポジトリを `~/.local/share/coding-agents` に取得し、インストーラーを実行します。
root以外で実行するDev Containerでは、対話なしで `sudo` を使える必要があります。

### インストール後

GitHub MCPのPATは環境ごとに登録します。未登録などの問題があれば、インストーラーが登録コマンドを表示します。
続けて [GitHub MCPの設定手順](docs/github-mcp.md) を確認してください。

## 共通設定と環境ごとの設定

次のシンボリックリンクを作成します。

```text
~/.codex/AGENTS.md -> coding-agents/AGENTS.md
~/.agents/skills   -> coding-agents/codex/skills
/etc/codex/config.toml -> coding-agents/codex/config.toml
/etc/codex/github-mcp-headers -> coding-agents/codex/github-mcp-headers
```

`CODEX_HOME` が設定されている場合、上の `~/.codex` は `$CODEX_HOME` になります。
既存のファイル、ディレクトリ、別の場所を指すシンボリックリンクは上書きしません。

`codex/config.toml` でモデル、推論の強さ、サービス設定、keymap、CLIの完了通知、GitHub MCPの接続設定を共有します。
全環境へ反映する変更はこのファイルを編集してGitで共有します。
`/etc/codex/config.toml` は、その環境の全ユーザーに適用されるため、個人用のWSL・Dev Containerを想定しています。

環境固有の設定は `$CODEX_HOME/config.toml` （未設定なら `~/.codex/config.toml` ）に置きます。
こちらが共通設定より優先されるため、共通化した項目を両方に残すと共通設定の更新が反映されません。
既存環境ではローカルの設定をバックアップし、共通化する項目だけを取り除いてください。
プロジェクトの信頼設定やCodexが管理する表示状態はローカルに残します。
インストーラーはローカルの `config.toml` を変更しません。

設定の優先順位は [公式ドキュメント](https://learn.chatgpt.com/docs/config-file/config-basic) を参照してください。

### 権限設定

共通設定は、作業領域への書き込みを許可し、コマンドのネットワークアクセスを無効にする既定値を提供します。
機密ファイルの読み取り禁止は一律には設定せず、必要な対象を各利用環境・プロジェクトで指定します。

プロジェクト固有の設定は、信頼済みリポジトリの `.codex/config.toml` に置きます。
リポジトリで共有する権限プロファイルは、個人用の `my-default` に依存せず、組み込みの `:workspace` を継承してください。
別のプロファイルを選択した場合、 `my-default` 内の設定は自動では引き継がれません。

権限プロファイルは、旧方式の `sandbox_mode` や `sandbox_workspace_write` と併用しないでください。

## GitHub MCP

GitHubの読み取りには、PATで認証するGitHub公式のHTTP MCPサーバーを使用します。
CLIとVS CodeのCodex拡張で接続設定を共有し、PATは各環境に保存します。
PATの発行・登録・確認・更新と接続できない場合の対処は、 [GitHub MCP](docs/github-mcp.md) を参照してください。

## CLIの完了通知

CLIは各ターンの応答完了時に、端末のフォーカス状態に関係なくOSC 9通知を送ります。
VS Codeの統合ターミナルでは、 [Terminal Notification](https://marketplace.visualstudio.com/items?itemName=wenbopan.vscode-terminal-osc-notifier) 拡張を使用します。
`codex-devcontainer-feature` を利用するDev Containerでは、この拡張もインストール対象になります。
VS Code 1.93以上とShell Integrationの有効化が必要です。OS側でも通知を許可してください。

## 更新

`install.sh` は、Bash開始時にリポジトリとsubmoduleを更新するコマンドを `~/.bashrc` へ追加します。
更新に失敗した場合は、現在の内容をそのまま利用します。
更新するとリンク先の内容にも反映されます。
IDEのみを使ってBashを起動しない場合は、リポジトリのルートで次を実行してください。
WSLの標準配置先は `~/coding-agents` 、Dev Container内は `~/.local/share/coding-agents` です。

```bash
git pull --ff-only
git submodule update --init --recursive
```

設定の更新後はCodexを再起動してください。

## 構成

- `AGENTS.md` : 共通の指示
- `codex/config.toml` : 共通のCodex設定とkeymap
- `codex/github-mcp-headers` : GitHub MCP用の認証ヘッダー取得
- `codex/set-github-pat` : 環境ごとのPAT登録・更新
- `docs/github-mcp.md` : GitHub MCPの設定と運用手順
- `codex/skills` : 自作skills
- `vendor/seraphr-agent-skills` : [seraphr/agent-skills](https://github.com/seraphr/agent-skills) のsubmodule

自作skillsは [NovanMondon/agents-skills](https://github.com/NovanMondon/agents-skills) の `d2ab0c83c8b40e71ef958807ed4f5c8ee611ccd7` から移行しました。
