# Desk Companion B1 界面实施依据

2026-09-29建立；2026-09-30设备部分被[独立常亮规范](../../../planning/2026-09-30/device-display-spec.md)取代。本文电脑／手机设计仍有效。用户要求简洁并高级；以下两张内置ImageGen图片由助手在已授权开发范围内选作实施参考，不记为用户逐页批准。原图与实际提示词保存在本目录。

- [电脑日历](calendar-desktop.png)：1536×1024，完整周视图。
- [手机Today](today-mobile.png)：原生竖图，按390px逻辑宽度检查；图片的系统状态栏不在网页中伪造。

## 设计系统与组件

白色主画布、冷灰侧栏#F6F7F9、正文#242936、次字#747D91、边线#E8EAF0、强调#6266D9。事件使用淡紫／蓝／绿／桃四色，文字保持深色；不使用整页渐变、玻璃或食物项目标志。Inter可变字体，中文采用系统无衬线；字体随应用本地分发并附许可。

电脑侧栏约256px，主标题34px，常规正文14–16px，时间轴12px，主导航16px。手机页面边距20px，Today标题34px、时钟54px，触控目标至少44px；设备布局按实际尺寸再验。细边框8px圆角按钮，事件6px圆角，手机下一事项12px圆角。动效只用于弹层与状态，支持减少动效。

组件：AppShell／Sidebar／BottomNav、MiniMonth、CalendarToolbar、MonthGrid、TimeGrid、Agenda、TodayView、EventEditor、EventDetail、ReminderInbox、RecordsView、DeviceView、Login。App只组织状态与模块，不把整个应用写成一个巨大组件。

图标统一Lucide细线，导航Today用House、Calendar用CalendarDays、Records用FileText、Device用Monitor，设置Settings、语言Globe、日期ChevronLeft／Right、添加Plus；禁止用文字箭头替代图标。

## 允许的主屏文案与数据

品牌暂名Desk Companion；Today、Calendar、Records、Device、Settings；Day／Week／Month；New event、Today；Personal／Study；English／简体中文；时区名按真实设置显示。

参考数据仅供示例：Weekly planning、Project discussion、Design review、Study session、Team check-in、Reading、Mum's birthday，标题与时间依图片。实际使用显示用户保存的事项及真实日期；示例数据始终标Example calendar，不伪装用户真实日程。

## 必要状态与布局延伸

未登录需要本地登录；无事项提供清楚的添加入口；新建／编辑使用同样的字体、边线与留白，长表单在弹层内滚动。重复事项先选本次或整组操作，删除明确确认。保存失败保留草稿，冲突显示原因与可恢复动作。

日视图沿用时间轴，月视图沿用格线和事件色；手机周视图允许横向滚动的时间网格，并提供更易读的日视图。**历史设备延伸已被用户否定：**原从手机Today延伸为大时钟和日程并排的方案保留作记录，不再用于设备首页；现按独立常亮规范执行。Records与Device采用开放列表分区，不新加无依据统计或假开关。

时钟／日期、实际事件、加载或错误提示、认证与提醒入口属于必要动态差异。生成图中轻微像素纹理不进入CSS；纯白背景保持。天气、AI和相机未接入时不显示虚构结果，相关状态以真实能力说明为准。

## 验证记录要求

浏览器实际查看1536×1024电脑、390×844手机与1024×600设备布局；按真实控件完成登录、创建、修改、重复例外、批量、语言、提醒和跨页面更新。最后使用view_image查看原参考与最新实际截图，记录布局、字体、配色、事件／控件和响应式五项差异及修复。手机状态栏、动态日期和新增必要功能明确单列，不声称完全相同像素。

## 2026-09-30 实施与检查结果

[实际应用](../../../desk-companion/README.md)已按本规范完成B1；[QA对照](../../../output/qa/desk-development-batch1-2026-09-29/verification.md)记录八项比较及截图。电脑主结构、时间网格与色彩保留；手机Today显示真实当前时间和当天示例，不绘制假的iOS状态栏。新增提醒箱／私人图标属于真实能力，未接能力保持说明。

手机日期字段采用单列，防止原生日期选择器挤压；提醒选项固定checkbox尺寸、两列排列，颜色／关闭等主要操作扩大为44px目标。密集月历格另需真机验证。320px周视图有意横向滚动，标题可省略并进入详情；日视图更适合快速查看。当时的设备布局给添加和提醒箱留独立触控空间；该设备截图现只作历史对照。

最后通过view_image复查两张参考、电脑与手机实际截图、手机表单、中文窄屏及设备首页；没有将IAB的缩放异常截图作为最终移动验证，采用Chrome重拍。临时显示尺寸已恢复，原始参考和提示词均保留。
