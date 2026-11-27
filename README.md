# coding-agents

個人用のWSL・Dev Containerで、Codexを使う環境を自動構築・更新するリポジトリです。
必要なツール、共通設定、skills、GitHub MCP、agent-rollbackを、環境の利用開始時にまとめて反映します。
機能ごとのセットアップコマンドを覚える必要はありません。手動で反映し直す入口は **`coding-agents sync`** です。

## 初回導入

WSLではPython 3、Git、curl、sudoを使える通常ユーザーで実行します。`/etc/codex/` の初回配置だけsudoを使います。
個人用環境の `/etc/codex/` を実行ユーザー所有にし、その後の自動更新ではsudoを不要にします。
インストーラー全体をsudoで実行しないでください。

```bash
git clone --recurse-submodules https://github.com/NovanMondon/coding-agents.git ~/coding-agents &&
~/coding-agents/install.sh
```

Dev Containerは `codex-devcontainer-feature` 1.2.0以降が、作成・起動・接続時に共有リポジトリを取得して同じ反映処理を実行します。
`codex-devcontainer-dotfiles` のインストーラーも同じ処理を呼びます。Featureはdotfilesの実行順やBashの起動に依存しません。
既存のコンテナへこの起動処理を導入する際は、更新したFeatureで一度再ビルドしてください。

初回のCodexログインとGitHub PATの発行・入力は必要です。
手動のsyncは対話端末でPAT未登録を検出すると非表示入力を案内します。自動実行では入力待ちにせず、他の設定を反映します。
詳細は [GitHub MCP](docs/github-mcp.md) を参照してください。

## 自動反映と手動の再反映

| 入口 | 実行する処理 |
|---|---|
| Dev Containerの作成・起動・接続 | 環境全体と、そのワークスペースの反映 |
| WSL等のBash開始・ログイン | 環境全体と登録済みワークスペースの反映 |
| Codexのセッション開始 | 同じ環境反映と、作業リポジトリの初期化・保存 |
| 手動の `coding-agents sync` | 更新取得を即時確認し、同じ内容を再反映 |

初回導入後、新しいシェルでは次の1コマンドを任意のディレクトリから実行できます。

```bash
coding-agents sync
```

導入直後の既存シェルでは `~/.local/bin/coding-agents sync` でも同じ処理を呼べます。
現在位置がGitリポジトリなら自動で対象に加えます。既に利用したリポジトリは現在位置に関係なく反映します。
IDEのみの利用も、共通のCodex hooksから対象を登録します。

自動実行の更新確認は最大1時間に1回です。常駐監視はせず、次の起動・接続・セッション開始で確認します。
設定ファイルやリンクの修復は更新確認の間隔に関係なく実行します。同時起動はロックで重複を防ぎます。
共有リポジトリに未コミット変更があれば取得を省略し、手元の内容を使います。変更を勝手に破棄しません。
取得失敗時は手元の設定・導入済みツールを利用し、失敗理由を表示します。次回に再試行します。

結果は `~/.local/state/coding-agents/status.json` に残します。自動実行の失敗はIDEやシェルの起動を止めず、手動実行の失敗は非ゼロで終了します。
認証の入力待ちやコンテナ再構築待ちは結果に別途記録します。PATの内容は記録しません。

設定ファイルの反映と、起動済みプロセスへの反映は別です。読み込み済みのCodex設定はCodex再起動後に有効になります。
マウント・権限・拡張などFeature側の変更にはコンテナの再ビルドが必要です。syncは実行中のセッションを終了したり、コンテナを自動破棄したりしません。

## 何を管理するか

`tools.json` がNode.jsの導入バージョン、Codex CLI、agent-rollback、必要なFeatureの版を管理します。
Node.js 20以上とnpmがあれば利用し、なければnvmでNode.jsを導入します。
Codex CLIは更新確認時の最新版、agent-rollbackは指定版を使います。パッケージは `~/.local/share/coding-agents-tools` に導入します。
`~/.local/bin` のCLI入口はNode.jsの実行パスを含むため、nvmを読み込まないシェルやhooksからも動きます。
同名の既存CLI入口があれば `~/.local/state/coding-agents/bin-backups` に保存してから管理用の入口を配置します。

主な設定は次のリンクで反映します。

