# 受限电脑作业：运行、验收与边界

2026-10-12，Group 2。已实现**本机专用笔记文件的真实保存与独立读回**，新增默认关闭的**独立演示应用 API 创建记录与独立读回**。通用电脑操作仍待接入。软件在谁的主机运行，笔记就写在该主机的运行目录；应用适配器只连接同一主机上由操作者指定的演示应用，不能称为远端PC或任意桌面控制。

## 在隔离目录试运行

从`desk-companion/`执行，首次依赖安装沿用README，不需要模型密钥。已有环境跳过依赖同步，避免移除已安装的可选视觉／音频包：

```sh
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

拥有者可见私人上下文时，审阅接口显示全文；启用隐藏私人资料后，列表和详情只返回状态／核验元数据，准备和批准返回403，取消与只读对账仍可用。重新显示不会删除已保存意图。模型状态工具仅返回状态和校验元数据；不自动把现有文件内容传到云模型。不记录原始语音，笔记内容在本机文件和持久意图中保存。业务JSON导出目前不包含作业或笔记；不要把它当完整主机备份。真实主机的私有运行目录与备份都应限制访问。

笔记适配器没有任意文件读取、浏览器控制、屏幕观察、shell、覆盖或删除工具。新增应用适配器只有下述固定应用 API，强制限制 origin／应用实例／动作；它不提供 GUI 或第三方软件控制。LCU、远端配对PC执行服务及通用桌面会话恢复仍未完成。个人上下文能力另见当前架构与相关契约，不由本作业功能推断完成。实际权限、模型预算、硬件及目标任务需另行确认。

## 独立应用 API 工作流（默认关闭）

新增 `create_record`／`verify_record`，旧 `save_note`／`verify_note` 保持原有文件和核验语义。固定动作由代码注册表映射到执行器；模型不能注册执行器、传任意URL／文件路径／JavaScript／shell，也不能批准。`DESK_COMPUTER_ENABLED=1`仍是总开关；只有额外明确配置`DESK_DEMO_APP_ORIGIN`才启用记录动作。

在另一个终端启动独立应用，指定未占用的非特权端口与新隔离目录，只用虚构数据：

```sh
cd desk-companion
PYTHONPATH=backend .venv/bin/python -m desk.demo_application \
  --port 8840 --directory "$PWD/.runtime/demo-records"
```

演示应用固定绑定`127.0.0.1`；打开`http://127.0.0.1:8840/`可查看实际保存记录，刷新读取最新状态。没有浏览器自动化，页面仅用于观察实际应用存储。它是单机演示服务，没有生产多用户认证；Host／Origin／自定义请求头阻挡普通跨站写入，但不防同一主机上的恶意进程。不要公开绑定、放真实个人资料或当作公开服务部署。

另以原启动方式运行Companion，只在该进程明确增加：

```sh
DESK_RUNTIME_DIR="$PWD/.runtime/computer-demo" DESK_COMPUTER_ENABLED=1 \
  DESK_DEMO_APP_ORIGIN=http://127.0.0.1:8840 \
  .venv/bin/uvicorn desk.app:create_app --factory --app-dir backend \
  --host 127.0.0.1 --port 8831 --workers 1 --no-access-log
```

端口必须为1024–65535且拼写规范。`localhost`、IPv6、其他IP、HTTPS、默认／前导零端口、路径、用户名、查询或片段均拒绝；不会解析DNS、跟随重定向或继承系统代理。配置错误会启动失败，而不是悄悄使用另一个目标。

执行契约：

1. 准备时只GET目标身份。待审完整意图绑定动作、生成记录ID、标题／全文、SHA256、固定origin、持久应用实例ID、执行器身份／范围、适配器及数据版本，以及关联事务版本
2. 拥有者批准准确版本和完整意图hash；执行前再次检查意图、范围、应用实例和最后的取消／期限栅栏。更换应用数据库实例或origin使旧意图失效
3. 仅对固定`POST /api/records`执行一次。应用以生成ID保存不可变记录；相同ID与不同参数冲突，不覆盖。服务端接收回执不等于完成
4. 单独`GET /api/records/<生成ID>`读取已存记录，验证ID、应用实例、原批准意图hash、标题hash、内容hash／字节数、执行器／范围／版本。结果中的`.json`是记录标识，不是可由模型指定的本机文件路径
5. 回执丢失、进程崩溃或核验失败保持unknown；只读对账绝不再POST。取消发生在已保存之后，最终仍可以真实显示Verified和已请求取消；不声称回滚。独立核验意图继续使用原记录标题及原批准hash，不把核验说明当成新标题

网络每阶段超时2秒，响应体最多64KB，并在流式读取中限制总读取预算；停止不能撤回已经发送的HTTP请求。没有自动写重试、外部凭据、支付、第三方应用、通用鼠标键盘、Pi／用户Mac控制或物理效果。独立应用每库最多1000条，页面显示最近100条，不提供删除或自动归档；业务备份不包含该演示数据库。

可复现独立进程检查（指定未占用测试端口）：

```sh
.venv/bin/python scripts/check_application_executor.py --port 18840 \
  --output ../output/qa/2026-10-12-agent-kernel/application-http-integration.json
.venv/bin/pytest -q tests/test_computer_jobs.py tests/test_application_jobs.py
```

检查器启动自己的独立应用子进程、只用临时目录和虚构Unicode文本，验证批准前零记录、HTTP创建后直接SQLite读回、重复准备仍一条记录及真实HTML读回；结束停止自己的服务并移除临时数据。它不是GUI点击或真人／付费服务验收。

## 可复现自动检查

```sh
uv run --no-sync pytest -q
uv run --no-sync ruff check backend scripts tests
cd frontend
npm test
npm run build
```

自动检查使用临时目录、虚构任务与模拟提供商；没有付费模型、LCU、真实GUI或硬件动作。[10月6日云端证据](../../output/qa/software-completion-2026-10-06/verification.md)保留当时浏览器未完成的限制；[10月9日本地整合验证](../../output/qa/2026-10-09-dot-integration/verification.md)补充实际浏览器保存、取消、只读对账、未知请求恢复及响应式检查。
