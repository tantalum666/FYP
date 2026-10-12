from pathlib import Path
ROOT=Path('/Users/tantalum/Documents/ChatGPT/FYP')
changed=[]
def replace(path,old,new):
    p=ROOT/path; text=p.read_text()
    assert old in text, (path,old[:80])
    p.write_text(text.replace(old,new,1)); changed.append(path)
def prefix_current(path,line):
    p=ROOT/path; s=p.read_text(); pos=s.index('\n\n')+2
    p.write_text(s[:pos]+line+'\n\n'+s[pos:]); changed.append(path)
replace('product.md','更新：2026-10-11。状态：**第2份v5团队日志DOCX／PDF本地完成，待成员核对；A1／E1／C1保留，待方向反馈；运行角色仍用原许可样本**。','更新：2026-10-12。状态：**A1 V4／C1各三套服装概念已完成并检查，待选型；原稿与E1保留；第2份v5团队日志本地完成、待成员核对；运行角色仍用原许可样本**。')
new='''## 2026-10-12 A1与C1服装再设计

用户要求两位角色各再设计几版、尝试不同风格，不能只做都市上班族。这取代此前本阶段“保持既有服装”的限制，保留成年角色的脸、发型、眼睛、配饰与性格连续性。新的[六套服装与并排预览](design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md)分别为A1柔科技机能／轻户外／星旅轻奇幻，以及C1音乐舞台／运动休闲／现代和风；每项一次内置ImageGen编辑，1024×1536，原PNG及完整实际提示词保存。

协调代理逐张查看，六图头／双手／双鞋完整、主要身份稳定、服装结构可读。渐变、较高方跟、部分垂片／边饰比简报复杂的差异如实记录；六张均为有效首次结果，无重生成或像素后期。助手优先建议A1-W3与C1-W3进一步细化，属于视觉判断，不是用户已选型或人气结论。当前先比较六套，再按选定方向细化侧背面；E1反馈保留。原五版、E1、C1原图与提示词不覆盖，应用／学校文件不改。[本轮QA](output/qa/2026-10-12-wardrobe-variants/verification.md)记录完整阅读、来源与保护检查。

'''
replace('product.md','## 已实现的软件范围',new+'## 已实现的软件范围')
replace('product.md','当前下一步比较A1与C1，再细化选定方向；无新VRM或应用改动。','10月10日当时的下一步是比较A1与C1；10月12日已按新指令扩为六套服装对照，当前入口见下节；仍无新VRM或应用改动。')
replace('README.md','**Dot integration verification (9 October):**','**Wardrobe exploration (12 October, current art step):** [Six new full-body outfits and comparison preview](design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md) expand beyond office clothing: A1 soft-tech utility, light outdoor and astral fantasy; C1 music stage, sporty casual and modern Japanese-inspired fashion. Each uses its own original character as the sole visual reference. All six 1024×1536 PNGs, exact prompts and provenance are saved and individually inspected; original art and the licensed runtime model remain unchanged. A1-W3 / C1-W3 are assistant refinement suggestions, with user selection pending.\n\n**Dot integration verification (9 October):**')
replace('desk-companion/README.md','## 当前功能','**2026-10-12当前美术步骤：**A1 V4与C1各完成三套[独立服装再设计与并排预览](../design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md)，涵盖柔科技、轻户外、轻奇幻、舞台、运动休闲及现代和风。六张原生PNG／实际提示词已保存并逐张检查，当前先收敛服装方向；原稿与E1、许可VRM及应用源码保持。概念换装不表示运行时换装已实现。\n\n## 当前功能')
replace('desk-companion/docs/avatar.md','Updated: 10 October 2026','Updated: 12 October 2026')
replace('desk-companion/docs/avatar.md','## Original character art research','## Original character art research\n\n**Current art step, 12 October:** the user requested several wardrobe redesigns for both A1 V4 and C1, with styles beyond urban office clothing. [Six independent full-body variants and comparison preview](../../design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md) cover soft-tech utility, light outdoor, astral fantasy, music stage, sporty casual and modern Japanese-inspired fashion. Six native edits use the corresponding original as their sole reference, preserving recognizable adult identity and pose. Each 1024×1536 PNG and exact prompt is retained and individually inspected. A1-W3 and C1-W3 are assistant refinement suggestions only; user selection is pending. All original PNGs/prompts, E1 and the licensed sample VRM are preserved. New wardrobe concepts do not add runtime clothing, rigs or animation. Compare these outfits before targeted side/back work; E1 expression feedback remains outstanding.\n\nThe following paragraphs retain the dated development of the art brief.')
replace('design/desk-companion/characters/a1-character-brief.md','# A1 Character Brief · Working v1','# A1 Character Brief · Working v2')
replace('design/desk-companion/characters/a1-character-brief.md','Group 2 · 2026-10-10。','Group 2 · 更新2026-10-12，性格基线始于2026-10-10。')
replace('design/desk-companion/characters/a1-character-brief.md','- **服装：**象牙白短外套、石墨高领内层、蓝灰叠片短裙、半透深灰连裤袜和短靴。以[保留稿V4](2026-10-10-concepts/a1-silver-mist-anime-v4.png)作连续性参考，原稿不覆盖。','- **服装：**[保留稿V4](2026-10-10-concepts/a1-silver-mist-anime-v4.png)的浅外套／深内层／蓝灰裙／深灰袜是原基准。用户10月12日授权完整换装、拓展都市以外风格；现有[柔科技机能、轻户外、星旅轻奇幻三版](2026-10-12-wardrobe-variants/README.md)，均待比较选型。V4固定身份与画风参考，衣服不再限制为原组合；原PNG与提示词不覆盖。')
replace('design/desk-companion/characters/a1-character-brief.md','下一步先根据E1的脸部连续性与表情反馈微调，再制作侧面／背面规范；','当前先比较A1与C1的[六套服装](2026-10-12-wardrobe-variants/README.md)，再按选定方向细化侧面／背面；E1的脸部连续性与表情反馈仍保留。')
replace('design/desk-companion/characters/a1-expression-rules.md','Group 2 · 2026-10-10。','Group 2 · 更新2026-10-12，表情／性格规则始于2026-10-10。')
replace('design/desk-companion/characters/a1-expression-rules.md','- 保留象牙白短外套、石墨色高领内层、蓝灰叠片短裙、半透深灰连裤袜与短靴的方向；服装全身版本以[保留稿V4](2026-10-10-concepts/a1-silver-mist-anime-v4.png)作为本次连续性参考，未宣布V4最终定稿。','- 原E1以[保留稿V4](2026-10-10-concepts/a1-silver-mist-anime-v4.png)服装作连续性参考；10月12日用户授权探索都市以外的新衣服，现有[六套独立服装对照](2026-10-12-wardrobe-variants/README.md)。全身服装允许变化，脸／头发／配饰和本页性格／表情规则继续保留，最终服装尚未选定。')
replace('design/desk-companion/characters/a1-expression-rules.md','- 本次表情图只画头肩，完整服装继续由五版原稿记录。图中不出现裙袜不代表删去既有服装要求。','- 原E1只画头肩，其服装是当时V4基准的历史记录。新的服装选择由10月12日全身对照承担，图中不出现裙袜不能推断本轮全身衣物结构。')
replace('design/desk-companion/characters/a1-expression-rules.md','先检查同一人物的连续性、中性脸气质和六表情差异，再依据反馈修订表情／侧面／背面规范。','当前先比较新服装方向；同一人物的连续性、中性脸气质和六表情差异仍待反馈，再依据选定造型修订表情／侧面／背面规范。')
route='**2026-10-12当前路由：**用户要求A1 V4与C1各尝试不同风格的服装，不限都市上班族；[六套独立换装与并排预览](../2026-10-12-wardrobe-variants/README.md)已完成。下文保留本目录10月10日阶段记录；原PNG／提示词／manifest不覆盖。当前先比较六套服装，用户尚未选定最终造型。'
for path in ['design/desk-companion/characters/2026-10-10-concepts/README.md','design/desk-companion/characters/2026-10-10-c1-concept/README.md','design/desk-companion/characters/2026-10-10-expression-study/README.md']:
    prefix_current(path,route)
