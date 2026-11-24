---
name: howto
description: 具体的なやり方を忘れたときなどのためのスキル。[コマンド完了後の通知]
---

# HowTo

## コマンド完了後の通知

OSC9/OSC777 を使用した通知を行うコマンド

例
```
./xxx.exe; printf '\033]9;XXXが完了しました\007'
```
