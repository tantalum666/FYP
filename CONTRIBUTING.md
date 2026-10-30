# FYP · Group 2 collaboration

本仓库保存当前 Desk Companion 工程以及从选题开始的学校文档、研究、设计、历史 Senplate 工程和验证记录。当前要求以 [product.md](product.md) 为准；恢复工作先看 [handoff.md](handoff.md)，使用 AI 编程代理时遵守 [AGENTS.md](AGENTS.md)。历史文件的日期和状态保留。

## 加入仓库

仓库地址：[tantalum666/FYP](https://github.com/tantalum666/FYP)，默认分支 `main`，为私人仓库。

1. Xu Ziqian 和 Li Wenhua 各自注册或登录 GitHub，把 **GitHub 用户名**交给 Yuan Yuchen。
2. 仓库拥有者打开 **Settings → Collaborators → Add people**，搜索用户名，核对账号后发送邀请。
3. 组员登录自己的账号接受邀请，再打开仓库。私人个人仓库的协作者具有读写权限；仓库设置和成员管理仍由拥有者负责。

步骤依据：[GitHub 官方邀请说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)及[个人仓库权限](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)。本次建仓不包含向任何成员发送邀请。

## 取得并运行当前软件

可以在 GitHub Desktop 登录后选择 Clone repository，也可以用终端。私人仓库需要自己的 GitHub 登录凭据；不要互相传密码或访问令牌。

```sh
git clone https://github.com/tantalum666/FYP.git
cd FYP
```

第一次配置 Git 时，填写自己的姓名和 GitHub 账户邮件；可使用 GitHub 的私密 noreply 邮件。这样后续提交能分别记录每个人的贡献。此次首次提交是既有工作的集中快照，不代表所有内容由提交人独立完成；既有 AI 辅助记录和成员待核实归属继续保留。

当前软件需 Python 3.12+、uv 和 Node 22.12+。以下启动命令适用 macOS / Linux；Windows 可在 WSL 中使用。iPhone 构建需要 macOS / Xcode。

```sh
cd desk-companion
uv sync --frozen
cd frontend
npm ci
npm run build
cd ..
./scripts/dev.sh
```

打开 `http://127.0.0.1:5190/`；常亮屏是 `http://127.0.0.1:5190/?surface=device`。默认账号 `owner` 的密码在**每位成员自己的** `desk-companion/.runtime/credentials.json` 首次生成；显式本机预览可免登录。本机凭据与数据库不分发，相机／唤醒权重按说明下载；许可允许分发的角色素材保留来源与许可。

可选相机／音频依赖、Linux 设备安装、iPhone 框架准备、真实服务配置及评价步骤见[软件 README](desk-companion/README.md)和[操作指南](desk-companion/docs/operator-guide.md)。没有实体设备或语音密钥也可先开发日历、事务和界面。硬件及模型实际表现仍须另行验证。

## 每次修改的流程

1. 开工前同步 `main`，随后创建自己的分支。例如 `feature/xu-calendar`、`feature/li-posture` 或 `feature/yuan-integration`。分支名描述本次工作即可。
2. 尽量提前分配要修改的文件，避免三个人同时改同一份大型组件或学校正文。
3. 修改后提交，推到自己的分支，在 GitHub 打开 Pull Request，说明改了什么、为什么以及如何验证。请另一名组员查看后再合并到 `main`。
4. 合并后更新自己的 `main`。保留旧方案和已交付版本；新学校文件放具名的新副本。实际完成的工作写入 [work-log.md](work-log.md)，当前交接写入 [handoff.md](handoff.md)。

终端示例，从仓库根目录开始：

```sh
git switch main
git pull --ff-only
git switch -c feature/xu-calendar
# 完成修改后，添加本次实际变更的文件
git add desk-companion/frontend/src
git commit -m "Improve calendar interaction"
git push -u origin feature/xu-calendar
```

PR 流程是协作约定，当前没有声称已启用付费分支保护或强制审批。提交前用 `git status` 和 `git diff --staged` 核对内容；不要强制推送其他人的分支。

The #7–#14 code stack has been reviewed, fixed and merged; [review evidence](output/qa/2026-10-15-grok-review-merge/verification.md). The [original merge procedure](planning/2026-10-14/pr-stack-merge-order.md) is historical. After the 30 October all-PR review, #4/#15/#16 are closed as superseded with their branches retained. #5 remains draft/unmerged with reproduced migration and current-memory compatibility blockers. PR19 and64–69 are merged through [PR70](https://github.com/tantalum666/FYP/pull/70); [review/receipt](output/qa/2026-10-30-all-pr-review/verification.md). Hardware PR #17 was reviewed, repaired and merged on 26 October; see the [current handoff](handoff.md). The 2026-10-28 owner-authorized integration merged Grok PRs20–59 and the Alice/mobile/Omni baseline#60 through PR61; all41 source PRs are merged. Exact receipts are in the current handoff. Older per-slice merge restrictions do not replace that explicit authorization.

**只做本地验证，不使用 GitHub CI。**按变更运行相关检查，不需要配置或修复 Actions／账户额度。修改应用业务或界面时，从 `desk-companion/` 运行：

```sh
uv run --no-sync pytest -q
uv run --no-sync ruff check backend scripts tests
cd frontend
npm run build
npm test
```

纯文档修改核对链接、身份、日期和输出版本；DOCX / PDF 修改按项目流程逐页渲染检查。实际硬件、服务器和第三方账号需要独立的验证记录。

## 哪些内容共享，哪些留在本机

| 内容 | 位置与处理 |
|---|---|
| 当前软件及可复现依赖版本 | `desk-companion/`、锁文件、配置示例 |
| 需求、研究、决定及工作记录 | `planning/`、`research/`、根目录 Markdown |
| 学校输入原件及组员原始方案 | `inputs/`；[来源与完整性清单](inputs/manifest.json) |
| Proposal、Log sheet、询价、品牌及源码交付包 | `output/`、`outputs/`；保留各版 |
| 设计、参考资料、字体许可及验证证据 | `design/desk-companion/`、`output/qa/`；退役材料随Senplate集中归档 |
| 已退役的 Senplate 工程 | [archive/senplate](archive/senplate/README.md)；包含旧代码、设计、研究、学校版本和QA，不作为当前产品要求 |
| 密钥、登录密码、配对令牌、运行数据库 | `.runtime/`、`.env` 等，Git 忽略；各人本机配置 |
| 已安装依赖、工具缓存、构建结果 | `node_modules/`、`.venv/`、`python_packages/` 等；从锁文件重建 |

学校文件包含组员资料，仓库保持私人。第三方字体、论文、截图、商标参考和框架各自保留原许可与来源；私人协作上传不等于取得对外再分发授权，仓库没有给全部内容附加统一开源许可。

上传前可使用 Gitleaks 8.25+ 检查。项目配置只排除经核实的 SHA256 完整性值、公开 Figma 文件 ID 和一个 Swift 存储键的误报，不跳过整个研究或 QA 目录：

```sh
gitleaks git --pre-commit --staged --redact --max-archive-depth 2
```

## 2026-10-28 maintenance convention

Follow the latest AGENTS focused-reading workflow. Keep UI composition, data lifecycle, business edits and provider protocols separate; share existing services instead of copying state machines. Important verified milestones should be committed/pushed on a dedicated branch and reviewed through a PR. Source/asset/secret checks and remote readback are distinct from merging/deploying.

The current application includes the Alice/web/phone and unified conversation checkpoint. Local development may explicitly use`DESK_LOCAL_PREVIEW=1 ./scripts/dev.sh`; default authentication and real-device HTTPS/pairing remain. Run backend lint/tests and frontend tests/build locally with models and executors disabled. GitHub Actions is not used. Native touch, live models and hardware need independent evidence.
