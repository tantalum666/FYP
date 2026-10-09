# -*- coding: utf-8 -*-
from pathlib import Path
import json
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[3]
def replace(path,old,new):
 p=ROOT/path;s=p.read_text();assert s.count(old)==1,(path,s.count(old));p.write_text(s.replace(old,new))
def paragraph(path,prefix,text):
 p=ROOT/path;s=p.read_text();matches=[v for v in s.split('\n\n') if v.startswith(prefix)];assert len(matches)==1,(path,matches);p.write_text(s.replace(matches[0],text))

paragraph('README.md','**Character art (10 October):**','**Character art (10 October):** A1 remains the selected working direction. All five concepts (A1 V1–V4 and B1) and their five prompts are preserved unchanged. The user requested a further study of Japanese anime appearance and characterization before more edits. The [new study](research/2026-10-10-avatar-art/japanese-character-study.md), [illustrated board](research/2026-10-10-avatar-art/japanese-character-board.html) and [13-source record](research/2026-10-10-avatar-art/japanese-character-sources.json) cover six characters and primary acting / production interviews. Proposed A1 personality, expression and motion rules remain recommendations; no final character, V5 or replacement runtime model is made. [Version index](design/desk-companion/characters/2026-10-10-concepts/README.md).')
replace('product.md','**用户选择A1方向；平涂二次元V4已生成、待审阅；全身3D功能仍用原许可样本，Dot整合已在main**','**A1方向保持，五版概念及提示词原样保留；日本动漫形象／刻画研究已完成，新的性格与表情建议待评审；全身3D功能仍用原许可样本，Dot整合已在main**')
paragraph('product.md','A/B首轮各生成一张','A/B首轮各生成一张1024×1536全身概念，随后用户选择A1并连续要求降低写实度，形成V2／V3／V4。[五版与完整提示词](design/desk-companion/characters/2026-10-10-concepts/README.md)均逐字节保留。用户最新要求先保留几版，再研究日本动漫人物的形象与刻画；本轮完成[六角色研究](research/2026-10-10-avatar-art/japanese-character-study.md)、[图文板](research/2026-10-10-avatar-art/japanese-character-board.html)与13个来源记录。A1仍为工作方向，保留不等于否定V4或最终定稿；本轮没有继续生成或修改原图。')
paragraph('product.md','现有pixiv VRM与应用代码保持；下一步','现有pixiv VRM与应用代码保持。下一步建议先评审A1的一页性格／外形简报和六种表情规则，再依据具体反馈制作视图／表情。研究中的安静、敏锐、可靠与轻巧幽默是建议，不是用户已选性格；PNG不等于骨骼、贴图或可运行模型。现实D数不直接换算透明度；Pi并发、衣物穿插、语音桥和物理显示仍需实际验证。')
replace('desk-companion/README.md','详见[3D角色契约](docs/avatar.md)。','详见[3D角色契约](docs/avatar.md)。\n\n**2026-10-10美术状态：**A1 V1–V4及B1与五份提示词原样保留；[日本动画形象／刻画研究](../research/2026-10-10-avatar-art/japanese-character-study.md)与[图文板](../research/2026-10-10-avatar-art/japanese-character-board.html)已完成。A1保持工作方向，性格／六种表情建议待评审，本轮未生成新图或替换模型。')
paragraph('desk-companion/docs/avatar.md','The next art step is refinement','The user now explicitly retained all five concepts (A1 V1–V4 and B1) and requested Japanese anime appearance and characterization research. The [six-character study](../../research/2026-10-10-avatar-art/japanese-character-study.md), [visual board](../../research/2026-10-10-avatar-art/japanese-character-board.html) and [source record](../../research/2026-10-10-avatar-art/japanese-character-sources.json) are complete. A1 remains the working direction; no version is rejected or finalized by this preservation request. Proposed personality, six expressions and purposeful state transitions are art recommendations, not implemented animation or new tool permissions. The next suggested step is review of a concise A1 brief before further edits / turnarounds. All original PNGs and prompts are unchanged; no V5, runtime model or code was made this phase. Device and voice-bridge validation boundaries remain unchanged.')

