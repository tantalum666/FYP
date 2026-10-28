# Desk Companion 十分钟离线演示

日期：2026-10-27。这是 Group 2 的讲解顺序，使用本机假文字适配器。它不调用 Qwen、Gemini 或其他付费接口，也不能当作真实使用效果或商业收益。

界面默认是英文。下文按钮名用界面原文。需要中文时，登录页右上角把 Language 改成「简体中文」。

## 启动

在 `desk-companion/` 目录，依赖已经按 README 安装之后：

```sh
export DESK_RUNTIME_DIR="$PWD/.demo-runtime"
export DESK_TEXT_PROVIDER=fake
export DESK_COMPUTER_ENABLED=1
unset DESK_TEXT_API_KEY DESK_TEXT_ENDPOINT DESK_TEXT_BACKGROUND
.venv/bin/python scripts/seed_demo.py --refresh
./scripts/dev.sh
```

打开 http://127.0.0.1:5190/ 。账号是 `owner`。密码在 `.demo-runtime/credentials.json`，不要把密码投到屏幕上。开发脚本若打印了密码文件路径，以 `DESK_RUNTIME_DIR` 为准。

`--refresh` 会清掉这个演示目录并重新生成两条待批准作业。作业的批准窗口是五分钟，过期后界面会显示到期。电脑作业那一分钟若已经过期，在 Assistant 里用 Prepare a note 再准备一条，不要把过期说成执行失败。

侧栏若出现 Example calendar／含示例日程，主动说明这些是示例数据。

## 0:00–1:00 登录并说明边界

用 owner 登录。说明三件事：文字回复来自离线假适配器；笔记只写运行目录里的专用笔记夹；安静时段推迟的是事务检查，不是屏幕上的日程提醒。

## 1:00–3:00 提醒

点右上角铃铛，Open reminders。列表标题是 Reminders。应能看到 **FYP presentation**，状态是 Due。它开始前约八分钟，提醒设为提前十分钟，所以现在已经到期。

点 Acknowledge，说明这只是确认已看到，不删除日程。今天的日历上仍有 FYP presentation，稍后还有 Project discussion。

## 3:00–5:30 更正记忆

侧栏打开 Memory。已有一条事实：`The owner studies at CUHK.` 这是故意写错的演示事实。

打开 Assistant（侧栏 Device 里的 Assistant，或右上角 Assistant）。在 Your request 输入这句后点 Send：

```text
Please correct my memory: I study at CityU, not CUHK.
```

回复应说明更正尚未保存，并出现草稿。点 Confirm & save。回到 Memory，事实变为 `The owner studies at CityU.` 点 Correct 可以再改一次，用来说明拥有者直接编辑也不经过模型。不要在这一步打开语音。

假适配器只认这句里的 CityU／香港城市大学，以及演示稿里的另外两句。它不是通用模型。

## 5:30–8:30 电脑作业：批准、读回、取消

仍在 Assistant 页面，向下找到 Computer jobs。应有两条 Needs your approval：

1. **FYP demo note**。展开 Review exact text，读出全文。点 Approve this job。等待状态变为 Verified，并出现 Independent read-back matched。说明读回是写入之后的独立核对，作业成功不等于事务完成。
2. **Scratch note**。不要批准。点 Cancel job。状态应为 Cancelled before execution。说明取消发生在写入之前，没有文件被删除，因为文件还没写出来。

若笔记执行显示 Local note execution is disabled，说明启动服务时没有 `DESK_COMPUTER_ENABLED=1`。停掉脚本，带上变量重新启动。不要对听众的真实目录做这个演示。

也可以在 Your request 发送 `Please save a demo note.` 再准备一条新的待批准笔记。这仍然不访问网络。

## 8:30–10:00 安静时段

侧栏打开 Tasks，选中 Prepare the FYP demonstration。下次检查被种子脚本标成已经到期，然后由产品自己的安静时段逻辑推迟。演示目录把安静时段设成当天 00:00–23:59，因此不论讲解发生在几点，Next check-in 都会落在当天 23:59 附近，而不是立刻弹出跟进。

打开 Device，再打开 Calendar & companion。Reminders & quiet hours 里 Use quiet hours 已勾选，From 是 00:00，Until 是 23:59。读出页面上的句子：安静时段只暂停声音，不隐藏日历提醒。刚才的铃铛提醒已经证明这一点。

若时间允许，把 Until 改回 07:00、From 改回 22:00，点保存，说明这才是产品默认值。演示目录可以留着；不要把这组时间写进日常使用的 `.runtime/`。

## 结束时说明

- 没有调用付费文字接口，也没有测量减损、准确率或时延。
- 假适配器的三句演示语见上文。其他句子会得到固定的离线说明。
- 人格、语音和硬件不在这十分钟里。
