# coding-agents

Codexで共通利用する`AGENTS.md`、設定、skillsをまとめたリポジトリです。

## インストール

各WSLディストリビューションで実行します。
`/etc/codex/config.toml`への初回配置には管理者権限が必要です。
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
```

`CODEX_HOME`が設定されている場合、上の`~/.codex`は`$CODEX_HOME`になります。
既存のファイル、ディレクトリ、別の場所を指すシンボリックリンクは上書きしません。

Dev Containerでは、`codex-devcontainer-dotfiles`がこのリポジトリを取得してインストーラーを実行します。
root以外で実行するDev Containerでは、対話なしで`sudo`を使える必要があります。

## 共通設定と環境ごとの設定

`codex/config.toml`でモデル、推論の強さ、サービス設定、keymap、CLIの完了通知を共有します。
全環境へ反映する変更はこのファイルを編集してGitで共有します。
`/etc/codex/config.toml`は、その環境の全ユーザーに適用されるため、個人用のWSL・Dev Containerを想定しています。

環境固有の設定は`$CODEX_HOME/config.toml`（未設定なら`~/.codex/config.toml`）に置きます。
こちらが共通設定より優先されるため、共通化した項目を両方に残すと共通設定の更新が反映されません。
既存環境ではローカルの設定をバックアップし、共通化する項目だけを取り除いてください。
プロジェクトの信頼設定やCodexが管理する表示状態はローカルに残します。
インストーラーはローカルの`config.toml`を変更しません。

設定の優先順位は[公式ドキュメント](https://learn.chatgpt.com/docs/config-file/config-basic)を参照してください。

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
- `codex/skills`: 自作skills
- `vendor/seraphr-agent-skills`: [seraphr/agent-skills](https://github.com/seraphr/agent-skills)のsubmodule

自作skillsは[NovanMondon/agents-skills](https://github.com/NovanMondon/agents-skills)の`d2ab0c83c8b40e71ef958807ed4f5c8ee611ccd7`から移行しました。
