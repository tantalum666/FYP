# Group 2 Current Handoff

更新：2026-10-27。当前软件切片是离线演示、界面恢复、安全卫生和文字冒烟。硬件研究、`archive/` 和未合并的 A1 草稿没有改动。

## 当前状态与证据

- 软件健康 PR 仍待审查：[#21](https://github.com/tantalum666/FYP/pull/21) 是 CI 和开发脚本，[#22](https://github.com/tantalum666/FYP/pull/22) 是作业动作注册表，[#24](https://github.com/tantalum666/FYP/pull/24) 是模块说明。#21 的 Actions 作业没有启动，原因是账户付款或支出上限，不是测试失败。
- 本轮四支独立 PR：[#25](https://github.com/tantalum666/FYP/pull/25) 离线演示种子和假文字适配器，[#27](https://github.com/tantalum666/FYP/pull/27) 界面的离线／错误／会话过期，[#28](https://github.com/tantalum666/FYP/pull/28) 凭据文件、代理下的 Secure cookie 和开发访问日志，[#30](https://github.com/tantalum666/FYP/pull/30) Qwen／Gemini 文字冒烟。冒烟默认跳过，不进 CI，未使用真实密钥。
- 本地验证：#25 后端 186 通过；#27 前端 19 通过且构建通过；#28 后端 190 通过；文字冒烟分支后端 187 通过。没有付费 API。
- PR #4、#5、#15、#16 仍不合并。AliceChan／统一 Omni 的本地未发布增量仍不在 `main`。

## 一个下一步

**恢复 GitHub Actions 额度后重跑 #21，再由 Codex 按下面的顺序审查合并。** 不要并入 A1 草稿。

合并顺序：#21，然后 #22 与 #24。其后 #25、#27、#28 和 #30 互不依赖，可按任意顺序合并。`scripts/dev.sh` 在 #21、#25、#28 各改一行，冲突时三处都保留。#24 和 #30 都会改本文件；以包含上述全部 PR 的这一版为准，不要退回只写软件健康的交接。
