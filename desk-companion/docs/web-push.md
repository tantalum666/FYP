# Web Push

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
