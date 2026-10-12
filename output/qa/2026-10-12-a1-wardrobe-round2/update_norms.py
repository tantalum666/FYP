from pathlib import Path
import json
ROOT=Path('/Users/tantalum/Documents/ChatGPT/FYP'); QA=ROOT/'output/qa/2026-10-12-a1-wardrobe-round2'; changed=[]
def replace(p,old,new):
    q=ROOT/p;s=q.read_text();assert old in s,(p,old[:80]);q.write_text(s.replace(old,new,1));changed.append(p)
def line(p,prefix,new):
    q=ROOT/p;s=q.read_text();start=s.index(prefix);end=s.find('\n',start)
    if end<0:end=len(s)
    q.write_text(s[:start]+new+s[end:]);changed.append(p)
def paragraph(p,prefix,new):
    q=ROOT/p;s=q.read_text();start=s.index(prefix);end=s.find('\n\n',start)
    if end<0:end=len(s)
    q.write_text(s[:start]+new+s[end:]);changed.append(p)
replace('product.md','状态：**A1 V4／C1各三套服装概念已完成并检查，待选型；原稿与E1保留；第2份v5团队日志本地完成、待成员核对；运行角色仍用原许可样本**。','状态：**用户已确定A1为后续角色；A1新增六套服装，累计九套变体待服装选型；C1转历史参考；原稿／E1／学校日志保留，运行角色仍为许可样本**。')
anchor='## 已实现的软件范围'
new='''## 2026-10-12 用户确定A1与第二轮服装

用户明确“确定A1为后续形象，再设计几套A1的服装”。**A1角色身份已确定**，取代此前A1／C1仍并列待比较的当前状态；C1保留为历史参考。A1的银灰长发、灰蓝眼、开环发扣、成年脸型及既有性格继续，具体默认服装、正式名字／声音和原创3D资产尚未定稿。没有把用户选择A1解释为选择上一轮W1、W2或W3。

[第二轮六套新服装](design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/README.md)为W4新中式、W5轻哥特、W6居家针织、W7太空探索、W8海风度假、W9星夜礼服；[A1九套总索引](design/desk-companion/characters/a1-wardrobe-index.md)保留前轮三套。每项以A1 V4为唯一参考，六张成稿1024×1536；W8首图未符合本套中长裙开口简报，以相同提示词重试一次，其余首次成功，原生文件和实际提示词保留。协调代理逐张查看六张，身份／站姿基本稳定，头手鞋完整，服装结构可读。

助手建议优先比较W4与W6，W9可作正式主题装，是视觉建议而非用户已选默认衣服。当前从A1九套收敛服装，再细化选定款侧背面与可制作结构；E1反馈保留。原A1／B1／C1／E1、前轮原图／提示词、学校文件与运行许可模型保持。[本次QA](output/qa/2026-10-12-a1-wardrobe-round2/verification.md)继承同一美术任务全读与收尾记录，仅补读相关新增／变更，不重新声称全库阅读。

'''
replace('product.md',anchor,new+anchor)
replace('product.md','当前先比较六套，再按选定方向细化侧背面；E1反馈保留。','当时先比较六套；同日随后用户已选择A1，当前改为下节A1九套服装对照，E1反馈保留。')
paragraph('README.md','**Wardrobe exploration (12 October, current art step):**','**A1 selected (12 October, current art step):** The user has confirmed A1 as the continuing character identity. [Six additional A1 outfits and preview](design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/README.md) explore modern Chinese-inspired fashion, soft gothic, cozy knit, space exploration, seaside casual and evening wear. Together with the earlier three, the [A1 wardrobe index](design/desk-companion/characters/a1-wardrobe-index.md) contains nine outfit variants. All six new 1024×1536 PNGs and exact prompts are saved and individually inspected; C1 remains a historical comparison. The default outfit is still pending selection, and the licensed runtime model is unchanged.')
replace('README.md','C1 awaits comparison feedback and does not replace the runtime model.','C1 was a comparison candidate at that stage; the user subsequently selected A1, so C1 is retained as a historical reference and does not replace the runtime model.')
paragraph('desk-companion/README.md','**2026-10-12当前美术步骤：**','**2026-10-12当前美术步骤：**用户已确定A1为后续角色，C1转历史参考。新增[六套A1服装与并排预览](../design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/README.md)，加上前轮三套，见[A1九套总索引](../design/desk-companion/characters/a1-wardrobe-index.md)。角色身份已定、具体默认服装待选；原稿／E1、运行许可VRM和应用源码保持，概念图不表示对应3D服装已实现。')
replace('desk-companion/README.md','供对照，A1／B1／E1保持，当前先比较方向。','供当时对照；A1／B1／E1保持，同日后续用户已选择A1，当前服装步骤见下段。')
paragraph('desk-companion/docs/avatar.md','**Current art step, 12 October:**','**Current art step, 12 October:** the user has explicitly selected A1 as the continuing character identity. [Six additional A1 wardrobe concepts](../../design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/README.md) expand the [A1 wardrobe index to nine variants](../../design/desk-companion/characters/a1-wardrobe-index.md). Original A1 V4 is the sole identity/pose reference. Six 1024×1536 outputs were individually inspected; exact prompts and native PNGs are preserved. W8 used one retry for the specified skirt opening; the other five succeeded first time. A1 identity is selected, while the default outfit, original VRM, rigs and clothing deformation remain pending. C1 is a historical comparison. Original art, E1 and the licensed runtime sample are unchanged; current art work does not add runtime clothing or grant new tool permissions.')
replace('desk-companion/docs/avatar.md','C1 is pending comparison, not an approved final character.','C1 was pending comparison at that stage; the user has since selected A1, leaving C1 as a historical reference.')
replace('design/desk-companion/characters/a1-character-brief.md','# A1 Character Brief · Working v2','# A1 Character Brief · A1 selected / Working v3')
replace('design/desk-companion/characters/a1-character-brief.md','用户同意按日本动画研究建议推进；本页固定本阶段工作方向，最终脸型、声音及3D资产未定稿。','用户已明确确定A1为后续形象；本页固定角色身份与性格，服装、正式名字／声音及原创3D资产仍待细化。')
line('design/desk-companion/characters/a1-character-brief.md','- **服装：**','- **服装：**原[V4](2026-10-10-concepts/a1-silver-mist-anime-v4.png)作为身份／画风基准，衣服允许完整探索。现有[九套服装变体](a1-wardrobe-index.md)：前轮柔科技／轻户外／轻奇幻，以及本轮新中式／轻哥特／居家针织／太空探索／海风度假／星夜礼服。用户选定A1角色，但未选择具体默认衣服；各版原PNG／提示词保留。')
paragraph('design/desk-companion/characters/a1-character-brief.md','当前先比较A1与C1的','当前从[A1九套服装](a1-wardrobe-index.md)收敛默认款和备选，再细化选定款侧背面；E1表情反馈保留。C1为历史对照，不再与A1并列待选。不把角色选择称为原创VRM、绑定或自然语音完成。依据见[日本动画研究](../../../research/2026-10-10-avatar-art/japanese-character-study.md)。')
replace('design/desk-companion/characters/a1-expression-rules.md','本文件是本阶段工作简报；新表情图、最终脸型与3D资产仍需实际审阅。','用户同日随后已确定A1为后续角色；本文件继续固定其性格和表演规则，表情精修、服装与原创3D资产仍需实际审阅。')
replace('design/desk-companion/characters/a1-expression-rules.md','现有[六套独立服装对照](2026-10-12-wardrobe-variants/README.md)。','用户随后确定A1，现有[A1九套服装变体](a1-wardrobe-index.md)。')
route='**2026-10-12最新决定：**用户已确定A1为后续角色，C1转为历史参考；新增[六套A1服装](../2026-10-12-a1-wardrobe-round2/README.md)，累计[A1九套服装变体](../a1-wardrobe-index.md)。角色身份已定，默认服装待选。下文保留本目录原阶段记录，原PNG／提示词／manifest保持。'
for p in ['design/desk-companion/characters/2026-10-10-concepts/README.md','design/desk-companion/characters/2026-10-10-c1-concept/README.md','design/desk-companion/characters/2026-10-10-expression-study/README.md']:
    paragraph(p,'**2026-10-12当前路由：**',route)
