# Group 2 Current Handoff

更新：2026-10-12后续。当前：**Web与Linux常亮屏界面已启动，可在本机独立测试工作区试用；小月历裁切已修复并复核。** 用户刚追问的测试账号密码已在聊天回答，不写入仓库。

## 当前产物与证据

- 用户入口：[Web管理页](http://localhost:8832/)／[Linux常亮屏界面](http://localhost:8832/?surface=device)。运行在Mac，绑定`127.0.0.1:8832`，独立目录`desk-companion/.runtime/user-preview-20261012`，当前服务PID89265、exec session15293保留运行；只用于本机试用，不是Pi实装或公网部署。
- 本周虚构示例与一条Web UI保存的测试日程；两页共享显示、Linux触摸管理／返回、桌面1280×800／窄屏390×844／设备1024×600通过。侧栏月历160px被202px日期列撑开的问题已修复，周日可选；构建通过、相关控制台错误0。[本轮QA](output/qa/2026-10-12-web-linux-preview/verification.md)保留截图／DOM／运行及数据保护证据。
- 测试目录仅启用需本人逐项批准的专用笔记和回放入口；真实文字／语音AI未配置，后台AI关闭，未启动相机／音频／输出代理。原主工作区四文件、学校及旧角色资产保持；用户标签页保留，临时检查页已关闭、尺寸覆盖清除。
- [17模块功能／待办](planning/2026-10-12/software-function-inventory.md)、[九套服装包](output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)与[A1六视角／四细节](design/desk-companion/characters/2026-10-12-a1-turnaround-details/README.md)保留。前阶段保存／清单及QA已推送至`ff3df6c`，[PR #4](https://github.com/tantalum666/FYP/pull/4)开放，main仍`ccfac48`；本轮仅增加布局修复与试用记录。

## 未完成与保留

待开发：指定应用／远端PC执行器及权限／恢复、长期个人记忆查看／纠正／删除、作业归档／完整业务导出、A1原创VRM／绑定、RIG专用适配与采用相应音频路径时的角色音量桥。LCU和清洁模块仍为候选；逐音素、CI等增强不自动变成本版必做。

待真实验证：语音／唤醒／AEC／费用、真人姿态、Pi并发与连续运行、iPhone签名／系统行为、Google本人OAuth、显示光学和机械停机／动作。[第2份v5日志](planning/2026-10-11/logsheet-2-review.md)、学校原件和所有旧资产保持；本轮未核实学校提交状态。

## 唯一下一步

**用户在两个测试入口试用日历、事务和设备界面并反馈具体问题。** 后续开发仍按17模块清单收敛真实PC任务／服务和目标设备验证，A1制作参考继续保留。
