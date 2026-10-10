# -*- coding: utf-8 -*-
"""One-use closeout of the A1 brief / E1 art phase; raw assets are untouched."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json

ROOT=Path(__file__).resolve().parents[3]
def para(path,prefix,text):
 p=ROOT/path;s=p.read_text();found=[v for v in s.split('\n\n') if v.startswith(prefix)];assert len(found)==1,(path,prefix);p.write_text(s.replace(found[0],text))
def once(path,old,new):
 p=ROOT/path;s=p.read_text();assert s.count(old)==1,(path,old);p.write_text(s.replace(old,new))

once('product.md','**A1方向保持，五版概念及提示词原样保留；日本动漫形象／刻画研究已完成，新的性格与表情建议待评审；全身3D功能仍用原许可样本，Dot整合已在main**','**用户同意A1简报方向；角色简报／六表情规则与E1对照已完成，E1待图像反馈；五版原稿保留，运行角色仍用原许可样本**')
para('product.md','A/B首轮各生成一张','A/B首轮各生成一张1024×1536全身概念，随后用户选择A1并连续降低写实度，形成V2／V3／V4。[原五版与提示词](design/desk-companion/characters/2026-10-10-concepts/README.md)均保留；[日本动漫六角色研究](research/2026-10-10-avatar-art/japanese-character-study.md)及13来源在研究阶段完成。用户随后明确同意按建议推进，安静、敏锐、可靠、熟悉后轻巧幽默成为当前性格工作基线，非最终角色名称／声音／模型定稿。')
para('product.md','现有pixiv VRM与应用代码保持。','[简明角色简报](design/desk-companion/characters/a1-character-brief.md)、[六表情／表演规则](design/desk-companion/characters/a1-expression-rules.md)与[六表情对照E1](design/desk-companion/characters/2026-10-10-expression-study/README.md)已完成。E1以实际查看的V4为唯一参考，一次内置ImageGen生成1536×1024头肩对照；原图、完整提示词和hash保留，无像素后期。倾听与开心差异仍小，关切略偏担忧；E1待图像反馈，不是全身V5或已绑定表情。下一步据E1反馈定向微调，再补侧背面规范。应用／pixiv VRM保持，真实语音、Pi并发与光学效果仍需另验。')
para('README.md','**Character art (10 October):**','**Character art (10 October):** The user accepted the A1 character-brief direction after the Japanese anime study. The [concise brief](design/desk-companion/characters/a1-character-brief.md), [expression/acting rules](design/desk-companion/characters/a1-expression-rules.md) and [six-expression E1 sheet](design/desk-companion/characters/2026-10-10-expression-study/README.md) are complete. One native ImageGen call used V4 as the sole continuity reference; original PNG, prompt and provenance are retained. Listening/Joy remain close and Care leans toward worry, so E1 awaits visual feedback. All five original concepts and prompts are unchanged. E1 is a separate head-and-shoulder study, not full-body V5, a rigged asset or a runtime replacement. The [six-character research](research/2026-10-10-avatar-art/japanese-character-study.md) remains available.')
para('desk-companion/README.md','**2026-10-10美术状态：**','**2026-10-10美术状态：**用户同意A1方向后的[简明角色简报](../design/desk-companion/characters/a1-character-brief.md)、[表情／表演规则](../design/desk-companion/characters/a1-expression-rules.md)与[六表情E1](../design/desk-companion/characters/2026-10-10-expression-study/README.md)已完成。E1待图像反馈；原A1 V1–V4及B1／五提示词保持，许可样本与程序没有替换。')
once('desk-companion/docs/avatar.md','A2/B2, turnarounds and expression sheets are not generated.','A2/B2 and turnarounds are not generated. A separate six-expression E1 concept sheet is now available; rigged expression assets are not made.')
para('desk-companion/docs/avatar.md','The user now explicitly retained','The user retained all five concepts and accepted the Japanese-anime study recommendations as the A1 working direction. The [concise brief](../../design/desk-companion/characters/a1-character-brief.md) and [expression/acting rules](../../design/desk-companion/characters/a1-expression-rules.md) specify calm, perceptive, reliable behavior with occasional light humor. One native ImageGen call produced the [E1 six-expression sheet](../../design/desk-companion/characters/2026-10-10-expression-study/README.md) from the sole V4 reference. Raw output, actual prompt and hashes are preserved; all previous art is unchanged. Listening/Joy remain close and Care leans toward worry. E1 awaits visual feedback and is neither a full-body V5 nor a rigged/runtime asset. The next step is targeted visual refinement before side/back views. These rules do not add implemented animation, provider configuration or tool permissions; existing runtime and voice/device validation boundaries remain unchanged.')

once('design/desk-companion/characters/2026-10-10-concepts/README.md','**A1_SELECTED / ALL_FIVE_VERSIONS_PRESERVED / JAPANESE_CHARACTER_STUDY_COMPLETE / FINAL_CHARACTER_PENDING**','**A1_BRIEF_WORKING_V1 / ALL_FIVE_VERSIONS_PRESERVED / E1_VISUAL_REVIEW_PENDING**')
para('design/desk-companion/characters/2026-10-10-concepts/README.md','均为1024×1536原生ImageGen结果。','均为1024×1536原生ImageGen结果。来源／SHA／实际编辑输入见[manifest](manifest.json)。用户已同意研究后的工作方向，现有[简明角色简报](../a1-character-brief.md)、[表情规则](../a1-expression-rules.md)及另存的[六表情E1](../2026-10-10-expression-study/README.md)。E1待图像反馈，以上五版继续原样保留；头肩表情图不命名为全身V5，应用仍用原许可样本。')
p=ROOT/'design/desk-companion/characters/2026-10-10-concepts/manifest.json';m=json.loads(p.read_text());m.update(state='A1 working brief accepted; all five originals preserved; separate E1 expression study awaits visual feedback',current_phase='Character brief and six-expression E1 complete, runtime unchanged',character_brief_path='design/desk-companion/characters/a1-character-brief.md',expression_rules_path='design/desk-companion/characters/a1-expression-rules.md',expression_study_path='design/desk-companion/characters/2026-10-10-expression-study/manifest.json',updated_at=datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat());p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')

para('research/2026-10-10-avatar-art/character-concepts.md','2026年10月10日。用户要求先保留','2026年10月10日。A1 V1／V2／V3／V4和B1原PNG、五份提示词继续原样保留。用户已同意研究后的建议；[角色简报](../../design/desk-companion/characters/a1-character-brief.md)、[详细规则](../../design/desk-companion/characters/a1-expression-rules.md)及另存的[六表情E1](../../design/desk-companion/characters/2026-10-10-expression-study/README.md)已完成。E1待图像反馈，具体最终造型未定。')
para('research/2026-10-10-avatar-art/character-concepts.md','本轮没有生成V5','E1是一张独立的头肩表情研究，不是全身V5，未覆盖旧稿或替换模型。下一步据E1反馈细化脸部与表情，再补侧背面规范。原生成和研究过程见资产索引及各阶段QA。')
p=ROOT/'research/2026-10-10-avatar-art/japanese-character-study.md';s=p.read_text();idx=s.index('\n\n');s=s[:idx]+'''\n\n**当前推进：**用户已同意研究后的建议。[简明角色简报](../../design/desk-companion/characters/a1-character-brief.md)、[六表情／表演规则](../../design/desk-companion/characters/a1-expression-rules.md)与[独立E1对照](../../design/desk-companion/characters/2026-10-10-expression-study/README.md)已完成，E1待图像反馈。以下是此前研究阶段记录，“本轮只研究”等表述仅指该阶段；原五版持续保留，研究访问范围不变。
'''+s[idx:];p.write_text(s)
for name in ['popular-character-study.md','wardrobe-study.md']:
 para('research/2026-10-10-avatar-art/'+name,'**当前状态（2026-10-10）：**','**当前状态（2026-10-10）：**用户同意日本动画研究后的A1工作方向；[角色简报](../../design/desk-companion/characters/a1-character-brief.md)、[表情规则](../../design/desk-companion/characters/a1-expression-rules.md)与[六表情E1](../../design/desk-companion/characters/2026-10-10-expression-study/README.md)已完成。E1待图像反馈，原五版保留，VRM未替换；以下历史研究的旧下一步由此取代。')

p=ROOT/'decision-log.md';p.write_text(p.read_text()+'''\n## 2026-10-10 用户接受A1简报方向与六表情E1

- **用户决定：**“可以，就按照你的建议来”，承接日本动画研究后的简报、六表情与后续定向设计建议。安静／敏锐／可靠／熟悉后轻巧幽默成为工作基线；不等于自动选定尚未生成的图、正式名字或声音。
- **实际完成：**[简明简报](design/desk-companion/characters/a1-character-brief.md)与[表情／表演规则](design/desk-companion/characters/a1-expression-rules.md)保存；实际查看V4后，用内置ImageGen一次生成[六表情E1](design/desk-companion/characters/2026-10-10-expression-study/README.md)，1536×1024，保留原PNG、提示词、输入与hash，无像素后期。
- **观察与下一步：**身份／配色基本连续，疑问与思考清楚；倾听与开心仍接近，关切略偏担忧。E1待图像反馈，先定向调整，再补侧背面规范。
- **取代关系：**取代“性格建议尚未接受、下一步先写简报”的当前状态。研究阶段的未生成记录保持历史日期；E1独立于全身V1–V4，不叫全身V5。原五PNG／五提示词／应用与模型保持，不增加已实现的动画或工具权限，不合并main。
''')
(ROOT/'handoff.md').write_text('''# Group 2 Current Handoff

更新：2026-10-10。当前：**用户同意A1简报方向；简报／六表情规则与E1图已完成，E1待图像反馈。** 分支`codex/full-body-3d-avatar`／[PR #4](https://github.com/tantalum666/FYP/pull/4)，main保持Dot整合。

## 当前成果与证据

[简明角色简报](design/desk-companion/characters/a1-character-brief.md)／[表情与表演规则](design/desk-companion/characters/a1-expression-rules.md)：安静、敏锐、可靠，熟悉后轻巧幽默；保留银发／灰蓝眼／开环发扣及既有服装，表达跟随真实交互与回执。

[六表情E1](design/desk-companion/characters/2026-10-10-expression-study/README.md)：以实际查看的V4为唯一参考，一次内置ImageGen生成1536×1024头肩对照；原图、完整提示词和来源／SHA保留，无像素后期。疑问／思考更清楚，倾听与开心仍近，关切稍偏担忧。E1是独立研究图，未最终定稿、不是全身V5或绑定表情。

[原五版](design/desk-companion/characters/2026-10-10-concepts/README.md)与五提示词保持；[日本动画研究](research/2026-10-10-avatar-art/japanese-character-study.md)及13来源保留。[本轮QA](output/qa/2026-10-10-a1-character-brief/verification.md)继承阅读链，核对原图／提示词、E1原生身份、107保护文件、VRM、程序与本地链接。实际程序证据仍为[3D QA](output/qa/2026-10-09-3d-avatar/verification.md)及[Dot QA](output/qa/2026-10-09-dot-integration/verification.md)，本轮未重跑或改写。

## 唯一下一步

**依据E1图像反馈定向微调脸部／表情，随后补侧面／背面规范。**不自动把概念替换应用或合并main。许可样本与代码保持；逐音素／远端音量、真实语音／AEC／费用、Pi／iPhone／光学、PC／LCU、长期记忆、作业归档／备份、真人姿态、RIG／清洁及物理停止仍待完成或实测。
''')
print('Current art docs synchronized; original PNGs/prompts/runtime untouched.')
