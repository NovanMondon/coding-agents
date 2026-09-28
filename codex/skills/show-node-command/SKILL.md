---
name: show-node-command
description: node のコマンドをユーザーに提案・提示するときに使用するスキル
---

# Show Node Command

node のコマンドをユーザーに提示する際、コピー＆ペーストで実行できるようなコードを提示してください。

## 典型的なよいやり方

```
node -e '
  console.log("Hello, Node!");
  console.log(
    "Hello, Node!"
  );
  console.log("Hello, Node!");
'
```
