---
name: show-command
description: コマンドをユーザーに提案・提示するときに使用するスキル
---

# Show Command

コマンドをユーザーに提案・提示するとき、以下を守ってください。

- コマンドはコピー＆ペーストで実行できる形式で提示すること
- 途中でエラーが起きたらそれ以降実行すべきでないコマンドの場合、途中でエラーが起きたら中断するようにコマンドを作成すること。


### Good Example

```
npm ci &&
npm run build
```

```
(
  set -euo pipefail
  cd ./my-app
  npm ci
  npm run build
)
```

## Node

### Good Example

```
node <<'NODE'
const message = "It's ready!";
console.log(message);
console.log("$HOME is printed literally.");
NODE
```
