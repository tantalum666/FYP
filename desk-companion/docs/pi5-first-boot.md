# Pi 5 8GB 首次启动 · Group 2

**2026-10-31：用户已恢复Pi工作。家庭Wi-Fi／教室Wi-Fi与网线／宿舍网线配置已写入原卡并安全弹出；实际开机连接以[本轮QA](../../output/qa/2026-10-31-pi-home-resume/verification.md)为准。[网络方案](pi-network-profiles.md)。**
<!-- FYP-CONTEXT-20261027 -->
> HISTORICAL 2026-10-27 快照：当时Pi暂停，旧API预算关闭。当前恢复状态见文首31日记录。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

**HISTORICAL 2026-10-27：用户暂不启动Pi，下一轮Halls冷启动卡已准备并安全弹出，尚未实测。恢复前先核对Mac当前IP并启动状态接收；详见暂停快照 (local historical material: `output/qa/2026-10-26-pi5-dorm/pause-state.json`; not included in this checkpoint)。**

2026-10-22。用户指定的128 GB SD卡已由官方Raspberry Pi Imager 2.0.7写入、完整读回校验成功并安全弹出。写入时目标为内置SDXC读卡器中的`/dev/disk14`、127999672320字节；该盘号以后可能变化，不得直接沿用写盘命令。没有写入Mac系统盘。

## 当前联网恢复状态

2026-10-26已保留系统补写NETGEAR02和受限LAN SSH，并实际连通Mac。网页登录／Alice显示／日历导航和Mac屏幕共享均成功；系统时间已同步。USB数据链路仍未接通。当前按[Mac访问指南](pi5-usb-mac.md)的Wi-Fi方法操作；联网与部署修复QA (local historical material: `output/qa/2026-10-26-pi5-classroom/verification.md`; not included in this checkpoint)记录证据，不重新烧卡。

## HISTORICAL：最初准备的Mac与USB路径

用户随后确认没有显示屏，只有Mac与USB线。已在原卡追加USB网络、公钥SSH和隧道内桌面配置，并再次校验／弹出。现在按[无屏幕连接指南](pi5-usb-mac.md)操作：断电插卡 → Mac数据线连接Pi5的USB-C电源口 → 等待离线安装／一次重启 → Mac双击Connect-Pi-from-Mac.command。学校账号在远程桌面里填写。10月23日已完成实际开机／扩容和修正版安装；10月26日远程桌面改由Wi-Fi隧道实际接通，USB数据链路仍未接通。

如果以后有显示器，仍可以直接使用本地桌面。网页的owner账户密码在Pi首次安装时生成，通过首次使用窗口查看。

系统登录用户为`desk`，与网页的`owner`不同。系统随机口令只在Mac的`~/Downloads/Desk-Companion-Pi5/pi-login.json`中保存，未写进聊天或Git。首次页面口令在Pi上生成，Mac系统口令文件不能用于网页登录。

## 已装内容与路径

- 官方Raspberry Pi OS 64-bit Trixie Desktop，发行2026-10-06；保留默认Wayland/labwc，不强制X11。
- 编译好的网页／AliceChan、后端、ARM64 Python3.13环境、姿态与唤醒模型、系统依赖、中文字体、Mousepad与Chromium；首次安装不需要在线下载Node／pip／apt。
- 程序与依赖：`/opt/desk-companion`，root所有。业务数据：`/home/desk/.local/share/desk-companion`，desk私有。
- 用户级`desk-companion.service`只监听`127.0.0.1:8831`，单进程；原版SSH关闭；当前卡启用受USB／所选私有LAN规则保护的公钥SSH，桌面／应用通过SSH隧道访问，没有公网发布。
- 现有本项目Qwen Key仅转入`/home/desk/.config/desk-companion/qwen.env`，0600、目录0700；首次配置后删除root暂存副本。不复制Mac日历／账户数据库或其他项目Key。
- 普通发行配置默认关闭AI／电脑执行；这张用户指定的Pi镜像显式启用Omni、受限笔记和Linux双应用适配器。仍需拥有者逐项批准写入，模型没有shell／任意路径／自动确认权限。

本机保留的专用`.img`含用户私有凭据，只用于这台个人Pi，不应上传Git或公开分享。历史USB工厂镜像（早于10月26日实机热修复）SHA256：`f2e1cf933a5191637a821794fd9f6a2baca9036ba58e6c8bb5791f2608951e99`；大小6744440832字节。构建／写入证据 (local historical material: `output/qa/2026-10-22-voice-linux-sd/verification.md`; not included in this checkpoint)。

## 诊断与验收边界

```sh
systemctl --user status desk-companion.service
journalctl --user -u desk-companion.service -n 50
cloud-init status --long
sudo tail -n 60 /var/log/cloud-init-output.log
```

安装完成标记是`/var/lib/desk-companion-provisioned`，其中是载荷SHA256；相同安装重复运行不重置账户，摘要不同会拒绝隐式升级。失败时先检查日志，不重新烧卡来冒充修复。私有日志／配置不要整份公开上传。

已验证：官方镜像下载SHA；ARM64依赖导入；离线安装、普通用户API、凭据权限与重复运行；cloud-init及网络schema；文件系统检查；镜像内载荷逐字节读回；SD写后校验。首次安装测试在隔离ARM64 Debian容器内执行，raspi-config／真实NetworkManager命令单独留待Pi；不是实际开机验收。

已验证Pi启动／扩容、修正版安装、NETGEAR02联网、网页与真实Linux桌面连接。仍未验证：VTC直连及远程可达、Pi直连Qwen、声卡／AEC／真实麦克风、Wayland双应用、GPU帧率／持续温度、姿态机位和机械硬件。最新统一Omni代码尚未同步，当前Pi是10月22日包加10月26日部署修复。写卡成功不能替代这些目标设备检查。5元仅为已结束的合成短测授权，日常用户主动语音仍按提供商计费，产品没有人民币硬限额。

学校设置依据：[VTC官方Android连接指南](https://dilwllrchelpdesk.vtc.edu.hk/en/support/solutions/articles/43000496746-how-can-i-login-to-vtc-wifi-by-android-mobile-device-)（页面修改2019，2026-10-22取阅）；系统来源：[Raspberry Pi OS](https://www.raspberrypi.com/software/operating-systems/)及[官方cloud-init说明](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/)。

10月26日VTC-Student试连未通过，已恢复NETGEAR02并重新验证网页／桌面。新boot配置只做恢复、不含学校凭据；已安装VTC profile私有保存但关闭自动连接。详见VTC专项结果 (local historical material: `output/qa/2026-10-26-pi5-vtc/verification.md`; not included in this checkpoint)。