asset=ROOT/'design/desk-companion/characters/2026-10-10-concepts/README.md'
s=asset.read_text();history=s[s.index('以下为首轮历史记录：'):];history=history[:history.index('当前下一步是')]
asset.write_text('''# Group 2｜角色概念版本索引

2026年10月10日。当前：**A1_SELECTED / ALL_FIVE_VERSIONS_PRESERVED / JAPANESE_CHARACTER_STUDY_COMPLETE / FINAL_CHARACTER_PENDING**。

用户要求保留几版，继续研究日本动漫形象与刻画。本轮五张PNG及五份提示词hash完全一致，没有重生成、像素修改或覆盖。A1仍为工作方向；V4、其他A1稿和B1均保留，具体最终版本未定。

| 版本 | 原PNG | 实际完整提示词 | 用途与主要变化 |
|---|---|---|---|
| A1 V1 | [银雾原稿](a1-silver-mist-v1.png) | [prompt](a1-prompt.txt) | 初始半写实3D概念，保留服装／身份线索 |
| A1 V2 | [二次元V2](a1-silver-mist-anime-v2.png) | [prompt](a1-anime-v2-prompt.txt) | 强化动漫脸、线条与赛璐璐明暗 |
| A1 V3 | [平涂V3](a1-silver-mist-anime-v3.png) | [prompt](a1-anime-v3-prompt.txt) | 减少衣物、丝袜和鞋的渐变，脸接近V2 |
| A1 V4 | [小幅微调V4](a1-silver-mist-anime-v4.png) | [prompt](a1-anime-v4-prompt.txt) | 色调进一步收敛，背景仍有轻微渐变，脸／服装／姿态接近V3 |
| B1 V1 | [墨青原稿](b1-ink-teal-v1.png) | [prompt](b1-prompt.txt) | 都市剪裁对照；保留为历史候选 |

均为1024×1536原生ImageGen结果。来源／SHA／实际编辑输入见[manifest](manifest.json)。[日本动画研究](../../../../research/2026-10-10-avatar-art/japanese-character-study.md)及[图文参考板](../../../../research/2026-10-10-avatar-art/japanese-character-board.html)已完成；下一步建议先评审A1性格与六种表情规则。研究建议不是新定稿。PNG不等于三视图、绑定、动画或VRM，应用仍用原许可样本。

## HISTORICAL：首轮生成与审阅

'''+history+'\n')
manifest=asset.with_name('manifest.json');m=json.loads(manifest.read_text());m.update(state='All five images and prompts preserved; Japanese anime study complete; final art pending',current_direction='A1 remains selected; character and expression recommendations await review',current_phase='Research completed without further generation or pixel edits',preserved_assets=['A1','A1-v2','A1-v3','A1-v4','B1'],research_path='research/2026-10-10-avatar-art/japanese-character-study.md',updated_at=datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat());manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')

(ROOT/'research/2026-10-10-avatar-art/character-concepts.md').write_text('''# Group 2｜五版角色概念保留

2026年10月10日。用户要求先保留现有版本，再研究日本动漫人物。**A1 V1／V2／V3／V4和B1原PNG、五份实际提示词全部保留，hash一致。**A1为已选工作方向，具体最终造型未定；保留不等于废弃V4。

- [完整五版索引、原图与提示词](../../design/desk-companion/characters/2026-10-10-concepts/README.md)。
- [最近生成的A1 V4](../../design/desk-companion/characters/2026-10-10-concepts/a1-silver-mist-anime-v4.png)：小幅压平衣物／丝袜色调，脸、服装、站姿接近V3，背景仍有轻微渐变。
- [日本动画形象／刻画研究](japanese-character-study.md)与[图文板](japanese-character-board.html)：六角色、官方图和原始制作／配音访谈。

本轮没有生成V5、像素编辑或覆盖旧稿。新的外形、性格与表情规则属于建议；下一步先评审一页A1简报，再依据反馈制作视图／表情与3D资产。应用代码与原许可模型保持。
''')

