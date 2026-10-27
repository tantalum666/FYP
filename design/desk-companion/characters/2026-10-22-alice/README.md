# AliceChan：当前初用角色

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../../../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

Group 2 · 2026-10-22。用户明确要求保存模型比较，并先使用AliceChan；此决定取代继续选型或精修被否决A1v1的下一步。采用作者完整外观，A1原画／九套衣服／失败源仍保留；没有把此初用选择扩为永久品牌决定。

- 作者：edisonlee55，当前GitHub名yuna0x0；作品Alice Chan (Uniform ver.)。
- [作者仓库](https://github.com/yuna0x0/AliceChan)／[正式发布v1.0.4](https://github.com/yuna0x0/AliceChan/releases/tag/v1.0.4)；该发布附带的独立VRM文件版本为1.0.2、实际为VRM0。
- 未改原件 (local historical material: `design/desk-companion/characters/2026-10-22-alice/alice-original.vrm`; not included in this checkpoint)，16,791,024字节，SHA256 `f04f0585aa73d47843ffe1a3042e776d679e345a3d7301c349f4d81e641b19bd`。
- 授权：[作者完整CC BY-SA4.0](../../../../desk-companion/frontend/public/avatars/alice/LICENSE.md)。保留作者、来源、许可、修改说明；后续共享改作继续遵循ShareAlike，不宣称作者背书或全部学生原创。
- [运行副本](../../../../desk-companion/frontend/public/avatars/alice/alice-ready.vrm)，16,790,968字节，SHA256 `370b2312e9f97834db868751e43e9dd33b9112e5d151d592757c3f47315e195e`。
- [来源和内嵌权限](../../../../desk-companion/frontend/public/avatars/alice/source.json)、[兼容性变更](compatibility.json)、重现脚本 (local historical material: `design/desk-companion/characters/2026-10-22-alice/build_runtime.py`; not included in this checkpoint)。运行副本同为CC BY-SA4.0。

Khronos检查原件有3处SKIN_SKELETON_INVALID，均为可选skin.skeleton字段指向的节点不是所有关节的共同祖先。运行副本只把三项1改为0；JSON其他字段相同，完整BIN字节相同。几何、脸／发／衣、材质／纹理、关节编号／逆绑定、表情和VRM许可均保留。运行副本0错误、17警告、24信息；警告主要为旧VRM扩展命名及原件不含切线。检查器不验证VRM扩展本身，浏览器另做实际显示。

## 已接入与验证

默认原色／100%头部比例；Web常驻、DeviceApp与独立黑底／镜像输出使用同一运行资产。原生眨眼、轻笑、幅度口型、注意／短点头保持。拖动、连续缩放、边缘半身／露头／隐藏与召回保留；当前不增加游戏式动作或重建五官。

`?surface=models&lang=zh`可看各角度／全身／脸部和署名。内置选择应用到已打开的同源Web／Device页；旧本机VRM缓存保留，可主动打开。原v1外观偏好保留在旧key，新v2默认Alice，不把旧银灰／96%头比例套到新角色。

本轮QA与截图 (local historical material: `output/qa/2026-10-22-alice-software/verification.md`; not included in this checkpoint)实际覆盖全身／脸、换模取景、跨页同步、常驻拖到边缘、缩放／隐藏／召回、设备页与390宽布局。浏览器结果来自Mac，不代表树莓派GPU／内存／热负载验收。研究候选和作者许可比较保留在[上轮目录](../2026-10-21-ready-models/README.md)。
