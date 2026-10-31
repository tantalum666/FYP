# 只用 Mac 访问 Pi 5 · Group 2

**31 October latest: Pi work is paused by the owner. The results below are preserved checkpoints; resume hardware only on a new owner instruction. Active personal-agent software is [PR74](https://github.com/tantalum666/FYP/pull/74).**

**2026-10-31：家庭Wi-Fi、原配对SSH、网页Alice与Mac屏幕共享已实测连通。教室Wi-Fi／有线、宿舍有线配置已从Pi读回，有线尚未插线验收。Pi本机浏览器触发低电压事件，当前先核对电源／线材。详见[本轮QA](../../output/qa/2026-10-31-pi-home-resume/verification.md)与[网络方案](pi-network-profiles.md)。**
<!-- FYP-CONTEXT-20261027 -->
> HISTORICAL 2026-10-27 快照：当时Pi暂停，旧API预算关闭。当前恢复状态见文首31日记录。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

**HISTORICAL 2026-10-27：用户暂不启动Pi，下一轮Halls冷启动卡已准备并安全弹出，尚未实测。恢复前先核对Mac当前IP并启动状态接收；详见暂停快照 (local historical material: `output/qa/2026-10-26-pi5-dorm/pause-state.json`; not included in this checkpoint)。**

HISTORICAL 2026-10-26：当时通过教室NETGEAR02连通SSH、网页和Mac屏幕共享，无需外接显示器。Pi已开机、扩容、安装；保留原卡系统及数据，补写联网配置并修复实际发现的启动／网页／桌面兼容问题。实机QA (local historical material: `output/qa/2026-10-26-pi5-classroom/verification.md`; not included in this checkpoint)保留全部失败与最终读回。

## 当前连接方法

1. Pi插卡并启动，Mac与Pi连接同一个可互通LAN。家里使用已保存的家庭Wi-Fi，教室保留NETGEAR02并支持网线，宿舍使用网线；实际优先级见[网络方案](pi-network-profiles.md)。USB数据链路仍未独立验证。不要带电拔卡。
2. Mac双击`~/Downloads/Desk-Companion-Pi5/Connect-Pi-over-LAN.command`。主机名为`desk-companion.local`，31日家庭实测地址为`192.168.0.105`；DHCP地址可能变化，应重新发现，不能沿用旧教室地址。
3. 网页通过`http://127.0.0.1:8891/?lang=zh`进入，Mac屏幕共享通过`vnc://127.0.0.1:5901`进入。这两个端口只在Mac回环监听。保留连接脚本窗口，关闭或Ctrl-C会断开隧道；若提示端口占用，先确认已有连接，不强制结束其他程序。
4. 网页用户名`owner`，使用Pi生成的网页密码。屏幕共享使用独立桌面密码。Mac私有副本分别是`~/.config/desk-companion/pi5-classroom/web-login.json`和`desktop-login.json`，权限0600，口令不进入聊天／Git。
5. 当前桌面会话已登录。Pi系统用户`desk`，其既有口令仍在Downloads/Desk-Companion-Pi5/pi-login.json；不要把系统、网页和桌面密码混用。

### Pi专用显示端与远程管理入口

Pi已有独立常亮／触控界面，见[设备规范](../../planning/2026-09-30/device-display-spec.md)。当前隧道中的[专用显示端](http://127.0.0.1:8891/?surface=device)使用`?surface=device`，路由到DeviceApp；普通工作区中的`?page=device`只是设备设置页，两者不可混称。前一轮回复展示的侧栏／设备设置截图不是Pi常亮界面。

实现为Pi本地API／静态资源，加Chromium应用窗口或kiosk全屏显示，业务与手机／网页共享，设备构图独立。Pi本机访问127.0.0.1:8831，Mac隧道预览访问8891。它不需要Mac负责运行主界面，也不需要联网下载UI；外部AI等在线功能另算。

31日实机读回确认`/opt/desk-companion/scripts/kiosk.sh`默认指向`?surface=device`，带`--kiosk`；欢迎窗口的“打开桌面页面”也指向这个入口。当前autostart仍执行session.sh→welcome.py，尚未配置为自动进入常亮全屏。重新通过Mac渲染Pi提供的设备页，时钟／月历正常，未登录时Calendar locked；触控入口打开登录面板，关闭后返回显示，无应用warn/error。此检查没有启动Pi本机Chromium、修改登录或自动启动，不等于Pi触摸屏／长期配对／连续运行验收。

31日家庭Mac地址192.168.0.107/24，Pi为192.168.0.105/24，直连路由经en0，原SSH主机密钥一致。`eth0`最后为无载波，当前家中及学校网线均未实测。HISTORICAL：26日教室Mac为192.168.49.3/24、Pi Wi-Fi为192.168.49.5/24，Pi以太网曾取得172.18.37.28/24，和Mac不同网段；网口灯亮不等于远程可达。学校Student/Halls的问题保留在下方历史记录。

## 访问范围

- SSH使用原专用Ed25519密钥和独立known_hosts，只允许desk公钥；root、密码及交互口令登录关闭。不删除已记录主机身份。主机身份变化应停下来核对。
- nft允许lo／usb0，以及eth0和已选定wlan0连接的当前直连私有IPv4网段（/20或更小）；实际家庭规则为wlan0来源192.168.0.0/24，其余SSH入站丢弃。连接／租约事件更新项目独立表，不清空系统／NetworkManager的其他规则。
- 应用仅监听Pi127.0.0.1:8831，WayVNC仅监听127.0.0.1:5900；SSH仅允许转发这两个目标。没有将应用或VNC直接暴露给教室LAN。
- Mac屏幕共享需要兼容的VNC密码方式。当前WayVNC0.10.2用独立八字符密码和legacy authentication，真正的网络认证／加密仍由SSH承担。私有桌面配置保持0600，重试不重置密码；不能把此VNC模式独立公开到网络。[官方兼容说明](https://github.com/any1/wayvnc#des-authentication-legacy)。
- Mac脚本只接受实际直连LAN路由，不经VPN或任意异网段地址尝试SSH。没有关闭VPN、启用Internet Sharing或放宽Mac系统安全设置。
- 仍保留Wayland/labwc和1280×720无实体屏幕输出。相机、唤醒／语音及机械输出服务默认停用。

## USB路径与历史

原USB脚本为`Connect-Pi-from-Mac.command`，默认地址10.12.194.1。只有Mac实际识别USB网络接口后才可用；该地址走VPN时脚本拒绝连接。Pi使用已装官方rpi-usb-gadget；此前两根线和端口试验没有枚举数据设备，不能断言线材或板子损坏。官方Pi5供电建议及实际供电余量仍需独立核验；短测throttled=0x0不等于连续运行验收。

历史私有工厂镜像`desk-companion-pi5-usb-fixed-20261023.img`的SHA256为`f2e1cf933a5191637a821794fd9f6a2baca9036ba58e6c8bb5791f2608951e99`。它含凭据且早于10月26日修复，不能公开或称为当前卡完整备份。此次卡只改user-data/meta-data；五份旧启动文件保存在Mac私有pi5-classroom目录，原系统和应用数据不重刷。

## 诊断与当前版本

```sh
cloud-init status --long
systemctl status ssh desk-usb-ssh-guard
systemctl --user status desk-companion desk-vnc
wayvncctl client-list
```

安装标记为`/var/lib/desk-companion-provisioned`，课堂联网标记为`/var/lib/desk-companion-classroom-20261026-ready`。当前网络状态为`/boot/firmware/desk-network-status.json`，只读回选定非秘密字段；完整私有日志／配置不要上传。31日NTP已同步。cloud-init虽结束但有缺少`cc_netplan_nm_patch`的可恢复警告；不能把exit2隐去或写成全绿。

Pi运行10月22日离线包加10月26日三处部署修复，最新统一Omni／Work代码尚未同步到Pi。当前已验证家庭联网、登录、Alice网页与Linux桌面连接。Pi本机Chromium可渲染，但启动时出现低电压；已关闭窗口，先核对供电再做有界稳定性复测。之后才按[迁移契约](pr5-integration.md)停服务、备份并更新软件。Pi语音、声卡／AEC、Wayland双应用、GPU帧率／持续温度、姿态和机械仍未验收。

## 2026-10-26 VTC-Student试连结果

按学校官方PEAP／MSCHAPv2、系统CA和vtc.edu.hk域名校验设置，凭据只在私有配置。首次5GHz关联报status16，没有观察到进入EAP；两个后续2.4GHz切换没有完成状态记录，管理连接中断。不能据此认定密码错误、学校隔离或硬件损坏。专项QA (local historical material: `output/qa/2026-10-26-pi5-vtc/verification.md`; not included in this checkpoint)保留经过和限制。

正常重启后已恢复NETGEAR02、公钥SSH、网页及Mac桌面。VTC自动连接关闭，试验任务停止，临时校园地址SSH例外已撤除。VTC资料保留在Pi的root0600配置，后续需先定位无线关联／切换问题再启用；不要重复烧卡、提交密码或把未经验证的固件降级当作修复。

## HISTORICAL 2026-10-26：宿舍Student／Halls

用户随后移至宿舍并要求按Student→失败后Halls重试。Mac的Student网络地址现为10.104.53.195/21；Halls显示为已保存的加密网络，网页确认另行检查。教室NETGEAR02恢复成功是历史证据，不等于宿舍Pi在线。当前没有挂载SD或Pi USB入口，等待原卡回插后再配，不能直接沿用教室地址／防火墙来源。详情见宿舍预检 (local historical material: `output/qa/2026-10-26-pi5-dorm/verification.md`; not included in this checkpoint)。

宿舍后续实测：Student接入／DHCP已成功，Mac远程访问未通；自动转Halls后无线激活失败，尚未到网页。当时日志门 (local historical material: `output/qa/2026-10-26-pi5-dorm/verification.md`; not included in this checkpoint)记录详情。当时SD留Mac读取错误；31日已重新插回Pi并验证家庭连接。内置SD槽可能报告Internal，应按可移除介质、容量、UUID、root和已知主机身份核对，不能仅用external筛选判定有无SD。
