# PR #6–#13 合并顺序

更新：2026-10-14。给 Group 2 组员。这是当前 GitHub 上的叠栈，不是新的产品决定。不要开通托管模型账号。不要把 PR #4 或 #5 并进这条线。

## 两条线

| PR | 分支 | 合并基线 | 内容 |
|---|---|---|---|
| #6 | `cursor/tooling-review-docs-8674` | `main` | Muse／Dot 拆解文档。与下面的代码栈同时从 `main` 拉出。 |
| #7 | `cursor/owner-memory-agent-8674` | `main` | 拥有者记忆 |
| #8 | `cursor/folder-job-action-8674` | #7 | 指定文件夹作业 |
| #9 | `cursor/persona-file-8674` | #8 | 文字和语音共用人格 |
| #10 | `cursor/quiet-followup-8674` | #9 | 关闭跟进后跳过已排队的文字建议 |
| #11 | `cursor/quiet-schedule-8674` | #10 | 安静时段推迟跟进，一次最多 3 条 |
| #12 | `cursor/job-recovery-ux-8674` | #11 | 作业卡片说明读回失败后的下一步 |
| #13 | `cursor/text-adapters-8674` | #12 | 文字适配器，以及同一份作业绑定表 |

#6 和 #7 都会改 `handoff.md`、`product.md`、`decision-log.md`、`work-log.md`。代码栈还改 Desk Companion 程序。

## 建议顺序

一次只合并一个，从下往上。

1. 合并 **#7** 到 `main`。
2. 依次处理 **#8、#9、#10、#11、#12、#13**。每合并一个，把下一个分支变基到最新 `main`，再把它的 PR 基线改成 `main`，然后合并。
3. **#6** 放在 #7 之后。变基时会在上面四个活文档冲突。这四个文件保留 `main` 上的正文。保留 #6 新增的 `docs/tooling-and-review/`。

变基只发生在该 PR 自己的分支上，用 `--force-with-lease`。不要改写 `main`，也不要改写别人的分支。

```sh
git fetch origin
git switch cursor/folder-job-action-8674
git rebase origin/main
git push --force-with-lease
```

把示例里的分支换成「下一个尚未合并的 PR 分支」。GitHub 上把该 PR 的 base 改为 `main`，看完差异后再合并。

## 不要这样做

- 不要把 #13 直接并进 `main`，除非 #7 至 #12 都已经审过。那样一次会带上 #7 至 #13 的全部提交。若选择这条，合并后把 #7 至 #12 关掉，并注明提交已包含在 #13。
- 不要把 #4（`codex/full-body-3d-avatar`）或 #5（`codex/personal-agent-kernel-20261012`）插进 #7 至 #13。它们是另一条栈。
- 不要为了消冲突而重排功能提交。冲突只应出现在四个活文档，以及 #6 与代码栈同时改过的同一段落。

#13 之上若还有新的叠栈分支，等 #13 进入 `main` 之后按同样步骤接上。不要插到 #7 前面。
