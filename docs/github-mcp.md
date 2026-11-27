# GitHub MCP

共有設定の `github` MCPは、GitHub公式のHTTPサーバーにPATで接続します。
CLIとVS CodeのCodex拡張で同じ設定を使い、PATは環境ごとに登録します。
全体の導入・更新方法は [README](../README.md) を参照してください。

## 前提条件

Codexが利用する環境内でセットアップし、CLIと拡張が同じ `CODEX_HOME` を使うようにしてください。
この方式は、その環境から直接HTTP MCPへ接続する場合に対応します。別のremote executor経由の接続には使えません。
Codexは `http_headers_helper` への対応が必要です。CLI 0.172.0と拡張同梱のCodex 0.171.0-alpha.13.2で設定の認識を確認しています。

導入・更新・PAT登録は任意のディレクトリから `coding-agents sync` を使います。

既存のGitHub MCP設定がある場合は、PAT登録前にローカル・プロジェクト設定の `mcp_servers.github` を確認し、共通設定と競合する項目を取り除いてください。
特に `bearer_token_env_var` 、`http_headers.Authorization` 、`env_http_headers.Authorization` と、以前のOAuth認証情報を併用しないでください。
以前 `codex mcp login github` で認証していた環境では、CLIの `codex mcp logout github` でそのOAuth認証情報を解除します。
明示的なBearerトークンやOAuth認証情報は、今回のヘッダー取得より優先されます。

## PATの発行・登録

初回導入は [README](../README.md) の入口から行います。
保存済みPATは自動で再利用します。未登録なら、自動反映は入力待ちにせず他の設定を進め、対話端末の `coding-agents sync` が非表示入力を案内します。

fine-grained PATは一つの所有者を対象とします。会社のリポジトリなら、Resource ownerにそのOrganizationを指定します。
複数Organizationを対象とする場合は、対象ごとにPATと接続設定を分けるなど、別の構成が必要です。

1. [fine-grained PAT作成画面](https://github.com/settings/personal-access-tokens/new) で名前・有効期限・Resource ownerを設定します。
2. Repository accessで対象リポジトリを選択します。
3. 読み取り用途では、必要な項目に `Read` を設定します。コード・Issue・PR・CIログを参照する場合の対象は、Contents、Issues、Pull requests、Actions、Metadataです。
4. `Generate token` でPATを発行し、次のコマンドの非表示入力へ貼り付けます。PATを引数、チャット、共有設定には書かないでください。

```bash
coding-agents sync --github-pat
```

Organizationの承認が必要な場合は、承認を待ってから接続を確認してください。
発行条件の詳細は [GitHubのPAT管理手順](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) を参照してください。

## 登録状態と接続の確認

登録状態は次のコマンドで確認します。成功時は何も出力せず、問題があれば理由を標準エラー出力へ表示して非ゼロで終了します。
確認対象はPATファイルの存在・読み取り可否・空値・文字種です。GitHubには通信せず、有効期限やアクセス権限は確認しません。
`--check` なしでは認証ヘッダーを出力するため、手動確認には使わないでください。

```bash
/etc/codex/github-mcp-headers --check
```

確認後、CLI・Codex拡張を再起動し、それぞれから `mcp__github__*` のツールで対象リポジトリを取得してください。
ChatGPT側のGitHub接続（ `mcp__codex_apps__github_*` ）で取得できても、このPAT用MCPの接続確認にはなりません。
共通のエージェント指示では、PAT用MCPが利用できない場合にChatGPT側の接続で代替せず、登録状態を確認するよう指定しています。

## PATの更新と再構築

PATの更新には、利用する環境で初回と同じ登録コマンドを実行します。
入力の検証に失敗した場合、既存のPATは変更せず、反映未完了として報告します。登録後はCodexを再起動してください。

```bash
coding-agents sync --github-pat
```

PATは `${CODEX_HOME:-$HOME/.codex}/secrets/github-pat` に保存します。
ホストや別コンテナの認証情報をコピーせず、利用する環境で登録してください。
`codex-devcontainer-feature` を使う場合の保存先は `/var/lib/codex-home/secrets/github-pat` です。
同じ永続ボリュームを使う再構築では保持され、インストーラーが固定リンクを作り直します。ボリュームを削除した場合は再登録が必要です。

## 接続できない場合

1. **確認コマンドがない**：`coding-agents sync` で設定を再反映してください。公開コマンド自体がない場合は [初回導入](../README.md#初回導入) の入口を使います。
2. **登録確認が失敗する**：固定リンクが未作成なら `coding-agents sync` を実行します。PATが未登録・不正なら `coding-agents sync --github-pat` で登録・更新してください。読み取り不可の場合は所有者と権限も確認します。
3. **登録確認は成功するが接続できない**：CodexのMCP接続エラーを確認します。PATの有効期限、Resource owner、対象リポジトリ、必要なRead権限、Organizationの承認状態、通信状態を確認してください。
4. **ChatGPT側の接続だけ成功する**：PAT用MCPは未確認です。Codexを再起動して `mcp__github__*` が利用できるか確認し、利用できなければ上記の診断を行ってください。

## 接続の仕組み

`/etc/codex/config.toml` の共有設定から、`https://api.githubcopilot.com/mcp/` に接続します。
`http_headers_helper` が `/etc/codex/github-mcp-headers` を呼び、`~/.config/coding-agents/github-pat` の固定リンクからPATを読んでAuthorizationヘッダーを生成します。
リンク先はインストール時の `${CODEX_HOME:-$HOME/.codex}/secrets/github-pat` です。helperに `CODEX_HOME` が渡らなくても同じPATを参照できます。
同じOSユーザーでは一つのPAT保存先を使います。登録時の `CODEX_HOME` とリンク先が異なる場合は処理を止めるため、インストール時と同じ環境で登録してください。
PATをシェルの環境変数に登録する必要はありません。保存時の権限は `secrets` ディレクトリが `700` 、PATファイルが `600` です。
仕様は [CodexのHTTP MCP設定](https://learn.chatgpt.com/docs/extend/mcp#streamable-http-servers) を参照してください。
