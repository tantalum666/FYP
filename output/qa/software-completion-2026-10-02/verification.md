# Group 2 软件集中完成验证

任务开始2026-10-02，跨日继续至2026-10-03；同一工作轮，未因日期或上下文恢复重启全库阅读。

## 开工、保留与范围

- [阅读记录](reading-record.json)：111份项目自有Markdown，10623行，77块，截断补读完成，coverage_verified=true。
- [保护前清单](protected-before.json)／[保护后核对](protected-after.json)：107项旧代码、学校交付及组员身份文件，changed=[]。
- 本轮源码修改前副本在`before/`；主库SQLite备份在私有`.runtime/backups/software-before-20261002.sqlite3`。
- 主库仍为7条原有sample事项。浏览器／模拟器使用独立`.runtime/completion-qa/`，其新增及导入均为明确的测试数据。
- 没有真实音视频采集、付费语音调用、电机动作、学校服务器登录、外部联系或Moodle提交。

## 自动化与构建

| 检查 | 已观察结果 | 证据 |
|---|---|---|
| 后端业务／API／协议 | 84 passed，单个Starlette上游弃用提示 | [完整结果](backend-tests.txt) |
| 前端日期／布局规则、音频重采样、占用合并、农历、缓存隐私 | 11 passed | [完整结果](frontend-tests.txt) |
| Ruff | 检查通过 | [结果](ruff.txt) |
| TypeScript／Vite | 生产构建成功 | [构建日志](frontend-build.txt) |
| npm依赖审计 | 0已报告漏洞；此前CLI间接uuid问题通过兼容覆盖处理 | [审计JSON](npm-audit-final.json) |
| iPhone＋WidgetKit＋App Intents | 本地模拟器签名构建成功、安装启动 | [最终构建](ios-final-build.log) |
| Linux启动文件 | 生成预览，bash语法检查通过；未在Pi安装 | `.runtime/linux-preview/`、[诊断](diagnostics.json) |

后端覆盖：原45项日历、姿态标定／可见性／持续窗口／复测／失联／来源、配对批准／撤销、输出过期／停机／去重、服务端隐私、助理确认／到期／版本、天气缓存／安静时段、ICS／备份／分享、实时协议、OAuth、手机投影／提醒上限、镜像侧向、活动复测及具体发生项审阅日期。

没有用仅返回200的接口或已排队动作冒充物理成功。新的设备反馈工具返回queued，测试明确断言physical_completion_confirmed=false。

## 模型和评价

- [MediaPipe冒烟](pose-runtime-smoke.json)：Mac0.10.35、合成空帧、0人；推理实际运行，未开相机。1.0.1在Mac的CPU图问题先被复现后固定版本。
- [唤醒冒烟](wake-runtime-smoke.json)：官方中英3M int8模型处理4秒合成静音，未检测到唤醒；未开麦克风。修复缺失sherpa-onnx-core的安装依赖。
- [合成评价](synthetic-evaluation.json)：404评分帧，来源为synthetic，个人设置帧排除；分组泄漏会拒绝。其F1／提示统计仅用于评价器代码验证。
- Linux选择具有aarch64发行包的MediaPipe1.0.1，未据wheel存在宣称已运行或达到Pi性能。

## 浏览器实际操作

| 流程 | 实际检查 |
|---|---|
| 助理 | 输入Tomorrow 15:00–16:00 QA project review，生成草稿，确认后显示Saved，并在同一日历出现；语音未配置按钮保持禁用 |
| 姿态 | 开启隔离回放，依次点三项Start，保存reference／forward／side；持续前倾显示提示及still_deviated；另一次合成回到参考得到adjusted；停流后显示无法判断 |
| 配对 | Chrome拥有者产生单次码，iPhone输入后两边核对3757，拥有者批准；手机读取同一API日历，停止并重新启动App后仍可进入 |
| 天气／双历 | 选择香港、公众假期和农历，读取真实公开天气；再次打开并连续保存两次偏好成功 |
| 文件导入 | 上传[合成ICS](calendar-import-fixture.ics)，预览1项，确认新增1项；界面明确UTC时区与范围展开规则 |
| 分享 | 独立IAB无账号打开忙闲链接，只见合并区间，没有私人标题；拥有者撤销后重载显示不可用 |
| 备份 | 网页改为实际附件链接。IAB下载成功，文件位于用户Downloads，校验包含9项测试事件且无认证表；用该文件做恢复预览，再应用0新增／0更新／9保留 |
| 常亮屏 | 1024×600夜间、中文日间、720×1280竖屏可读，无主导航栏；闲置后回到显示，操作入口按设备单独展开 |
| iPhone | 原生桥／Keychain实际配对；修复SceneDelegate未使用自定义桥与安全区、输入框字号导致的自动缩放；观察跨午夜日期切换 |

