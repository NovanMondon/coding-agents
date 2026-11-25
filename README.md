# coding-agents

Codexで共通利用する`AGENTS.md`、設定、skillsをまとめたリポジトリです。

## インストール

各WSLディストリビューションで実行します。
`/etc/codex/`への初回リンク配置には管理者権限が必要です。
通常のユーザーで実行すると、その配置処理だけに`sudo`を使います。
`install.sh`全体を`sudo`で実行しないでください。

```bash
git clone --recurse-submodules https://github.com/NovanMondon/coding-agents.git ~/coding-agents
~/coding-agents/install.sh
```

次のシンボリックリンクを作成します。

```text
~/.codex/AGENTS.md -> coding-agents/AGENTS.md
~/.agents/skills   -> coding-agents/codex/skills
/etc/codex/config.toml -> coding-agents/codex/config.toml
/etc/codex/github-mcp-headers -> coding-agents/codex/github-mcp-headers
```

`CODEX_HOME`が設定されている場合、上の`~/.codex`は`$CODEX_HOME`になります。
既存のファイル、ディレクトリ、別の場所を指すシンボリックリンクは上書きしません。

Dev Containerでは、`codex-devcontainer-dotfiles`がこのリポジトリを取得してインストーラーを実行します。
root以外で実行するDev Containerでは、対話なしで`sudo`を使える必要があります。

## 共通設定と環境ごとの設定

`codex/config.toml`でモデル、推論の強さ、サービス設定、keymap、CLIの完了通知、GitHub MCPの接続設定を共有します。
全環境へ反映する変更はこのファイルを編集してGitで共有します。
`/etc/codex/config.toml`は、その環境の全ユーザーに適用されるため、個人用のWSL・Dev Containerを想定しています。

環境固有の設定は`$CODEX_HOME/config.toml`（未設定なら`~/.codex/config.toml`）に置きます。
こちらが共通設定より優先されるため、共通化した項目を両方に残すと共通設定の更新が反映されません。
既存環境ではローカルの設定をバックアップし、共通化する項目だけを取り除いてください。
プロジェクトの信頼設定やCodexが管理する表示状態はローカルに残します。
インストーラーはローカルの`config.toml`を変更しません。