```text
~/.codex/AGENTS.md -> coding-agents/codex/AGENTS.md
~/.agents/skills -> coding-agents/codex/skills
~/.local/bin/coding-agents -> coding-agents/bin/coding-agents
~/.config/coding-agents/github-pat -> ~/.codex/secrets/github-pat
/etc/codex/config.toml -> coding-agents/codex/config.toml
/etc/codex/hooks.json -> coding-agents/codex/hooks.json
/etc/codex/github-mcp-headers -> coding-agents/codex/github-mcp-headers
/etc/codex/rollback-hook -> coding-agents/codex/rollback-hook
/etc/codex/agent-rollback-mcp -> coding-agents/codex/agent-rollback-mcp
```

`CODEX_HOME` が設定されていれば、上の `~/.codex` はそのディレクトリになります。
以前の `coding-agents/AGENTS.md` へのリンクは配布用ファイルへ移行します。無関係のファイルやリンクは上書きせず報告します。
`/etc/codex` の設定とhooksは環境全体へ適用するため、個人用WSL・Dev Containerを想定しています。

環境固有の設定は `$CODEX_HOME/config.toml` （未設定なら `~/.codex/config.toml` ）に置きます。
こちらが共通設定より優先されます。独自に上書きした項目は共通設定の変更を受けません。
旧セットアップが作ったagent-rollbackのMCP設定だけはバックアップして共通設定に移行します。
プロジェクト信頼設定、表示状態、その他のローカル設定は保持します。

共通の権限設定は作業領域への書き込みを許可し、コマンドのネットワークアクセスを無効にします。
プロジェクトの権限プロファイルは個人用の `my-default` ではなく `:workspace` を継承してください。
権限プロファイルは旧方式の `sandbox_mode` や `sandbox_workspace_write` と併用しないでください。

## 自動チェックポイント

agent-rollbackはCodexのSessionStart、UserPromptSubmit、PreToolUse、PostToolUseでチェックポイントを作ります。
共通のsystem hooksを使うので、リポジトリごとの `arb init codex` や `/hooks` の信頼操作は通常手順にありません。
対象は作業場所のGitリポジトリルートです。Git外では初期化・保存を行いません。worktreeも各作業ツリーを対象にします。

初回は `/.agent-rollback/` をGitのローカル除外に加え、初期チェックポイントを作ります。
既存のチェックポイントは保持し、初期保存を重複させません。保存領域がGit追跡済みなら除外では解決しないため報告します。
以前の `arb init codex` が生成したhooksはバックアップして除去し、他のhooksを保持します。移行後はCodexを再起動してください。

## CLIの完了通知

CLIはターン完了時にOSC 9通知を送ります。
VS CodeではFeatureが [Terminal Notification](https://marketplace.visualstudio.com/items?itemName=wenbopan.vscode-terminal-osc-notifier) を導入します。
VS Code 1.93以上、Shell Integration、OS側の通知許可が必要です。

## 開発

開発用規約はルートの `AGENTS.md`、他環境へ配布する指示は `codex/AGENTS.md` です。
機能追加は共通の自動反映経路への接続まで含めます。個別手動セットアップを追加するだけでは完了しません。
個人用環境のため、自動テストはデータ破壊・認証情報の漏えいと消失・環境の起動不能など、致命的な問題の防止に絞ります。
それ以外は変更に応じた構文チェックと必要な実操作での確認で済ませます。テスト追加やCIを一律の完了条件にはしません。

| ファイル | 役割 |
|---|---|
| `bin/coding-agents` / `lib/environment.py` | 公開入口と更新・反映・修復の本体 |
| `tools.json` | ツールと必要なFeatureの版 |
| `codex/config.toml` / `codex/hooks.json` | 共通設定、MCP、hooks |
| `codex/skills` | 配布する自作skills |
| `vendor/seraphr-agent-skills` | 外部skillsのsubmodule |

テストは一時ディレクトリを使い、実環境のホームや `/etc` を変更しません。
既存テスト一式を実行する必要がある場合は、次をリポジトリルートで実行します。npmを使って実パッケージをテスト用領域に取得してから、公開入口を検証します。

```bash
npm install --prefix /tmp/coding-agents-test-deps --ignore-scripts --no-audit --no-fund agent-rollback@1.1.1 &&
CODING_AGENTS_TEST_ARB_PREFIX=/tmp/coding-agents-test-deps python3 -m unittest discover -s tests -v
```

Codex CLIの取得・実行はテスト用の代替を使い、有料のモデル呼び出しは行いません。
`CODING_AGENTS_USER_DIR` と `CODING_AGENTS_SYSTEM_DIR` はテスト用の配置先指定です。通常の導入では指定しません。