replace('design/desk-companion/characters/2026-10-10-c1-concept/README.md','下一步比较A1与C1，再按用户反馈细化选定方向；','当前先比较10月12日六套新服装，再按用户反馈细化选定方向；')
replace('design/desk-companion/characters/2026-10-10-expression-study/README.md','下一步先收集E1的脸型／连续性和表情反馈，定向微调倾听与开心、关切的强度，再补侧面／背面规范；','当前先比较10月12日的新服装；E1的脸型／连续性和表情反馈保留，后续定向微调倾听／开心／关切，再补选定造型的侧背面；')
research_route='**当前状态（2026-10-12）：**用户要求A1 V4与C1各探索不同风格服装、不限都市上班族；[六张独立原生换装与并排预览](../../design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md)已完成并逐张检查。当前先比较六套，再细化选定方向；A1性格基线、原五版、E1与C1原稿／提示词及运行许可模型保持。以下原研究的日期、来源与访问范围保留，不是本轮重做人气评估。'
for path in ['research/2026-10-10-avatar-art/popular-character-study.md','research/2026-10-10-avatar-art/wardrobe-study.md','research/2026-10-10-avatar-art/japanese-character-study.md']:
    p=ROOT/path; s=p.read_text(); start=s.index('\n\n')+2; end=s.index('\n\n',start)
    p.write_text(s[:start]+research_route+s[end:]); changed.append(path)
