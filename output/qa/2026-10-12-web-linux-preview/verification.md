# Group 2 · Web／Linux界面试用 QA

2026-10-12，Asia/Hong_Kong。用户要求现在查看／测试Web和Linux版，期间追问的测试账号密码已在聊天回答；本报告不保存密码、cookie或token。

## 环境与流程

- Web：[localhost:8832](http://localhost:8832/)；独立常亮屏：[DeviceApp](http://localhost:8832/?surface=device)。服务绑定127.0.0.1:8832、PID89265／exec session15293，独立运行目录为`desk-companion/.runtime/user-preview-20261012`，保留供用户试用。
- `npm run build`先构建现有版本，修复后再构建；TypeScript／Vite均通过，已有约1.10MB 3D延迟块提示保留。
- Browser插件／browser skill未列出；依照现有工具指令使用内置CUA的文档化Playwright／tab级CDP，不另装或使用外部自动化。
- 流程：Web登录→Add→保存虚构日程→Event saved→Linux近期安排显示同一条；Touch to manage→管理面板→Back to display；修复后周日选择→日视图日期正确。

## 页面与交互结果

| 检查 | 结果 |
|---|---|
| 正确标题／URL、正文与框架覆盖 | Web／DeviceApp为Desk Companion，有实质内容，无框架覆盖 |
| Web1280×800 | 日程已保存、首页／近期安排显示；小月历修复后七列完整、周日可选 |
| 窄屏390×844 | 主要内容／底部导航可读，scrollWidth390，无水平溢出 |
| DeviceApp1024×600 | 大时钟／月历／近期事项可读，scrollWidth1024；触摸管理及返回正常 |
| 控制台 | 实测相关error／warn为0 |
| 数据与服务 | 健康端点ok、四后台循环ready；测试事件只保存一次，原主工作区四文件hash一致 |

[browser-checks](browser-checks.json)保留DOM范围、交互和尺寸；[runtime-validation](runtime-validation.json)保留服务、构建产物图片尺寸／hash及数据保护。当前为mac_local上预览Linux目标界面，未进行Pi实装／触控／GPU／温度或真实音视频测试。真实文字／语音未配置、后台AI关闭；未启动相机／音频／输出代理。测试目录可用专用笔记审批和回放入口。

## 修复与检查过程

`.mini-grid`可用宽度160px、固定28px按钮七列总scroll202px，侧栏client212px／scroll228px，最右列被裁切。七列改为`minmax(0,1fr)`，日期按钮使用`min(28px,100%)`及`min-width:0`。修后grid scroll160px／sidebar scroll212px，最右列完全在边界内，实际周日点选通过。变更仅为[styles.css](../../../desk-companion/frontend/src/styles.css)三处布局声明；没有增加镜像实现测试，使用构建和实际渲染验证。

首次高层截图裁切未匹配模拟宽度，后用tab级CDP明确clip，PNG尺寸读回1280×800／1024×600／390×844。可见Web标签页被手动切换至Device后，另建隐藏检查页，不干扰用户页。AX将pressed按钮显示成checkbox，基于DOM实际button语义完成日期检查；隐私select精确label未匹配，用可匹配label后保存成功。以上失败未计为通过。尺寸覆盖均清除，隐藏检查页关闭，两用户标签页保留。

## 证据与保留

[修复前Web](web-before-mini-calendar.png)／[修复后Web](web-preview.png)／[窄屏](web-mobile-preview.png)／[Linux常亮屏](linux-display-preview.png)。原主库保护基线在[main-runtime-before](main-runtime-before.json)，只保存路径／hash，不保存内容或凭据；阅读继承及本轮补读见[reading-record](reading-record.json)。

更新product、软件README、决定／工作日志和handoff；[收尾检查](closeout-validation.json)核对旧资产、原主工作区、内部链接与组号。服务保留给用户，不自动创建定时任务或跨轮后台工作；用户可以在测试工作区自行增改事项。未调用付费模型、启用设备权限、进行硬件动作、联系他人或提交学校文件。