replace('design/desk-companion/characters/2026-10-10-c1-concept/README.md','正式角色仍未选定。','当时角色尚待选择；同日后续用户已确定A1，C1留作历史参考。')
replace('design/desk-companion/characters/2026-10-10-c1-concept/README.md','当前先比较10月12日六套新服装，再按用户反馈细化选定方向；','当前推进A1服装与后续造型，C1原稿保留；')
replace('design/desk-companion/characters/2026-10-10-expression-study/README.md','当前先比较10月12日的新服装；','当前比较A1九套服装；')
paragraph('design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md','Group 2 · 2026-10-12。状态：','Group 2 · 2026-10-12。状态：**FIRST_ROUND_PRESERVED / A1_CHARACTER_SELECTED / OUTFIT_SELECTION_PENDING**。用户后续已确定A1为形象，C1转为历史参考；当前见[第二轮六套A1](../2026-10-12-a1-wardrobe-round2/README.md)及[A1九套总索引](../a1-wardrobe-index.md)。以下记录第一轮六图及当时建议。')
replace('design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md','当前下一步：依据这六套的比较反馈收敛服装方向，再细化选定款的侧背面与可制作结构；E1表情反馈仍保留为后续。','当前下一步：从A1九套变体收敛服装，再细化选定款侧背面；C1原款保留，E1反馈继续。')
rr='**当前状态（2026-10-12后续）：**用户已确定A1为后续形象，C1转历史参考；新增[六套A1服装](../../design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/README.md)，累计[A1九套变体](../../design/desk-companion/characters/a1-wardrobe-index.md)。角色身份已定，具体默认服装待选；E1、原稿／提示词与运行许可模型保持。以下原研究日期、来源和访问范围保留，不是本轮重做人气评估。'
for p in ['research/2026-10-10-avatar-art/popular-character-study.md','research/2026-10-10-avatar-art/wardrobe-study.md','research/2026-10-10-avatar-art/japanese-character-study.md','research/2026-10-10-avatar-art/mainstream-anime-c1-study.md']:
    paragraph(p,'**当前状态（2026-10-12）：**',rr)