prefix_current('research/2026-10-10-avatar-art/mainstream-anime-c1-study.md',research_route)
replace('research/2026-10-10-avatar-art/mainstream-anime-c1-study.md','下一步对照A1与C1的脸部、发型轮廓、服装和长期相处的气质，按用户反馈再细化。','10月12日已按用户新指令完成A1／C1六套服装；当前对照这些新款，按反馈再细化。')
replace('research/2026-10-10-avatar-art/character-concepts.md','2026年10月10日。','更新2026年10月12日；原概念始于10月10日。')
replace('research/2026-10-10-avatar-art/character-concepts.md','E1是一张独立的头肩表情研究，不是全身V5，未覆盖旧稿或替换模型。当前先比较A1与C1，再按用户反馈细化选定方向。','E1是一张独立的头肩表情研究，不是全身V5，未覆盖旧稿或替换模型。10月12日已完成[六套服装再设计](../../design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md)：A1柔科技／轻户外／轻奇幻，C1舞台／运动休闲／现代和风。当前先比较六套，再细化选定方向。')
handoff='''# Group 2 Current Handoff

更新：2026-10-12。当前：**A1 V4与C1各三套服装再设计已完成，六张均有效并已逐张查看；待比较选型。** 用户要求不同风格、不要只做都市上班族；脸／头发／眼睛／配饰及原稿保留。

## 当前产物与证据

- [六版原图、完整提示词和比较说明](design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md)／[并排预览](design/desk-companion/characters/2026-10-12-wardrobe-variants/review-board.html)。A1-W1柔科技机能、W2轻户外、W3星旅轻奇幻；C1-W1音乐舞台、W2运动休闲、W3现代和风。
- 六次内置ImageGen编辑，每项以对应原稿为唯一参考，1024×1536，均1次成功。协调代理实际查看全部六张：主要身份稳定、头手鞋完整、衣物结构可读；方跟、垂片及边饰偏差见[清单](design/desk-companion/characters/2026-10-12-wardrobe-variants/manifest.json)。无像素后期，原生与项目文件逐字节一致。
- 助手优先建议A1-W3与C1-W3进一步细化；属于视觉判断，用户未选择最终款。A1性格／六表情规则继续，衣服允许按本轮授权探索。[本轮QA](output/qa/2026-10-12-wardrobe-variants/verification.md)包含139份／12,884行全文阅读、来源、保护及链接检查。

## 保留状态与未完成项

[A1五版](design/desk-companion/characters/2026-10-10-concepts/README.md)、[E1](design/desk-companion/characters/2026-10-10-expression-study/README.md)、[C1原稿](design/desk-companion/characters/2026-10-10-c1-concept/README.md)及全部旧PNG／提示词不覆盖。服装选型、E1表情反馈、侧背面与原创VRM／绑定未完成；应用仍用pixiv许可样本。本轮只本地保存，无Git写入或运行时更改。

[第2份v5日志DOCX](<output/submission/2026-10-11/AY26_Logsheet_No2_Group 2_YuanYuchen_250342840.docx>)／[PDF](<output/submission/2026-10-11/AY26_Logsheet_No2_Group 2_YuanYuchen_250342840.pdf>)保持；[制作记录](planning/2026-10-11/logsheet-2-review.md)中的个人工作归属／下期计划仍供成员复核。本轮没有核实Moodle当前提交状态，也没有签署、上传或对外联系。

软件证据仍见[3D QA](output/qa/2026-10-09-3d-avatar/verification.md)及[Dot QA](output/qa/2026-10-09-dot-integration/verification.md)。远端音量／逐音素、真实语音／AEC／费用、Pi／iPhone／光学、PC／LCU、真人姿态及RIG实物仍需实现或实测，不以PNG概念代替。

## 唯一下一步

**根据六套服装的比较反馈收敛A1／C1造型，再细化选定款的侧背面及可制作结构。** 原稿持续保留，不把助手推荐当成用户选型。
'''
(ROOT/'handoff.md').write_text(handoff); changed.append('handoff.md')
with (ROOT/'decision-log.md').open('a') as f:
    f.write('''\n## 2026-10-12 A1 V4与C1服装多风格再设计\n\n- **用户决定：**为A1 V4与C1再设计几版，尝试不同风格，不局限都市上班族。取代此前本阶段“保持原服装”的限制；没有取消A1性格基线或选择C1取代A1。\n- **工程美术安排：**两位各三套：[A1柔科技机能／轻户外／星旅轻奇幻；C1音乐舞台／运动休闲／现代和风](design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md)。各自原稿为唯一参考，身份／姿态尽量保持，衣服袜鞋完整重设计。\n- **实际结果：**六张1024×1536原生PNG，三个限定图像代理各顺序两次内置ImageGen；均首次成功，协调代理逐张查看，原PNG／实际提示词／来源hash保存，无像素后期。垂片、边饰及鞋跟等偏差按实际记录。\n- **建议与选型：**助手建议优先细化A1-W3与C1-W3，是本轮视觉判断；用户尚未选定。当前先比较六款，再补选定方向侧背面；E1反馈仍待。\n- **边界：**旧五版、E1、C1原PNG与提示词保留；不替换运行许可模型或改应用／学校文件，不代表原创VRM、衣物绑定或目标设备效果完成。本轮本地保存、未Git写入。\n''')
