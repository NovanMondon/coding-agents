# coding-agents

Codexで共通利用する`AGENTS.md`とskillsをまとめたリポジトリです。

## インストール

各WSLディストリビューションで実行します。

```bash
git clone --recurse-submodules https://github.com/NovanMondon/coding-agents.git ~/coding-agents
~/coding-agents/install.sh
```

次のシンボリックリンクを作成します。

```text
~/.codex/AGENTS.md -> coding-agents/AGENTS.md
~/.agents/skills   -> coding-agents/codex/skills
```

`CODEX_HOME`が設定されている場合、上の`~/.codex`は`$CODEX_HOME`になります。
既存のファイル、ディレクトリ、別の場所を指すシンボリックリンクは上書きしません。

Dev Containerでは、`codex-devcontainer-dotfiles`がこのリポジトリを取得してインストーラーを実行します。

## 更新

`install.sh`は、Bash開始時に次の更新を行うコマンドを`~/.bashrc`へ追加します。
更新に失敗した場合は、現在の内容をそのまま利用します。

```bash
git -C ~/coding-agents pull --ff-only
git -C ~/coding-agents submodule update --init --recursive
```

更新するとリンク先の内容にも反映されます。

## 構成

- `AGENTS.md`: 共通の指示
- `codex/skills`: 自作skills
- `vendor/seraphr-agent-skills`: [seraphr/agent-skills](https://github.com/seraphr/agent-skills)のsubmodule

自作skillsは[NovanMondon/agents-skills](https://github.com/NovanMondon/agents-skills)の`d2ab0c83c8b40e71ef958807ed4f5c8ee611ccd7`から移行しました。
