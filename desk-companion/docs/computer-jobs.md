# 受限电脑作业：运行、验收与边界

2026-10-31：保留真实应用和原有队列；执行前核对批准意图哈希，隐藏私人信息时只返回作业状态且拒绝新批准，取消仍可用。旧 PR5 假记录应用按已被取代处理，未进入动作目录；[整合契约](pr5-integration.md)。
<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

2026-10-30，Group 2。原有两件**同一作业契约**上的本机写入：专用笔记目录，以及拥有者指定的一个真实文件夹。两者都保留完整意图授权、独立读回和取消；现另加入受限Linux编辑器→浏览器流程。通用电脑操作、任意路径和 shell 仍未接入。软件在谁的主机运行，文件就写在该主机上，不能把本机保存称为远端 PC 控制。

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

打开`http://127.0.0.1:8831/`，以owner登录。新目录首次口令由服务生成，保存在该目录的`credentials.json`；不要上传该文件。默认Ask first模式下，打开助理直接输入文件请求；也可在More → File activity手动准备：

1. Prepare a note：输入虚构标题及完整文本，准备后还没有写入文件
2. 在对话卡片核对全文与目标，选择Allow once；文件名／SHA等信息在Details
3. 后台保存到`computer-demo/computer-notes/<作业ID>.txt`，独立读回一致后显示Verified、字节数及SHA256
4. 文件内容即批准的文本，标题用于作业识别，不额外写入文件。可用系统文件工具另行读取核对
5. Check the file again创建只读核验意图；这一手动准备入口仍保留单次批准；不会修复、替换或覆盖文件

本地规则也接受`Save note: fictional text`／`保存笔记：虚构文本`，返回待审作业；自然语言模型默认关闭。关联事务入口使用当前task_id／version，保存文件不自动完成事务。

## 失败与恢复

- 待批准5分钟、批准后60秒期限。过期或旧版本不能执行。这两个期限都是 `Store.clock` 的绝对时间；准备、批准、过期和执行共用这一时钟，未注入时才用墙上时钟。模拟重启必须把原时钟传给新进程，不能改取真实日期，否则批准后的 60 秒期限会被判过期
- 未开始时取消不会创建文件；已经开始时先显示Stopping，最终可能是已取消、已核验或结果未知
- 取消不会删除已有文件。不要把软件取消当作回滚或物理停机
- unknown：执行不自动重试，选Check existing result进行只读核验。服务重启和写后回执异常都保留此路径
- 如果文件缺失、被修改、目录不安全或核验仍不可用，保持unknown；确认原因后再准备新意图，不反复盲点批准
- 卡片直接写出读回原因：全文不一致、文件不存在、无法安全读取，或暂时不能读回。路径指纹变化时，下一步是按当前文件夹重新准备，原卡片保留为记录。取消且未写入时写明没有新文件。文件夹作业显示绑定指纹前 12 位
- 笔记和文件夹动作登记在 `JobService._bindings`。以后若授权一个有边界的应用动作，在这里增加一行，仍走批准、独立读回和取消。不另开第二套作业队列。
- 相同操作ID重试去重，不同参数拒绝。UI保留未知请求恢复入口，恢复旧请求不会清掉另一个任务的未提交笔记
- 状态读取断开／陈旧时禁止批准；取消不依赖普通保存队列。已批准作业保存在服务端，关闭页面不会删除它

## 拥有者指定的一个文件夹

笔记适配器仍由 `DESK_COMPUTER_ENABLED=1` 打开，目录固定在运行目录的 `computer-notes/`。文件夹适配器不看这个开关。拥有者在 File activity 的文件夹设置里填写名称和**绝对路径**后，服务才接受 `save_folder_file`。未指定时准备作业返回 `FOLDER_NOT_CONFIGURED`。

路径必须是已经存在的真实目录，不能是符号链接，也不能是运行目录本身、它的上级或它里面的子目录。这样不会把文件写到 SQLite、凭据或专用笔记目录旁边。模型工具没有 path 字段；作业记录里只有文件夹名称和路径指纹，不保存路径字符串。配对显示屏不能改这个目录。

批准绑定当时的全文、标题、文件夹名称和路径指纹。批准前如果改了目录或清除了指定，作业返回 `COMPUTER_SCOPE_CHANGED`，两个目录都不会被写入。执行和核验都逐级通过目录句柄打开已批准的绝对路径，任一级变成符号链接都会拒绝，不只检查最后一级。写入仍是新建 `<作业ID>.txt`，已有同名文件保持不变。读回比较字节数和 SHA-256。取消不删除已写文件。核验是另一项需要批准的只读作业，不会把被改过的文件改回去。

本地规则：`Save to folder: …`／`保存到文件夹：…` 只准备待审作业。`Save note:`／`保存笔记：` 仍走专用笔记目录。

## 容量、隐私与未完成范围

最多1000项作业，待审／排队合计最多20项；列表优先未解决记录，最多200条。未提供历史归档／删除UI，达到上限需后续加入明确的保留策略，不能直接删数据库。该能力属于单拥有者原型，不是多租户服务。

拥有者审阅接口显示全文，模型状态工具仅返回状态和校验元数据；不自动把现有文件内容传到云模型。不记录原始语音，笔记内容在本机文件和持久意图中保存。业务 JSON 备份包含作业记录、最近事件和已指定文件夹的路径。运行令牌不在里面。仍在运行的作业恢复为待审阅，不会自己继续执行。这仍不是整机镜像。真实主机的私有运行目录与备份都应限制访问。