changed.append('decision-log.md')
replace('work-log.md','更新：2026-10-11。','更新：2026-10-12。')
with (ROOT/'work-log.md').open('a') as f:
    f.write('''\n## 2026-10-12 A1 V4／C1六套服装再设计\n\n- **目标：**按用户要求为两位各尝试不同风格服装，超出都市上班族；保持原角色身份并保留原稿。\n- **开工：**139份项目自有Markdown／12,884行、59批全文，包含历史研究与规划；最初组合输出截断后分别补读，阅读期间hash未变。压缩恢复沿用记录，未重启。[本轮范围](output/qa/2026-10-12-wardrobe-variants/reading-record.json)。\n- **产物：**[六图与实际提示词](design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md)：A1柔科技机能／轻户外／星旅轻奇幻，C1音乐舞台／运动休闲／现代和风。六张1024×1536，各一次内置ImageGen编辑，以对应原稿为唯一参考，原生与项目PNG字节一致，无像素后期或无效图重试。\n- **工具：**Creative Production明确要求多图委派，三个限定代理各顺序两图；终态结果已消费并用中断接口确认，无销毁句柄API，不冒称销毁。仅嵌套画板工具可见而技能禁止该路由，未挂载原生画板；共享renderer生成静态并排检查页，无派生拼图。\n- **视觉检查：**协调代理使用view_image逐张查看全部六张，主要身份／姿态稳定、成年观感、完整头手鞋和衣物结构通过；柔和渐变、方跟、垂片／边饰复杂度按实际说明。助手优先建议A1-W3与C1-W3，不是用户选择或人气成绩。\n- **同步与验证：**product、两个README、avatar契约、A1简报／规则、原资产目录的当前路由、五份美术研究入口、decision-log和handoff同步；[QA](output/qa/2026-10-12-wardrobe-variants/verification.md)记录6张元数据／hash、原稿／提示词／许可VRM／学校文件保护、本地链接及预览。纯美术任务不重跑应用套件或DOCX渲染。\n- **剩余与边界：**用户比较后收敛服装，再细化侧背面／可制作结构；E1反馈和原创模型尚未完成。原学校日志与此前未提交工作保持，本轮没有Git写入、运行时／硬件动作、语音消费、采购、签署、Moodle操作或对外联系。\n''')
changed.append('work-log.md')
import json
q=ROOT/'output/qa/2026-10-12-wardrobe-variants'
(q/'updated-norms.json').write_text(json.dumps(sorted(set(changed)),ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'updated_markdown':len(set(changed)),'paths':sorted(set(changed))},ensure_ascii=False,indent=2))