for name in ['popular-character-study.md','wardrobe-study.md']:
 p=ROOT/'research/2026-10-10-avatar-art'/name;s=p.read_text();first=s.index('\n\n');s=s[:first]+'''\n\n**当前状态（2026-10-10）：**用户要求原样保留A1 V1–V4及B1，继续研究日本动画的形象与刻画。[本轮研究](japanese-character-study.md)／[图文板](japanese-character-board.html)已完成；A1工作方向保持，下一步先评审性格／六种表情简报。没有生成新图或替换VRM。

## HISTORICAL：此前的人气／方向或服装研究

以下正文保留当时的研究与建议；其中的后续生成顺序已由上方当前状态取代。
'''+s[first:];p.write_text(s)
for name in ['reference-board.html','wardrobe-reference-board.html']:
 p=ROOT/'research/2026-10-10-avatar-art'/name;s=p.read_text();needle='<body>';assert needle in s;s=s.replace(needle,needle+'<aside style="padding:14px 24px;background:#ecebe3;color:#303a3e;font:14px/1.5 sans-serif">HISTORICAL · 首轮方向／服装研究。现有五版已保留，当前进入日本动画形象与刻画研究。<a href="japanese-character-board.html">查看最新研究板 ↗</a></aside>',1);p.write_text(s)

(ROOT/'handoff.md').write_text('''# Group 2 Current Handoff

更新：2026-10-10。当前：**五版概念原样保留；日本动画形象／性格刻画研究完成，A1建议待评审。** 分支`codex/full-body-3d-avatar`／[PR #4](https://github.com/tantalum666/FYP/pull/4)，main保持Dot整合。

## 当前成果与证据

[新研究](research/2026-10-10-avatar-art/japanese-character-study.md)／[图文参考板](research/2026-10-10-avatar-art/japanese-character-board.html)／[13个来源](research/2026-10-10-avatar-art/japanese-character-sources.json)：Vivy、约尔、宫森葵、常守朱、桃香、梅丽鲁，区分官方设定、实际视觉观察、原始访谈与A1设计建议。未完整观看剧集或试听访谈。

[五版索引](design/desk-companion/characters/2026-10-10-concepts/README.md)包含A1 V1–V4与B1、五份提示词和来源／SHA。本轮hash一致，未生成V5、编辑像素或替换模型。A1仍为工作方向，保留不等于否定V4或最终定稿。安静／敏锐／可靠／轻巧幽默及六种表情只是建议。

[本轮QA](output/qa/2026-10-10-japanese-character-study/verification.md)沿用同一美术任务128文件全读与补读链，记录当前补读、来源访问、八张参考图实际加载、研究板查看、资产／107保护项／代码／VRM与链接检查。应用验证仍见[3D QA](output/qa/2026-10-09-3d-avatar/verification.md)和[Dot QA](output/qa/2026-10-09-dot-integration/verification.md)，不因研究重跑或改写。

## 唯一下一步

**先评审一页A1性格／外形简报及六种表情规则，再依据明确反馈制作视图／表情。**本轮只研究，不自动出新稿或合并main。原应用及许可样本保持；逐音素／远端音量、真实语音／AEC／费用、Pi／iPhone／光学、PC／LCU、长期记忆、作业归档／备份、真人姿态、RIG／清洁及物理停止仍待完成或实测，研究不取代这些验证。
''')

p=ROOT/'decision-log.md';p.write_text(p.read_text()+'''\n## 2026-10-10 同一美术任务：保留五版与日本动画刻画研究

- **用户决定：**先保留几版，再研究日本动漫人物的形象与刻画。A1方向继续；不解释为否定V4、恢复B并列主选或批准新造型。
- **实际完成：**A1 V1–V4与B1、五份提示词hash一致；[六角色研究](research/2026-10-10-avatar-art/japanese-character-study.md)、图文板、13来源完成。官方设定、版本、实际观察与本组推论分开；检查六官方角色视觉、宫森葵表情图及Orange视角示意，未完整观看动画／试听访谈。
- **研究建议：**下一轮先明确A1性格与六种表情，通过有原因的反应、姿态与语气表现身份；保留银发／既有服装方向。可靠、安静、敏锐与轻巧幽默尚未由用户最终选定。
- **取代关系及边界：**取代上一条“立即据V4反馈继续精修”的当前下一步，先进行研究／简报评审。没有V5、像素修改、模型／代码／学校变更；沿既有功能分支／PR保存，不自动合并main。
''')
print('Updated current docs, historical entry notices and concept manifest; raw art and prompts untouched.')
