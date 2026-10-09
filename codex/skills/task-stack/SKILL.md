---
name: task-stack
description: 現在の会話からタスクを抽出し、WBSによるタスク構造とFocus Stackによる現在の実行文脈を分離して可視化する。
---

# Task Stack

現在の会話に存在するタスクを以下の2つの構造に分離して整理する。

1. WBS (Work Breakdown Structure): 何を達成するために、どの作業が必要か
2. Focus Stack: 現在どの作業文脈にいて、何が何に割り込んでいるか

WBSの親子関係とFocus Stackの親子関係を混同しないこと。
必要に応じて、現在のファイルの状態を再確認すること。

## WBS

会話中で明示または合意されたタスクをMECEかつ構造的に抽出する。

タスク間に「part-of」の関係がある場合のみ親子関係にする。

親タスクを達成するための構成要素でないタスクを、単に途中で発生したという理由だけで子タスクにしない。

独立した目的を持つタスクが複数ある場合は、複数のWBSルートを許容する。

### Statusを付与する

各WBSタスクに以下のいずれかの状態を付与する。

- NOT_STARTED: 未着手
- IN_PROGRESS: 着手済みで未完了
- BLOCKED: 外部条件や他タスク待ちで進行不能
- DONE: 完了
- CANCELLED: 実施しないことが確定
- UNKNOWN: 会話から判断不能

現在フォーカスされているかどうかをStatusで表現しない。
現在位置はFocus Stackで表現する。

## Focus Stack

現在の会話で、どのタスクを処理している文脈なのかを抽出する。

Focus Stackはbottomからtopへ現在の実行文脈を表す。

最上位の要素をCURRENTとする。

新しい独立タスクが既存タスクの途中で開始された場合、そのタスクをFocus Stackにpushする。

割り込みタスクが完了し、元のタスクに戻った場合はpopする。

Focus Stack上の包含関係をWBS上のpart-of関係と解釈しない。

## 出力

以下の形式を基本とする。

### WBS

[STATUS] タスク
├─ [STATUS] サブタスク
│  ├─ [STATUS] サブタスク
│  └─ [STATUS] サブタスク
└─ [STATUS] サブタスク

独立したタスクがある場合は別ルートとして表示する。

### Focus Stack

Focus Stack [bottom → top]

タスク
└─ タスク
   └─ タスク ← CURRENT

### 不確実な点

以下が存在する場合のみ記載する。

- タスクか単なる会話上の話題か判別できない
- 親子関係が確定できない
- 完了状態が判別できない
- WBSに明らかな漏れがある可能性がある
- 分解軸が混在している

推測によって不確実性を隠さない。

## 例

会話上、

1. 「XXXする」を開始
  - XXX-AA, BB, CC, DD の存在が確認される
2. XXX-AAを完了
3. XXX-BBを開始
4. 途中で独立したYYY対応が発生
  - YYY-AA, BB の存在が確認される
5. YYY-AAを完了
6. 現在YYY-BBを処理中

の場合、以下のように表示する。

### WBS

[IN_PROGRESS] XXXする
├─ [DONE] XXX-AAの対応
├─ [IN_PROGRESS] XXX-BBの対応
├─ [NOT_STARTED] XXX-CCの対応
└─ [NOT_STARTED] XXX-DDの対応

[IN_PROGRESS] YYY対応
├─ [DONE] YYY-AAの対応
└─ [IN_PROGRESS] YYY-BBの対応

### Focus Stack

XXXする
└─ XXX-BBの対応
   └─ YYY対応
      └─ YYY-BBの対応 ← CURRENT