設定の優先順位は[公式ドキュメント](https://learn.chatgpt.com/docs/config-file/config-basic)を参照してください。

## GitHub MCP

CLIとVS CodeのCodex拡張は、同じ共通設定からGitHub公式のHTTP MCPサーバーに接続します。
`http_headers_helper`がPATファイルを読み、認証ヘッダーをCodexに渡します。
シェルの環境変数へのPATの登録は不要です。
接続するCodexプロセスがWSL・Dev Container内で動作し、両方のクライアントが同じ`CODEX_HOME`を使用することが前提です。
この機能はCodexが実行される環境からのHTTP接続用です。別のremote executor経由のMCP接続には使えません。

### 初回登録

`http_headers_helper`に対応したCodexを使用してください。
CLI 0.172.0と拡張同梱のCodex 0.171.0-alpha.13.2で設定の認識を確認しています。
各環境の`coding-agents`リポジトリのルートで、まずインストーラーを実行します。
既存環境でも、新しいヘッダー取得用スクリプトのリンクを追加するために再実行が必要です。
WSLの標準配置先は`~/coding-agents`、Dev Container内は`~/.local/share/coding-agents`です。

```bash
./install.sh
```

1. GitHubの[fine-grained PAT作成画面](https://github.com/settings/personal-access-tokens/new)で、名前・有効期限・対象の所有者とリポジトリを設定します。
2. コード閲覧、Issue操作、PRレビュー、CIログ閲覧には、`Contents: Read`、`Issues: Read and write`、`Pull requests: Read and write`、`Actions: Read`を権限の出発点にします。必要な操作に合わせて調整してください。
3. `Generate token`で発行したPATを、次のコマンドの非表示入力へ貼り付けます。PATをコマンド引数、チャット、共有設定には書かないでください。

```bash
./codex/set-github-pat
```

fine-grained PATは一つの所有者を対象とします。複数Organizationへのアクセスなど、用途によってはトークンの分割やclassic PATの検討が必要です。
Organizationの承認が必要な場合は、承認後に接続を確認してください。
詳しくは[GitHubのPAT管理手順](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)を参照してください。

PATは`${CODEX_HOME:-$HOME/.codex}/secrets/github-pat`に保存します。
`secrets`ディレクトリの権限は`700`、PATファイルは`600`です。
ホストや別コンテナの認証情報をコピーせず、利用する環境で登録してください。
`github-mcp-headers`は認証情報を標準出力へ返す内部コマンドなので、確認のために直接実行しないでください。

### 接続の確認と更新

登録後はCLI・Codex拡張を再起動し、それぞれからGitHub MCPで同じ対象リポジトリを取得できることを確認してください。
PAT未登録・空ファイル・不正な文字を含む場合、ヘッダー取得用スクリプトはエラー終了します。
期限切れ・権限不足はGitHubへの接続・操作時に検出されます。登録スクリプトはGitHubへ通信しません。
PATの差し替えは初回と同じ登録コマンドを使用し、Codexを再起動します。
入力の検証に失敗した場合、既存のPATは変更しません。

ローカル設定やプロジェクト設定に既存の`mcp_servers.github`がある場合は、共通設定と競合する項目を取り除いてください。
特に`bearer_token_env_var`、`http_headers.Authorization`、`env_http_headers.Authorization`と、以前のOAuth認証情報を併用しないでください。
以前`codex mcp login github`で認証していた環境では、CLIの`codex mcp logout github`でそのOAuth認証情報を解除してから再起動します。
ヘッダー取得用スクリプトより明示的なBearerトークンやOAuth認証情報が優先されます。
仕様は[CodexのHTTP MCP設定](https://learn.chatgpt.com/docs/extend/mcp#streamable-http-servers)を参照してください。

`codex-devcontainer-feature`を使うDev ContainerではPATを永続ボリューム内に保存します。
同じボリュームを使う再構築では保持され、ボリュームを削除した場合は再登録が必要です。

## CLIの完了通知

CLIは各ターンの応答完了時に、端末のフォーカス状態に関係なくOSC 9通知を送ります。
VS Codeの統合ターミナルでは、[Terminal Notification](https://marketplace.visualstudio.com/items?itemName=wenbopan.vscode-terminal-osc-notifier)拡張を使用します。
`codex-devcontainer-feature`を利用するDev Containerでは、この拡張もインストール対象になります。
VS Code 1.93以上とShell Integrationの有効化が必要です。OS側でも通知を許可してください。

## 更新

`install.sh`は、Bash開始時に次の更新を行うコマンドを`~/.bashrc`へ追加します。
更新に失敗した場合は、現在の内容をそのまま利用します。

```bash
git -C ~/coding-agents pull --ff-only
git -C ~/coding-agents submodule update --init --recursive
```

更新するとリンク先の内容にも反映されます。
IDEのみを使ってBashを起動しない場合は、上のコマンドをリポジトリの配置先に合わせて実行してください。
Dev Container内の配置先は`~/.local/share/coding-agents`です。
設定の更新後はCodexを再起動してください。

## 構成

- `AGENTS.md`: 共通の指示
- `codex/config.toml`: 共通のCodex設定とkeymap
- `codex/github-mcp-headers`: GitHub MCP用の認証ヘッダー取得
- `codex/set-github-pat`: 環境ごとのPAT登録・更新
- `codex/skills`: 自作skills
- `vendor/seraphr-agent-skills`: [seraphr/agent-skills](https://github.com/seraphr/agent-skills)のsubmodule

自作skillsは[NovanMondon/agents-skills](https://github.com/NovanMondon/agents-skills)の`d2ab0c83c8b40e71ef958807ed4f5c8ee611ccd7`から移行しました。

### 権限設定

共通設定は、作業領域への書き込みを許可し、コマンドのネットワークアクセスを無効にする既定値を提供します。
機密ファイルの読み取り禁止は一律には設定せず、必要な対象を各利用環境・プロジェクトで指定します。

プロジェクト固有の設定は、信頼済みリポジトリの `.codex/config.toml` に置きます。
リポジトリで共有する権限プロファイルは、個人用の `my-default` に依存せず、組み込みの `:workspace` を継承してください。
別のプロファイルを選択した場合、`my-default` 内の設定は自動では引き継がれません。

権限プロファイルは、旧方式の `sandbox_mode` や `sandbox_workspace_write` と併用しないでください。
