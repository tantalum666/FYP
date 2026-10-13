# Evidence transfer and limitations

仅转交证据，未重启服务或测试。原文件字节保持不变；永久删除未执行。

报告 `report.md`：UTF-8 **12818 字节**，SHA256：
`a5d37ab0f5dec78f960928cf3bc90e2eb20d0c3ab18b0c5425861918940eac7f`

转交时发现两项需要附注的证据限制：

- 部分 `.txt` 保存的是“accessibility tree 没有变化”的摘要。原报告的“28b AX has…”只能作为当时工具返回的观察记录，保存的 TXT 不能独立复核完整详情。
- 53、54、56、58、59 等后段截图虽以 `.png` 命名，实际编码为 **JPEG，1280×720**。14、43、50、52 为真正 PNG。没有改名、转码或改写原报告。

已实际查看的还原截图已保存至 Library，返回确认：
`library_file_id = libfile_7cb9831f63508191a4d4bf8550039217`。
文件为 `50-watch-restored-terminal-history.png`，193424 字节，SHA256：
`6c49c0c4e0bac32620a2b6b1ee12b3115c0f4319d40d110698d3f736c2bcdc91`。
本地 Library 身份写回成功，上传后文件字节哈希未变。

精选 manifest 如下，不包含全量64图：

| 文件 | 字节 | SHA256 |
|---|---:|---|
| 14-search-zh-work-narrow.png | 89497 | `9fe13d51c38c015cc2b975f67803f9a32735fe9a2ca3693813ea09270bbae66f` |
| 43-watch-retry-completed.png | 185281 | `f52bfcdd97f35108cf5a53ee5043844b156f6869b0302c8a495e07c41ac8cae1` |
| 50-watch-restored-terminal-history.png | 193424 | `6c49c0c4e0bac32620a2b6b1ee12b3115c0f4319d40d110698d3f736c2bcdc91` |
| 52-permanent-removal-preview-cancelled.png | 163297 | `4869a30bc3a723d13af8480f8d57a55100ab455e943694a2e6b05666a7a4e34f` |
| 53-capacity-zh-known.png | 69852 | `1d4b4ae010162af166ef4d7ad9b2195b4e7a1e5fb03774f671d655a0c9600a54` |
| 54-capacity-unavailable-unknown.png | 57133 | `ac4a0cc2205a55cad13dbd3efa969a947dde148672e28c00d1a5c29f2a9edcac` |
| 19-search-late-fence.json | 70 | `bf6da014271a4d55b441c10ed055dfa4433c6b3923cc12e274e0dad45f5be7b7` |
| fixture-controls-used.jsonl | 311 | `44799c0e5af531d3fdba9a9218072a55a968fc70a026790d7d671a6f8294ae90` |
| fixture-closeout.json | 3800 | `e02c1676a56336557d0f95be76160e9c09c44790c657ccbcd7b21386f82c8696` |

14测得图像尺寸390×844；43/50/52为1280×800；53/54实际为1280×720。19仅记录 `responses: []`、`hits: 0`、`query: ""`，不能证明迟到响应围栏。

关闭清点时间 `2026-10-13T16:12:11.518534+00:00`：schema3，3任务、6文件、24项已取消Work、3项已取消且保留历史的关注、2条审阅；模型/工具调用、text AI usage、agent steps、connector intents、computer jobs、public captures均为0。服务退出码0，5191无监听。
