# A1 · 第二轮服装六套

Group 2 · 2026-10-12。状态：**A1_CHARACTER_SELECTED / SIX_NEW_OUTFITS_COMPLETE / OUTFIT_SELECTION_PENDING**。

用户明确“确定A1为后续形象，再设计几套A1的服装”。A1成为后续角色身份，C1转为历史对照；没有据此擅自选定上一轮A1-W1／W2／W3中的任何一套服装。本轮继续银灰长发、灰蓝眼、开环发扣及既有成年脸型／性格，以[A1 V4](../2026-10-10-concepts/a1-silver-mist-anime-v4.png)为唯一参考，完整探索六套新衣服。

[六套并排预览](review-board.html)／[A1全部九套总索引](../a1-wardrobe-index.md)。

| 编号 | 原图与方向 | 实际轮廓 | 完整实际提示词 |
|---|---|---|---|
| A1-W4 | [新中式](a1-w4-modern-chinese.png) | 立领斜襟、短肩披与交叠裙，蓝白配色和云纹形成新中式轮廓。 | [prompt](prompts/a1-w4-modern-chinese.txt) |
| A1-W5 | [轻哥特](a1-w5-soft-gothic.png) | 方领、绒感上身、短泡袖、烟紫分层A字裙与系带短靴。 | [prompt](prompts/a1-w5-soft-gothic.txt) |
| A1-W6 | [居家针织](a1-w6-cozy-knit.png) | 燕麦白针织开衫、灰蓝高领上衣、炭灰短裤、过膝袜与便鞋。 | [prompt](prompts/a1-w6-cozy-knit.txt) |
| A1-W7 | [太空探索](a1-w7-space-explorer.png) | 象牙白灰蓝连身服、封闭拉链、腰带、完整长裤和厚底短靴。 | [prompt](prompts/a1-w7-space-explorer.txt) |
| A1-W8 | [海风度假](a1-w8-seaside.png) | 条纹船领上衣、雾蓝中长交叠裙、腰带及平底凉鞋。 | [prompt](prompts/a1-w8-seaside.txt) |
| A1-W9 | [星夜礼服](a1-w9-starlight-dress.png) | 午夜蓝不对称露肩礼服、局部缎面饰边、银扣及少量裙摆几何装饰。 | [prompt](prompts/a1-w9-starlight-dress.txt) |

## 实际检查与建议

协调代理逐张使用view_image检查全部六图：A1身份和原站姿基本稳定，成年观感、完整头／双手／双鞋与服装结构通过。六套明确改变领口、裙裤长度、袖形、材质和鞋型；背景与材质仍有柔和渐变，不能称完全两级赛璐璐或逐像素相同。

助手建议优先比较 **A1-W4新中式**与**A1-W6居家针织**：前者有清楚的服装身份，后者适合安静亲近的日常常驻。W9可作更正式的主题装。只是本轮视觉建议，具体默认服装未由用户选定。

- **A1-W4：**云纹较宽，盘扣及流苏较多，鞋跟高于很低跟目标。
- **A1-W5：**蕾丝边较宽，绒面纹理／高光较强，短靴为适度方跟。
- **A1-W6：**开衫长至下臀／大腿上部，比高髋目标稍长；腰线与短裤仍清楚。
- **A1-W7：**袖袋、腿袋和腰带环比简报多；衣料仍有自然余量，未变成紧身胶衣。
- **A1-W8：**腰部新增小圆扣，垂带稍长；首图开口高于本套简报范围，第二次生成后保留。
- **A1-W9：**银灰鞋跟较低跟目标高，长侧裙尖略超过膝下。

## 原图、提示词与范围

[manifest](manifest.json)及每项receipt保存精确输入／输出／prompt哈希、原生路径与尝试数。六张成稿均1024×1536，原生与工作区PNG逐字节一致，无裁切、缩放、拼图或像素后期。

三个现有图像代理各顺序生成两款，未新增代理句柄。共七次内置ImageGen：W8首图交叠开口高于本套“小腿范围”的简报，使用完全相同提示词重试一次；[首图](a1-w8-seaside-attempt1-rejected.png)与两次真实路径保留在receipt，不显示为正式候选。其余五张首次成功，没有再生成已合格图。无IP参考图、CLI/API回退或C1新图。

原生Creative Production画板的直接调用仍不可用，遵守禁止嵌套挂载的要求；共享renderer生成静态检查页。原A1／B1／C1／E1及上轮六图原文件与提示词均保留。角色选择不等于原创VRM或对应3D服装已完成；运行许可模型与学校文件保持。

[本次QA](../../../../output/qa/2026-10-12-a1-wardrobe-round2/verification.md)继承同一美术任务的全文阅读并记录本次补读、视觉、来源、保护与链接检查。该轮原计划先收敛服装；用户随后要求先保存再做形象图，现已另存[九套原图包](../../../../output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)并完成[A1六视角／四细节](../2026-10-12-a1-turnaround-details/README.md)。当前统一角色可制作参考，具体默认服装仍未选定。