replace('research/2026-10-10-avatar-art/character-concepts.md','C1是独立对照，尚未选为主方向。','C1是独立对照，现转为历史参考；用户已确定A1为后续角色。')
replace('research/2026-10-10-avatar-art/character-concepts.md','当前先比较六套，再细化选定方向。','后续用户已选定A1，当前见[新增六套A1](../../design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/README.md)与[A1九套总索引](../../design/desk-companion/characters/a1-wardrobe-index.md)，再细化选定服装。')
handoff='''# Group 2 Current Handoff

更新：2026-10-12后续。当前：**用户已确定A1为后续角色；新增六套A1服装已完成并检查，累计九套变体待服装选型。** C1转为历史参考，不再并列选角色。

## 当前产物与证据

- [新增六套A1原图／实际提示词／并排预览](design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/README.md)：W4新中式、W5轻哥特、W6居家针织、W7太空探索、W8海风度假、W9星夜礼服；[A1九套总索引](design/desk-companion/characters/a1-wardrobe-index.md)含前轮三套。
- 唯一参考为A1 V4；成年身份、银发／灰蓝眼／圆环发扣与原站姿基本连续。六张1024×1536，协调代理逐张查看，头／双手／双鞋完整、衣物结构可读。共七次内置ImageGen，W8首图开口未符合本套简报而同prompt重试一次；原生PNG／prompt／receipt保留，无像素后期。
- 助手优先建议W4与W6，W9可作正式主题装；不是用户已选默认服装。角色身份确定与衣服选型分开。来源与保存见[manifest](design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/manifest.json)及[本次QA](output/qa/2026-10-12-a1-wardrobe-round2/verification.md)。

## 保留状态与未完成项

旧A1／B1／C1／E1及上轮六图、提示词和原manifest保持；[A1简报](design/desk-companion/characters/a1-character-brief.md)与表演规则继续。默认服装、侧背面、E1精修、原创VRM／绑定尚未完成；运行时仍用pixiv许可样本。本次仅本地保存，无Git写入或运行时更改。

[第2份v5日志](planning/2026-10-11/logsheet-2-review.md)与学校原件保持，提交状态不在本次核实范围。真实语音／AEC／费用、Pi／iPhone／光学、PC／LCU、真人姿态及RIG实物仍需实现或实测；不由PNG概念代替。

## 唯一下一步

**从A1九套服装变体收敛默认款与备选，再细化选定款侧背面和可制作结构。** 不重新要求用户在A1／C1之间选角色。
'''
(ROOT/'handoff.md').write_text(handoff);changed.append('handoff.md')
with (ROOT/'decision-log.md').open('a') as f:f.write('''\n## 2026-10-12 后续：用户确定A1与第二轮六套服装\n\n- **用户决定：**“确定A1为后续形象，再设计几套A1的服装”。A1角色身份已确定，取代A1／C1并列待比较；C1及既有稿保留为历史参考。未选择前轮任一具体服装、正式名字／声音或已有运行模型。\n- **美术实施：**[新增A1-W4至W9六套](design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/README.md)，分别新中式／轻哥特／居家针织／太空探索／海风度假／星夜礼服。原A1 V4为唯一参考，身份与原姿态保持，衣服袜鞋可变。\n- **实际结果：**六张1024×1536原生PNG，七次内置ImageGen；W8首图开口不符本套简报，以相同prompt重试一次，首图与两次路径保存。三个现有图像代理复用，未新增句柄；协调代理逐张查看全部六张。原生与项目文件字节一致，无像素后期。\n- **建议与状态：**助手优先建议W4新中式／W6居家针织，W9作正式主题候选，属视觉建议。角色已定、默认服装待选；[九套总索引](design/desk-companion/characters/a1-wardrobe-index.md)进入当前入口，再细化选定款侧背面。\n- **保留：**前轮及旧PNG／prompt／manifest、E1与学校文件保持，运行时许可VRM未替换；没有Git写入、3D服装／绑定完成或目标设备新实测。\n''')
changed.append('decision-log.md')
with (ROOT/'work-log.md').open('a') as f:f.write('''\n## 2026-10-12 同一美术任务：A1确定与第二轮六套服装\n\n- **目标／决定：**用户确定A1为后续角色，再设计几套A1服装；C1转历史参考，具体衣服尚未选择。\n- **阅读：**按AGENTS同轮补充规则，继承上一阶段139份／12,884行全文及17份修改读回、新素材README；当前盘点140份，补读入口、A1简报／规则、前轮素材说明、最新决定与本次修改相关段。没有机械重启全库阅读或声称新全读。[本次记录](output/qa/2026-10-12-a1-wardrobe-round2/reading-record.json)。\n- **产物：**[六套新A1](design/desk-companion/characters/2026-10-12-a1-wardrobe-round2/README.md)、[九套总索引](design/desk-companion/characters/a1-wardrobe-index.md)、原PNG／实际prompt／receipt／manifest及共享renderer并排预览。W4新中式、W5轻哥特、W6居家针织、W7太空探索、W8海风度假、W9星夜礼服；均1024×1536，以原A1 V4为唯一参考。\n- **生成与检查：**复用三个限定图像代理，各顺序两款；共七次内置ImageGen，W8首图裙摆开口高于本套简报范围，相同prompt重试一次；其余首次成功。终态结果消费并用interrupt确认，工具无销毁句柄操作，不冒称销毁。原生与项目字节一致，无像素后期；协调代理实际查看六张成稿，身份／全身／结构通过，渐变、纹样与鞋跟偏差如实记录。\n- **同步与验证：**product、两个README、avatar契约、A1简报／规则、旧资产目录当前路由、五份美术研究、决定与handoff同步。角色选择与服装未选分开；旧图／prompt／manifest、许可VRM和学校保护项不变。文件、哈希、内链、预览与空白检查见[QA](output/qa/2026-10-12-a1-wardrobe-round2/verification.md)。纯美术任务不重跑应用套件／学校文档渲染。\n- **下一步／边界：**从A1九套收敛默认及备选，随后侧背面和可制作结构；E1／原创VRM／绑定仍待。应用源码、学校文件、运行数据保持，没有Git写入、硬件动作、语音消费、采购、签署、上传或对外联系。\n''')
changed.append('work-log.md');(QA/'updated-norms.json').write_text(json.dumps(sorted(set(changed)),ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'updated_norms':len(set(changed)),'selection':'A1 confirmed','C1':'historical reference'},ensure_ascii=False))
