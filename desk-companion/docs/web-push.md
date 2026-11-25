# Web Push

## 26 November · Lock-screen delivery on the normal desk

A Mac operator can opt in using a private mode-0600 `locked-reminders.json` in the selected runtime directory. It contains an inclusive Hong Kong `through` date, the `keep_awake` preference and, for Simulator delivery, a `simulator` object with an exact `udid`, loopback server `origin` and optional absolute CoreSimulator `device_set`. Screen lock does not require the page or native application to run. The local operator must enable notifications on the named Simulator against the same server. A change of server or an explicit opt-out clears its native receiver binding.

With that configuration, the existing backend schedule drains the durable notice outbox in quiet-aware, recipient-specific attempts. Each current subscription has its own acknowledgement. A simulator acceptance is separate from a Web Push service acceptance and from evidence on the screen. The Mac idle-sleep assertion belongs to the backend process. Browser or OS Focus settings still determine presentation. [Validated scope](../../output/qa/2026-11-26-grok-and-locked-reminders/verification.md).

## 25 November · Delivery evidence

The local browser queue records preparation for delivery. A separate `web_push_accepted` row records when the sender has received a successful response for at least one enrolled subscription. The receipt contains the notice ID, channel and time. The desk cannot establish whether the device displayed the banner or the owner read it from that response. Previous browser queue records remain available. [Verification](../../output/qa/2026-11-25-proactive-mail/verification.md).

## 2026-11-24 · 浏览器订阅与通知回到对话

在已启用 Web Push 的桌面，拥有者可在日历与助理偏好里启用「关闭 Alice 页面后也提醒我」。浏览器自身的通知权限仍由本人选择。页面从 PushManager 取得订阅，FYP 的原有 VAPID 发送器负责加密和投递。点击通知会打开同一来源的 Alice 对话。可以从同一处取消订阅。付费模型额度和 Web Push 订阅分别管理。后台主机需要在线，独立的设备必须在能够访问该桌面的受支持浏览器上订阅。

2026-10-27，Group 2。默认关闭。设置 `DESK_WEB_PUSH=1` 之后才会生成密钥并发送。

## 开关

未设置该变量时，`GET /api/push` 返回 `enabled: false`，不创建密钥文件，订阅接口返回 `PUSH_DISABLED`。页面收件箱和本机 Notification 仍可用。测试不打开网络连接。

## 密钥

第一次启用时在数据目录写入 `vapid-private.pem`，权限 `0600`。再次启动读取同一把密钥。公钥由 `GET /api/push` 给出。主题固定为 `mailto:desk-companion@localhost`。这不是一套付费推送服务。

## 订阅与撤销

拥有者 `POST /api/push/subscriptions`，正文是浏览器给出的 `endpoint`、`p256dh` 和 `auth`。同一 endpoint 再次保存会清掉撤销标记。`POST /api/push/subscriptions/{id}/revocations` 之后不再向该订阅发送。配对终端不能调用这些接口。

## 发送

发送器可以替换。正式路径用 `HttpPushSender` 把 aes128gcm 正文 POST 到订阅的 endpoint，并带 VAPID `Authorization`。测试传入假的发送器或 `httpx.MockTransport`。安静时段不发送。同一个通知 id 在浏览器通道只投递一次，因此也不会第二次发送。

浏览器要显示这条消息，需要 `frontend/public/sw.js` 和用户允许通知。服务工作线程只在消息到达时显示标题和正文。