Chrome扩展会话未返回下载事件，未据超时声明文件已保存，也未绕过内部页面访问策略。之后通过应用本身的标准附件链接，在IAB实际取得文件；[下载证据](browser-download-check.json)、[附件响应](http-export-check.json)、[已下载副本](browser-downloaded-backup.json)分别保留。

[集成状态](integration-status.json)记录三项标定、adjusted结果、1个配对终端、current天气，以及尚未配置的语音和Google。所有这些都来自隔离测试库。

## iOS系统功能边界

签名为本地Simulator用途，不是Apple真机／App Store发行签名。Widget扩展和两条App Intents已编译，App Group实际存在，原生已写入3项经过隐私处理的摘要；[共享容器核对](widget-storage-check.json)验证私人标题为空、没有通知载荷混入Widget。

没有替使用者授予通知／麦克风权限，未宣称通知已送达、Widget系统刷新频率或Siri口述触发已经验收。iPhone实际配对和重启进入有截图，系统交付条件在操作说明中列明。

## 截图

- [设备夜间1024×600](device-night-1024x600.jpg)
- [设备中文日间1024×600](device-day-zh-1024x600.jpg)
- [设备竖屏720×1280](device-portrait-720x1280.jpg)
- [iPhone配对后](iphone-paired.jpg)
- [iPhone重启后及跨午夜](iphone-after-restart.jpg)
- [配对管理](paired-controller-desktop.jpg)
- [只读忙闲分享](busy-share.jpg)
- [备份恢复](backup-restore.jpg)
- [姿态复测记录](posture-reassessment.jpg)

部分截图含测试配对码或测试安排，均来自隔离环境；配对码已单次使用或过期，测试分享已撤销。常亮屏的Private event来自开启观察但未取得有效新观察后的隐私投影，不是事件丢失。

## 本轮发现并修复的实质问题

1. MediaPipe1.0.1 Mac CPU图故障、sherpa运行库缺失、Xcode框架下载阻塞；分别固定已运行版本、补明确依赖、验证官方框架SHA并本地引用。
2. 44.1/48kHz音频分块的重采样相位偏移；修复跨块余量，两个速率均检验2秒输出采样数。
3. 相机失去帧时自动关闭并重开；不接受缺失／非有限关键点；增加模型文件校验。
4. 偏好保存回执的operation_id／revision误混入下一次表单；仅保留业务字段并实际连续保存回归。
5. 日程修改／删除审阅显示系列首日而非所选发生项；改为解析该发生项和例外，增加测试。
6. 常亮屏断连可能继续显示上次私人字段；增加本地过期投影与针对性测试。
7. 停止实体反馈可能被一般待保存请求阻挡；停止使用独立请求通道，后端先锁定再写记录。
8. 原生桥注册、安全区、输入自动缩放、导出附件和开发热更新根节点收尾。

## 外部条件

真实机位、人工标签、目标Pi、实际麦克风／AEC、机械限位／电源／停机、光学模块、语音服务凭据／费用授权、Google本人OAuth及Apple真机签名仍未取得。本轮没有把这些写成完成。下一步为在取得条件后执行操作说明和评价协议中的真实闭环测试。

## 收尾

- 主8831同源设备页与管理日历已启动、登录、显示原7项示例，并在IAB保留入口；新管理页面控制台没有新增warn/error。
- [主设备页](main-device-deliverable.jpg)、[主日历](main-calendar-deliverable.jpg)、[独立角色输出](avatar-output.jpg)补充实际产物。
- [源码包清单](source-package.json)记录148个源码／配置／文档文件；压缩包不含运行秘密、依赖目录、模型二进制和原始媒体。
- [内部链接检查](local-link-check.json)核对88个当前规范链接，无缺失。
- 已同步product、handoff、decision-log、work-log、S1–S10计划、设备规范、README、操作／架构／评价与依赖说明。9月29日批次计划已明确标为历史，不把旧下一步和当前实现混用。
