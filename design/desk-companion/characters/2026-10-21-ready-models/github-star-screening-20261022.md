# GitHub完整人物：star与个人使用筛选

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**HISTORICAL · 人物源与比较**。当前常驻已选 AliceChan；本页旧选择／精修下一步不再自动执行。原画、服装、失败源及各自许可保留。 [新聊天入口](../../../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

Group 2 ·2026-10-22。同一成品选择任务继续。用户认为uDesktopMascot自带角色、AliceChan还可以，要求再找有一定star、免费或个人可用的精美模型。**这是参考风格认可，不是最终人物／服装选择。**完整原貌优先，原生A1v1仍停止精修。

**随后用户决定：**选择先用AliceChan；已完成常驻接入，[当前资产／许可记录](../2026-10-22-alice/README.md)。下文保留选择前的比较与当时结论，不再以继续选型作为当前任务。

## 实际新增三种外观

| 完整角色／文件 | 来源项目与本次star | 实际观察 | 使用范围 |
|---|---|---|---|
| AIニケちゃんv2外套版 | [AITuberKit](https://github.com/tegnike/aituber-kit)1,127★；[独立官方素材库](https://github.com/tegnike/nikechan-assets)本身1★ | 原版VRM已实际载入，近景／30°／全身已看。紫色高马尾、金眼睛、宽外套、短裤、运动鞋，偏活泼可爱。 | [现行VRM条件](https://github.com/tegnike/nikechan-assets/blob/main/vrms/README.md)：个人非营利参考；禁止原件／改件再分发或应用打包，学校／团体使用未清除。官方明确旧内嵌flag不适用，以当前条件为准。 |
| 棕发短发款 | [Amica](https://github.com/semperai/amica)1,617★；[确切文件B](https://github.com/semperai/amica/blob/master/public/vrm/AvatarSample_B.vrm) | 内嵌title为AvatarSample_A、作者VRoid Project。棕短发、米色针织外套、蓝蝴蝶结、深色短裤／连袜和便鞋；近景／全身已看，较适合日常助理方向。 | [pixiv样本条件](https://vroid.pixiv.help/hc/en-us/articles/4402394424089-VRoidPreset-A-Z)：个人／商业用途可按条件使用，非CC0，不收费分发样本或做样本角色创建服务。 |
| 紫发双马尾款 | 同一[Amica模型目录](https://github.com/semperai/amica/tree/master/public/vrm)，不是另一个1,617★模型项目；[确切文件C](https://github.com/semperai/amica/blob/master/public/vrm/AvatarSample_C.vrm) | 内嵌title为AvatarSample_B。紫黑双马尾、彩色挑染／发饰、颈饰、黑上衣、棒球外套、粉裙；近景／全身及轻笑已看，风格更鲜明。 | 同上，保留原作者条件；不是Amica自制或CC0模型。 |

三款均保留原脸、头发、衣服、材质、骨架；原色、头部比例100%。原件字节／SHA、文件名错位、作者条件、当前stars与截图本机路径见[来源记录](github-star-screening-20261022.json)。文件内作者缩略图与实际网页截图分开保存。原件／图片只在Git忽略的`desk-companion/.runtime/github-model-screening-20261022/`，不随Git分发。

## 对照与未列入主选

- [uDesktopMascot](https://github.com/MidraLab/uDesktopMascot)357★，模型另标CC BY-NC4.0；[AliceChan](https://github.com/yuna0x0/AliceChan)8★，作者标CC BY-SA4.0。用户认可作参考，未设最终默认。
- [Microsoft Rocketbox](https://github.com/microsoft/Microsoft-Rocketbox)654★，微软明确MIT发布115个绑定人物，是确有模型数据的备用库；本轮未下载／试载，不算已验收的二次元候选。
- [hinzka52blendshapes](https://github.com/hinzka/52blendshapes-for-VRoid-face)271★，男／女素体与52种表情适合技术参考，不当完整服装人物。
- Amica文件A实际是Sara的Amica_1，带ExplicitlyLicensedPerson／禁止再分发，未验证本用户的独立授权。本次只列B/C两份pixiv样本。
- [ChatdollKit](https://github.com/uezo/ChatdollKit)1,241★的Unagirl嵌入OnlyAuthor，许可URL却指仓库Apache，未当作已清除；[Mate-Engine](https://github.com/shinyflvre/Mate-Engine)3,796★的默认模型保留权利、禁止随其他构建分发，未采用。
- AIRI50,559★作为运行框架参考，不因程序MIT或热度高就收下展示人物。旧ToxSam／Galaxy／自制头部不恢复为首选。

## HISTORICAL：筛选时的范围与建议

本轮读取公开GitHub资料／star／文件元数据，实际取得并试载3款完整原版。独立静态8843仅沿用已有构建，不启动后端、语音、相机或收费服务。无代码改动，所以未重跑无关测试／构建；没有Pi/GPU、连续动作或正式资产兼容性验收。取景按钮在换模后曾与画面不一致，手动切换后完成全身截图；未在研究中修UI。早期clip照片取景不佳，最终证据改为未裁切视口。

建议接下来比较AIニケ、Amica棕短、uDesktop原角色，紫双马尾作风格差异候选。用户仍未选定。个人本机参考与Group 2学校演示、多人共享、安装包分发分开核，尤其Nike不得把当前个人许可当作学校／团体已获授权。

本轮QA (local historical material: `output/qa/2026-10-22-github-model-screening/verification.md`; not included in this checkpoint)保留验证范围。下一步选定完整人物后，再做对应许可／兼容性与常驻接入，不重新进入J/Reira精修。
