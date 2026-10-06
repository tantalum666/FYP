# 受限电脑作业：运行、验收与边界

2026-10-06，Group 2。已实现的范围是**本机专用笔记文件的真实保存与独立读回**；通用电脑操作仍待接入。软件在谁的主机运行，文件就写在该主机的运行目录，不能把Pi本机保存称为远端PC控制。

## 在隔离目录试运行

从`desk-companion/`执行，依赖安装沿用README，不需要模型密钥：

```sh
uv sync --frozen
cd frontend
npm ci
npm run build
cd ..
DESK_RUNTIME_DIR="$PWD/.runtime/computer-demo" DESK_COMPUTER_ENABLED=1 \
  .venv/bin/uvicorn desk.app:create_app --factory --app-dir backend \
  --host 127.0.0.1 --port 8831 --workers 1 --no-access-log
```

打开`http://127.0.0.1:8831/`，以owner登录。新目录首次口令由服务生成，保存在该目录的`credentials.json`；不要上传该文件。打开助理，再找到Computer jobs：

1. Prepare a note：输入虚构标题及完整文本，准备后还没有写入文件
2. 核对全文及显示的生成文件名，选择Approve this job
3. 后台保存到`computer-demo/computer-notes/<作业ID>.txt`，独立读回一致后显示Verified、字节数及SHA256
4. 文件内容即批准的文本，标题用于作业识别，不额外写入文件。可用系统文件工具另行读取核对
5. Prepare another verification创建只读核验意图，仍需拥有者批准；不会修复、替换或覆盖文件

本地规则也接受`Save note: fictional text`／`保存笔记：虚构文本`，返回待审作业；自然语言模型默认关闭。关联事务入口使用当前task_id／version，保存文件不自动完成事务。

## 失败与恢复

- 待批准5分钟、批准后60秒期限。过期或旧版本不能执行
- 未开始时取消不会创建文件；已经开始时先显示Stopping，最终可能是已取消、已核验或结果未知
- 取消不会删除已有文件。不要把软件取消当作回滚或物理停机
- unknown：执行不自动重试，选Check existing result进行只读核验。服务重启和写后回执异常都保留此路径
- 如果文件缺失、被修改、目录不安全或核验仍不可用，保持unknown；确认原因后再准备新意图，不反复盲点批准
- 相同操作ID重试去重，不同参数拒绝。UI保留未知请求恢复入口，恢复旧请求不会清掉另一个任务的未提交笔记
- 状态读取断开／陈旧时禁止批准；取消不依赖普通保存队列。已批准作业保存在服务端，关闭页面不会删除它

## 容量、隐私与未完成范围

最多1000项作业，待审／排队合计最多20项；列表优先未解决记录，最多200条。未提供历史归档／删除UI，达到上限需后续加入明确的保留策略，不能直接删数据库。该能力属于单拥有者原型，不是多租户服务。

拥有者审阅接口显示全文，模型状态工具仅返回状态和校验元数据；不自动把现有文件内容传到云模型。不记录原始语音，笔记内容在本机文件和持久意图中保存。业务JSON导出目前不包含作业或笔记；不要把它当完整主机备份。真实主机的私有运行目录与备份都应限制访问。

此适配器没有任意文件读取、浏览器／应用控制、屏幕观察、shell、覆盖或删除工具。LCU、远端配对PC执行服务、目标应用／origin强制限制、真实会话恢复、长期记忆编辑管理尚未完成。实际权限、模型预算、硬件及目标任务需另行确认。

## 可复现自动检查

```sh
uv run --no-sync pytest -q
uv run --no-sync ruff check backend scripts tests
cd frontend
npm test
npm run build
```

自动检查使用临时目录、虚构任务与模拟提供商；没有付费模型、LCU、真实GUI或硬件动作。[本轮证据](../../output/qa/software-completion-2026-10-06/verification.md)如实区分通过和未运行。