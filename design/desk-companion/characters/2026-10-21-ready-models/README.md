# 完整成品角色候选

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**HISTORICAL · 人物源与比较**。当前常驻已选 AliceChan；本页旧选择／精修下一步不再自动执行。原画、服装、失败源及各自许可保留。 [新聊天入口](../../../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

Group 2 · 更新2026-10-22。**用户已明确选择先使用AliceChan。**完整原版外观已经进入常驻网页／Device／独立输出，[当前原件、授权、兼容性和QA](../2026-10-22-alice/README.md)是后续入口。停止原生A1v1精修的决定继续有效；原画／九套服装和所有失败源保留。

此前的uDesktopMascot／Alice风格认可及AIニケ、Amica三款追加外观记录，见[GitHub专项筛选](github-star-screening-20261022.md)。下面为选定Alice之前的候选记录；其中“尚未选定／常驻未换”是当时状态。

## 10月21日预览与保留记录

打开[现成角色预览](http://localhost:8832/?surface=models&lang=zh)。已从作者 BOOTH 免费下载 Reveria Lite VRM1.5，并通过页面的「打开本地 VRM」实际载入完整文件；不把宣传图冒充应用渲染。保留原脸／短银白发／长耳与角／黑白服装／材质／绑定／表情。它偏幻想、偏年轻，和 A1 的成熟侧分长卷发方向不同，是完整成品候选。

文件仅在 Downloads 和此浏览器的 IndexedDB 保存，刷新后自动恢复；「移除浏览器副本」不删除 Downloads 原件。没有上传至服务器、Git 或第三方；没有放入 public/dist 或修改许可标记。64MiB 上限、VRM0/1 结构和内嵌纹理检查先于载入；带外部资源 URI 的文件被拒绝。读取失败会提示，原有可显示预览保留。解析器直接读取文件字节，修正首次 blob fetch 失败，既有 CSP 未改变。

本地模型在此页按原色／100%头部比例显示，不提供捏脸／换色和常驻应用；原生表情／轻笑／完整闭眼／模拟口型、多角度与旋转缩放可检查。旧内置模型和它们的有限参数／应用功能收进折叠项。常驻／Device 继续原有基线。旧 `surface=a1` 也转到本页；否决稿只在 `surface=a1-history`，有明确归档标记。

## 10月21日三款保留候选

| 模型 | 来源／价格核对（10月20–21日） | 实际范围与差距 |
|---|---|---|
| Reveria Lite · NYOA. | [作者页](https://24a.booth.pm/items/7916400)，免费 VRM | 原件47,832,328字节，SHA见[来源](source.json)。实际本地显示，偏幻想年轻；保留原貌，不认作成熟A1。 |
| SELESTIA · STUDIO JINGO | [作者页](https://booth.pm/ja/items/4035411)，¥6,000 JPY；包含VRM/Blender/FBX等 | 实际看过作者粉色长发展示图；偏柔和可爱。未购买／导入。Hub播放出现首次账户／条款门，未代办注册或点击同意。 |
| RINDO · STUDIO JINGO | [作者页](https://booth.pm/ja/items/3443188)，¥7,000 JPY；包含VRM/Blender/FBX等 | 作者展示图的收眼与神态更适合作成熟方向比较，仍非A1。作者把VRM/PMX标为测试格式，不能预先保证本应用效果。未购买／导入。 |

## 来源与限制

Reveria 文件内写 CC0、Hub允许再分发，但作者链接的 VN3 条款英文参考版禁止原样再分发，改作分发需联系，软件捆绑另有限制；日文优先。当前采取**本机个人预览、不分发模型数据**。没有因文件内标签而宣称许可已完全清除，也没有主动联系作者。©NYOA24A；[完整来源／哈希及已核范围](source.json)。

原件 glTF 检查保留6项 `SKIN_SKELETON_INVALID`、1条旧 VRM 扩展警告和89项信息。实际可显示不代表原件已满足全部 glTF 规范、Pi 性能或可直接正式分发；本次不自动修几何、骨架、贴图或改许可。选定角色后再处理需要的兼容性和最小互动。

实际 QA 与截图 (local historical material: `output/qa/2026-10-20-ready-models/verification.md`; not included in this checkpoint)记录读取／缓存恢复、表情／角度、响应式与失败保留。当前工作本地未提交，PR16未更新或合并；语音、Linux/Pi、硬件和学校提交不在本轮验证内。
