# A1 原生精修 v1：脸型、眼睛与侧分波浪发

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**HISTORICAL · 人物源与比较**。当前常驻已选 AliceChan；本页旧选择／精修下一步不再自动执行。原画、服装、失败源及各自许可保留。 [新聊天入口](../../../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

Group 2 ·2026-10-19首版，2026-10-21明确否决。**用户认为外形太丑，要求直接用别人的模型；本版已停止精修并归档，完整源／导出／失败证据保留。**当前按[成品候选](../2026-10-21-ready-models/README.md)先保留作者原貌选择人物。本次只用完整现成模型、作者发型与VRoid原生控制，不恢复被否决的自制头部／程序化人物路线。

打开[真实对照页](http://localhost:8832/?surface=a1-history&lang=zh)。默认30°／轻笑，支持原画并排、正／侧／背、全身／脸、旋转／连续滚轮缩放、中性／轻笑／完整闭眼／模拟口型和暂停。该固定人物页不提供现代样本的捏脸／换色／比例创建服务，不挂工作空间Provider或采集音视频。常驻仍保留旧Shino／Victoria基线。

## 保存文件

- 完整可编辑源 (local historical material: `design/desk-companion/characters/2026-10-19-a1-vroid-refinement/a1-native-v1.vroid`; not included in this checkpoint)，6,979,013字节，SHA`9c6ad14616b2f03cba524b511a0842cdc0a01e2b7f0e6e42845abea68567ed4d`，ZIP CRC通过。
- 原生VRM导出 (local historical material: `design/desk-companion/characters/2026-10-19-a1-vroid-refinement/a1-native-v1.vrm`; not included in this checkpoint)，15,909,264字节，SHA`09398adfda7816e4e6e58ca2f5f17eab8c41e982e412ca9d67946b288f285234`。
- 运行VRM (local historical material: `design/desk-companion/characters/2026-10-19-a1-vroid-refinement/a1-native-v1-ready.vrm`; not included in this checkpoint)，15,909,228字节，SHA`6c629580037157d2ad198fa0b58c9e1009b4e36269276ec88e6f3bfd9dedd2c5`。当前只增加版本字段；BIN及所有非meta JSON字节／数据保持，几何、材质、纹理、形变和骨骼不变。
- [来源与改动](source.json)／[两个发型原件与SHA](third-party/reira/source.json)／打包脚本 (local historical material: `design/desk-companion/characters/2026-10-19-a1-vroid-refinement/prepare_runtime.py`; not included in this checkpoint)。应用中的固定副本和来源位于`desk-companion/frontend/public/avatars/a1-native-v1/`。

原J、原画／V4、九套服装、旧失败源和第一阶段脸部检查点均保留。未提交／推送／合并Git工作。

## 原生实际改动

VRoid2.14窗口此前可见但没有成为key window。通过系统Window菜单的`makeKeyAndOrderFront:`恢复后，滚动、文件打开、数值编辑和Save实际响应。文件对话框结束后需要核实焦点。上下文菜单操作作用于蓝色选中行，先选再右击；文本字段持焦点时使用实际Save菜单。

在完整官方J副本中调整下巴／脸型、原生鼻部、灰蓝虹膜，使用较收的现成眼型、细眼线和灰紫眉色；去掉两只兽耳与尾巴。原生表情／骨架保持。详细制作记录在progress.json (local historical material: `output/qa/2026-10-19-a1-vroid-native-refinement/progress.json`; not included in this checkpoint)，新眼组已取代早期眼部比例，旧数值只保留阶段历史。

用户下载的Reira Front／Back已导入；Front组用原生“翻转”对齐画面左侧斜刘海／右侧露额方向。主色B7B5CA、高光CAC5D4、细轮廓及柔和阴影构成本次配色。侧背面发现旧深色底发外露，实际换成可调色原生基础发型并将主色B7B5CA／阴影FFFFFF统一后重导出。前后失败与修正图保留。

临时使用原生高领模板，底色383B46／阴影2C2F39，以减少原衣物对脸部审阅的干扰。**它不是A1最终衣服或九套服装中的选款，完整剪裁、发夹和耳钉未完成。**

## 来源条件

底模为pixiv官方现代AvatarSample_J，[原件记录](../2026-10-18-existing-model-adaptation/editable-source-j.json)保留未改SHA。按[现代A-Z条件](https://vroid.pixiv.help/hc/en-us/articles/4402394424089-VRoidPreset-A-Z)使用，不标CC0，不进入角色创建服务。

头发为[Dahlia／Reira's Items的Wavy Hair V1与Edited Bangs V1](https://booth.pm/ja/items/4138976)。用户自行完成登录／下载；两个原件分别448,341／651,133字节，CRC及SHA已核。[作者条件](https://hub.vroid.com/en/characters/2503153150187103847/models/5733583802599684396)允许改作／再分发并要求署名，署名保留在UI、VRM和manifest；不称CC0或本组全原创。

首次原生键盘输入丢了URL冒号／作者分号，最终重新以原生paste输入，已在最新原生导出核实正确。打包脚本继续规范元数据，当前只增加0.1.0版本字段。没有修改模型二进制或重新投影原画。

## 验证与真实差距

本轮QA (local historical material: `output/qa/2026-10-19-a1-vroid-native-refinement/verification.md`; not included in this checkpoint)记录29前端检查、类型／构建、VRM0错误／14警告、真实桌面／窄屏、中英、多角度、眨眼／轻笑／模拟口型、鼠标旋转／缩放和来源保留。14条为旧VRM扩展名称与自动生成切线相关警告；不称零警告。浏览器模型请求HTTP200且显示成功，但调试事件仍有取消的ERR_ABORTED，原因未确认，保留记录。

与原画相比，上半段头发仍偏直，宽S波和蓬松感不足，右耳露出与脸部身份／成熟神态仍需继续校准。圆环夹、耳钉、完整服装和常驻替换未完成；本版用于实际审阅，不把工程通过当美术验收。Pi／Linux GPU／热负载和真实语音另验；本轮没有付费、真实采集、购买、外部联系或学校提交。

## 复现

```sh
python3 design/desk-companion/characters/2026-10-19-a1-vroid-refinement/prepare_runtime.py
cd desk-companion/frontend
npm run build
```

原生修改继续打开完整`.vroid`副本；导出时保留pixiv和Dahlia/Reira署名、两个条件URL及Other许可，不改成CC0。不再继续上段卷度／耳侧／脸部或服装精修；当前下一步以完整成品选择为准。