这两个适配器都没有任意文件读取、浏览器／应用控制、屏幕观察、shell、覆盖或删除工具。拥有者指定的文件夹只证明「一个事先命名的目录」可以沿用同一作业契约，不等于已经能操作任意应用。LCU、远端配对 PC 执行服务、目标应用限制和真实会话恢复尚未完成。实际权限、模型预算、硬件及目标任务需另行确认。

## 可复现自动检查

```sh
uv run --no-sync pytest -q
uv run --no-sync ruff check backend scripts tests
cd frontend
npm test
npm run build
```

自动检查使用临时目录、虚构任务与模拟提供商；没有付费模型、LCU、真实GUI或硬件动作。[10月6日云端证据](../../output/qa/software-completion-2026-10-06/verification.md)保留当时浏览器未完成的限制；[10月9日本地整合验证](../../output/qa/2026-10-09-dot-integration/verification.md)补充实际浏览器保存、取消、只读对账、未知请求恢复及响应式检查。

## 2026-10-22：Linux编辑器 → 浏览器

DESK_LINUX_DESKTOP_ENABLED=1另行启用linux_note_preview／verify_linux_file。仍登记在同一个JobService；先准备全文、拥有者批准，再由本机Mousepad独立实例实际编辑并保存，Chromium独立配置打开固定本地文本。浏览器DOM和文件SHA都一致才返回apps_verified=[mousepad,chromium]。助理More中的作业表单可选该流程，或输入“编辑并预览：…”／“Editor preview: …”。模型不提交路径、URL、shell或JS，也无批准工具。

需要Linux图形会话、D-Bus、Mousepad、Chromium、python3-pyatspi和python3-websockets。GTK由AT-SPI输入／保存；浏览器使用新配置的随机回环调试端口，只读取固定文件的document.body.innerText。保留Chromium沙盒，不使用--no-sandbox；子进程不继承模型Key。执行35秒上限／取消只清理本次进程组。文件一旦预留，即使只留下空文件也按结果未知处理，不声称撤销写入。服务重启后没有两应用证据，文件相同也不能补写整个工作流成功。

隔离ARM64 Linux容器已实跑“API准备无副作用→拥有者批准→Mousepad保存→Chromium读DOM→SHA读回”。156字节中英文／字面脚本内容正确，脚本文本未执行。容器X11结果不是Pi默认Wayland结果。该流程不具备任意桌面截图、点击、网页登录或远端电脑能力。证据 (local historical material: `output/qa/2026-10-22-voice-linux-sd/verification.md`; not included in this checkpoint)／[Pi准备](pi5-first-boot.md)。

## 2026-10-28 备份恢复校验

业务备份可往返笔记、指定目录和 Linux 两类动作。导入先校验完整持久意图：action、task字段、artifact_id、executor／scope及内容摘要，不能把缺字段记录写入后才使管理页报错。非终态恢复为review，approved_by／run_id均不恢复；最终应用需要拥有者身份。

导入的目录也必须走 accept_owner_folder：存在、绝对、逐级无链接、位于运行树之外，并重新计算路径指纹。复制另一个目录的指纹不能复用旧批准；执行前再次检查实际路径摘要。原先已存在的作业／目录保留，不覆盖。不存在或不安全的跨主机目录必须先由拥有者在目标主机处理，不能放宽验证来“完成恢复”。

## 2026-10-29：对话内操作、权限与事务接续

文件请求在同一助理中显示内容、Allow once／Not now、运行／停止、核验结果；File activity作为次级历史与目录管理入口，共用JobActionCard及请求契约。详情中的Check the file again读取当前事务版本，允许已完成／取消事务的新只读核验；新写入及旧版本仍拒绝。所有本地文件命令，包括Editor preview／编辑并预览，使用同一个事务范围解析函数。

拥有者显式启用Full access后，新拥有者请求中的受支持作业可按该版本持续授权；旧待审作业不自动执行。排队自动作业在领取与执行前重核模式版本，撤回后返回PERMISSION_CHANGED。手动一次批准不被模式切换替代，已经写成的文件不声称回滚。具体范围见[权限契约](assistant-permissions.md)。

事务详情仅向拥有者界面补可读标题，模型／常亮投影仍不带完整请求。TaskJobs显示文件结果并接回Alice；文件成功不自动完成事务。隔离实际旅程包含丢HTTP200响应、真实API重启、同键恢复、独立SHA／mtime不变及手机记录／完成；见[当前QA](../../output/qa/2026-10-29-assistant-permissions/verification.md)。

## 2026-10-30 复杂任务门槛

现有固定编辑器／浏览器路径降为冒烟检查。用户要求的下一主任务是[演示准备包](../../planning/2026-10-30/complex-application-acceptance.md)，涉及真实浏览器资料核对、Calc公式与版本保存、Writer／PDF，以及日历／事务更新和中断恢复。测试输入和离线参考已准备，后续[真实应用轮](../../output/qa/2026-10-30-application-execution/verification.md)通过受控脚本执行。新增单独的 ApplicationJobInput 与原六种 JobInput 并列，复用同一批准／队列／版本／未知结果读回；[应用执行契约](application-execution.md)记录实际 Calc／Writer／PDF、暂存与版本文件、来源哈希、阶段投影和重启恢复。脚本通过不代表语音 Agent 自主完成，正常 HTTP 模型仍需任务接续工作。
