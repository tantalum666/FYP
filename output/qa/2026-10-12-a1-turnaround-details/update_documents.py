"""Update current art routing while retaining dated research and source assets."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
changed = set()


def replace(path, old, new):
    file = ROOT / path
    text = file.read_text()
    assert text.count(old) == 1, (path, old[:100], text.count(old))
    file.write_text(text.replace(old, new))
    changed.add(path)


def line(path, prefix, new):
    text = (ROOT / path).read_text()
    matches = [s for s in text.splitlines() if s.startswith(prefix)]
    assert len(matches) == 1, (path, prefix, len(matches))
    replace(path, matches[0], new)


def append(path, text):
    file = ROOT / path
    file.write_text(file.read_text().rstrip() + '\n\n' + text.strip() + '\n')
    changed.add(path)


art = 'design/desk-companion/characters/'
archive = 'output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip'
qa = 'output/qa/2026-10-12-a1-turnaround-details/'

line('product.md', '更新：2026-10-12。状态：', '更新：2026-10-12。状态：**A1角色已确定；九套服装原图／提示词已单独打包；六个全身视角与四张细节图完成；默认服装待选，运行角色仍为许可样本**。')
replace('product.md', 'A1可据E1反馈定向微调，再补侧背面规范。', '当时拟先据E1反馈微调再补侧背面；10月12日新指令已先推进视角和细节，E1精修仍待。')
replace('product.md', '当前从A1九套收敛服装，再细化选定款侧背面与可制作结构；E1反馈保留。', '该阶段原计划先从九套收敛服装；用户随后要求先保存服装并制作全方位／细节图，当前顺序以下节为准；E1反馈保留。')
section = '''## 2026-10-12 保留九套服装与A1全方位／细节

用户明确先保存这些服装，再做A1全方位形象图和细节图。九套服装原PNG／九份实际prompt、原V4参考和索引另存[九套原图包](output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)，21项包内字节读回一致；原素材目录保留。默认服装未选，沿用V4原服装仅为本轮一致的工程参考。

[六个全身视角与四张细节](design/desk-companion/characters/2026-10-12-a1-turnaround-details/README.md)已完成：正面、左右侧面、背面、前后斜视，以及脸／发扣、后发、服装剪裁、短靴／裤袜。先检查T01正面，再制作侧背面；T03检查后才用于后斜视及后发细节。十张原生PNG逐张查看，共11次内置ImageGen；T06首稿头身方向不一致，补充明确指令重试一次，首稿与实际prompt均保留。八张1024×1536、两张1254×1254，无像素后期。

发扣固定在人物自身左侧，右侧视角自然遮挡。T05／T06实际斜视角度偏浅，不称精确45度；严格侧面远侧手／鞋会自然重叠。原稿未展示的后发、外套背缝和裙后片为本轮新增设计提案，跨视角细部仍需统一，不能当作共享精确3D几何或已批准最终背面。当前按[视图工作规范](design/desk-companion/characters/a1-turnaround-spec.md)统一可制作参考；默认服装、E1精修和原创VRM／绑定仍分别待完成。[本次QA](output/qa/2026-10-12-a1-turnaround-details/verification.md)记录同任务阅读链、原图保存、十图检查及旧资产保护；学校和运行样本保持，本轮本地保存。

'''
replace('product.md', '## 已实现的软件范围\n', section + '## 已实现的软件范围\n')

line('README.md', '**A1 selected (12 October, current art step):**', '**A1 art (12 October, current step):** The user selected A1, then asked to preserve the outfits and proceed to all-around views and details. The [nine-outfit archive](' + archive + ') contains nine original PNGs, nine exact prompts, the V4 reference and index; all 21 members were verified byte-for-byte. [Six full-body views and four detail images](' + art + '2026-10-12-a1-turnaround-details/README.md) are complete and individually inspected. Original V4 clothing is the working continuity reference, while the default outfit remains unselected. Front/rear oblique angles are shallower than requested, and unseen rear construction is a new design proposal. The [wardrobe index](' + art + 'a1-wardrobe-index.md) and previous art remain available; the licensed runtime model is unchanged.')
line('desk-companion/README.md', '**2026-10-12当前美术步骤：**', '**2026-10-12当前美术步骤：**用户已确定A1，要求先保存服装再做全方位和细节。[九套原图包](../' + archive + ')已核对，原素材与提示词保留；[六个全身视角与四张细节](../' + art + '2026-10-12-a1-turnaround-details/README.md)完成并逐张查看，原V4服装只是统一工作参考。斜视角度偏浅、未见背部结构为新设计提案，具体默认服装仍待选。[视图规范](../' + art + 'a1-turnaround-spec.md)与[A1九套总索引](../' + art + 'a1-wardrobe-index.md)供后续；二维图不表示原创VRM／衣物绑定完成。')
line('desk-companion/docs/avatar.md', '**Current art step, 12 October:**', '**Current art step, 12 October:** A1 is the selected identity. The user asked to preserve all outfits, then create all-around views and details. The [nine-outfit archive](../../' + archive + ') preserves original PNGs and exact prompts; all 21 archive members were verified. [Six full-body views and four details](../../' + art + '2026-10-12-a1-turnaround-details/README.md) are complete and individually inspected, using original V4 clothing as an engineering continuity reference. There were 11 native ImageGen calls; T06 used one retry for head/body alignment. Front/rear oblique angles are shallow, and previously unseen rear construction is a new proposal rather than measured shared 3D geometry. The [view specification](../../' + art + 'a1-turnaround-spec.md) records these limits. The default outfit, E1 refinement, original VRM, rigs and clothing deformation remain pending. C1 is historical; original art and the licensed runtime sample remain unchanged.')
replace('desk-companion/docs/avatar.md', 'For A1, targeted visual refinement precedes side/back views.', 'At that stage, targeted refinement was planned before side/back views; the 12 October directive supersedes that order while E1 refinement remains pending.')

brief = art + 'a1-character-brief.md'
replace(brief, '# A1 Character Brief · A1 selected / Working v3', '# A1 Character Brief · A1 selected / Working v4')
line(brief, '- **服装：**', '- **服装：**[九套服装变体](a1-wardrobe-index.md)及实际prompt已经保留并单独打包，默认服装未选。[本轮六视角／四细节](2026-10-12-a1-turnaround-details/README.md)沿用原[V4](2026-10-10-concepts/a1-silver-mist-anime-v4.png)服装仅作一致的工作参考，不把它或W4／W6宣布为最终款。')
replace(brief, '本轮已完成[六表情E1]', '此前已完成[六表情E1]')
line(brief, '当前从[A1九套服装]', '当前完成[六个全身视角与四张细节](2026-10-12-a1-turnaround-details/README.md)，见[视图规范](a1-turnaround-spec.md)。发扣固定在人物自身左侧；背部未见结构为新增设计提案，斜视角度偏浅，下一步统一发束／衣缝／裹裙的可制作参考。默认服装与E1精修保留。C1为历史对照；二维参考不代表原创VRM、绑定或自然语音完成。依据见[日本动画研究](../../../research/2026-10-10-avatar-art/japanese-character-study.md)。')

expr = art + 'a1-expression-rules.md'
replace(expr, '## 本阶段交付与下一步', '## 2026-10-10表情交付与当前进度')
replace(expr, '交付[简明角色简报]', '10月10日交付[简明角色简报]')
line(expr, '当前先比较新服装方向；', '用户随后要求先保留九套服装，再制作[A1全方位与细节](2026-10-12-a1-turnaround-details/README.md)，十张二维参考已完成；[视图规范](a1-turnaround-spec.md)补充人物自身左侧发扣及后发／衣物背部设计提案。E1的倾听／开心／关切精修、默认服装和跨视角细部统一仍待，不能把新中性脸细节称为六表情修订完成。3D建模、表情形变、动画、真实语音与Pi／光学效果继续分别验收。')

wardrobe = art + 'a1-wardrobe-index.md'
replace(wardrobe, '**角色身份A1已由用户确定；具体默认服装未选定。**', '**角色身份A1已由用户确定；九套服装已保存打包；具体默认服装未选定。**')
replace(wardrobe, '侧背面、原创VRM与服装绑定仍待制作，运行时仍为许可样本。', '九套服装各自的侧背面和衣物工程仍待；本轮另用原V4服装完成角色视角参考，运行时仍为许可样本。')
line(wardrobe, '当前下一步：', '按用户最新要求，先把九套原PNG／九份实际prompt与V4身份参考另存[九套原图包](../../../' + archive + ')；包内21项读回一致，原文件保留。随后完成[六个全身视角与四张细节](2026-10-12-a1-turnaround-details/README.md)，原V4服装仅作工程参考。当前下一步是统一角色视图的发束、后背衣缝与裹裙结构；服装选型保留为独立后续事项。')

for directory in ['2026-10-10-concepts', '2026-10-10-c1-concept', '2026-10-10-expression-study']:
    path = art + directory + '/README.md'
    line(path, '**2026-10-12最新决定：**', '**2026-10-12最新决定：**A1为后续角色，C1历史保留。[九套服装](../a1-wardrobe-index.md)及实际prompt已另存[原图包](../../../../' + archive + ')；[六个全身视角与四张细节](../2026-10-12-a1-turnaround-details/README.md)已完成，采用V4原服装作工程参考，默认服装仍未选。以下是本目录原阶段记录；旧PNG／prompt／manifest保持。')
replace(art + '2026-10-10-concepts/README.md', '2026年10月10日。当前：', '2026年10月10日历史阶段。阶段状态：')
replace(art + '2026-10-10-concepts/README.md', '当前对照A1与C1，以上五版与E1原图／提示词保持。', '当时对照A1与C1；当前A1已确定并完成新视角参考，以上五版与E1原图／提示词保持。')
line(art + '2026-10-10-c1-concept/README.md', '当前推进A1服装与后续造型，', '当前推进A1视角细部统一，C1原稿保留；[QA](../../../../output/qa/2026-10-10-c1-mainstream-anime/verification.md)记录本目录当时素材、来源与Git交付。')
line(art + '2026-10-10-expression-study/README.md', '当前比较A1九套服装；', '当前已保留九套服装并完成A1视角／细节参考；E1脸型与表情反馈继续保留，后续定向微调倾听／开心／关切。新视角不表示E1已修订或替换到应用。验证见[原阶段QA](../../../../output/qa/2026-10-10-a1-character-brief/verification.md)。')
first = art + '2026-10-12-wardrobe-variants/README.md'
replace(first, '当前见[第二轮六套A1]', '服装入口见[第二轮六套A1]')
line(first, '这是服装概念探索。', '这是第一轮服装概念探索。当时未制作侧背面；当前另用原V4服装完成[A1六视角／四细节](../2026-10-12-a1-turnaround-details/README.md)。九套变体各自背部、原创VRM／衣物绑定仍待，学校文件与运行样本保持。')
line(first, '当前下一步：', '用户最新要求先保存服装再做角色视图，已完成[九套原图包](../../../../' + archive + ')及[A1视角／细节](../2026-10-12-a1-turnaround-details/README.md)；下一步统一角色可制作参考，服装选型和E1反馈保留。')
second = art + '2026-10-12-a1-wardrobe-round2/README.md'
replace(second, '当前下一步：比较A1九套服装、收敛默认款及备选，再细化选定款侧背面与可制作结构。', '该轮原计划先收敛服装；用户随后要求先保存再做形象图，现已另存[九套原图包](../../../../' + archive + ')并完成[A1六视角／四细节](../2026-10-12-a1-turnaround-details/README.md)。当前统一角色可制作参考，具体默认服装仍未选定。')

research = 'research/2026-10-10-avatar-art/'
for name in ['japanese-character-study.md', 'mainstream-anime-c1-study.md', 'popular-character-study.md', 'wardrobe-study.md']:
    path = research + name
    line(path, '**当前状态（2026-10-12后续）：**', '**当前状态（2026-10-12后续）：**A1角色已确定，C1历史保留；[九套服装](../../' + art + 'a1-wardrobe-index.md)及实际prompt已另存[原图包](../../' + archive + ')。用户随后要求全方位／细节，已完成[六个全身视角和四张细节](../../' + art + '2026-10-12-a1-turnaround-details/README.md)，原V4衣服仅作一致工作参考，默认服装仍未选。当前统一角色可制作参考；E1精修／原创VRM仍待。以下保留原研究日期、来源和访问范围，历史生成顺序不作为当前下一步。')
for name in ['japanese-character-study.md', 'mainstream-anime-c1-study.md']:
    path = research + name
    text = (ROOT / path).read_text()
    paragraphs = text.split('\n\n')
    assert paragraphs[1].startswith('**当前状态')
    replace(path, paragraphs[1] + '\n\n', paragraphs[1] + '\n\n## HISTORICAL：原研究与当时建议\n\n')
replace(research + 'mainstream-anime-c1-study.md', '当前转为A1九套服装的比较与细化。', '当时转为A1九套服装比较；当前已按上方新指令完成保留与角色视图。')
replace(research + 'character-concepts.md', '再细化选定服装。原生成和研究过程见资产索引及各阶段QA。', '用户最新要求先保存九套，已另存[原图包](../../' + archive + ')并完成[A1六视角／四细节](../../' + art + '2026-10-12-a1-turnaround-details/README.md)。原V4服装只是工作参考；当前统一可制作结构，默认服装仍待选。原生成和研究过程见资产索引及各阶段QA。')

spec = art + 'a1-turnaround-spec.md'
replace(spec, '本轮推进A1视角和结构细节，暂停继续增加衣服。', '本轮完成六个全身视角与四张结构细节，暂停继续增加衣服。')
append(spec, '''## 本轮实际结果

十张成稿均由协调代理实际查看，原生与项目文件逐字节一致：六全身＋D02／D03为1024×1536，D01／D04为1254×1254。11次调用，T06首稿头身不一致而重试一次；初始／第二次实际提示词及被拒首稿均保留，其他九张首次成功。

T05／T06实际角度比目标四分之三浅，索引标为前／后斜视，不能称精确45度。侧面远侧手／鞋自然重叠，D02／D03取景略宽，D04鞋头分片和高光更明确。后发／衣缝／裹裙仍有细微差异，下一步统一可制作参考，不把二维生成图称为共享三维模型。来源与逐图观察见[manifest](2026-10-12-a1-turnaround-details/manifest.json)。''')

append('decision-log.md', '''## 2026-10-12 后续：保存服装并制作A1全方位／细节

- **用户决定：**“先保存着这些服装，然后开始做A1的全方位形象图和细节图”。取代上一阶段当前“先选默认衣服再补侧背面”的顺序；A1身份继续，不等于用户已选衣服或最终背部结构。
- **保存：**九套原PNG、九份实际prompt、原V4参考及索引存入[九套原图包](output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)，21项读回字节一致；既有目录和历史版本保留。
- **工程选择：**沿用V4原服装统一研究视角，固定发扣在人物自身左侧；正面中性参考经检查后约束侧背面，背面经检查后约束后斜视／后发。未见的后发、衣缝和裹裙后片是新增设计提案，不从原图虚构已知三维结构。
- **结果：**[六个全身视角与四张细节](design/desk-companion/characters/2026-10-12-a1-turnaround-details/README.md)，十张原生PNG逐张检查，11次调用；T06首稿回头而重试一次，首稿及第二次实际prompt保留。八张1024×1536、两张1254×1254。T05／T06斜视较浅、侧面自然遮挡和细节图材质增强均记录，无像素后期。
- **后续与边界：**当前统一发束、背部衣缝和裹裙的可制作参考；默认服装、E1精修、原创VRM／绑定仍待。学校、旧资产和运行许可模型保持，本轮本地保存，没有Git写入或新实物验证。''')

handoff = '''# Group 2 Current Handoff

更新：2026-10-12后续。当前：**A1身份已确定；九套服装原图／实际提示词已单独保存；六个全身视角与四张细节图完成并逐张检查。** C1历史保留，默认服装未选。

## 当前产物与证据

- [九套服装原图包](output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)：九PNG＋九prompt＋V4身份参考＋索引，21项读回一致；[九套总索引](design/desk-companion/characters/a1-wardrobe-index.md)和原素材目录保留。
- [A1六视角／四细节及预览](design/desk-companion/characters/2026-10-12-a1-turnaround-details/README.md)：正、左右侧、背、前后斜视，脸／发扣、后发、衣物、靴袜。原V4衣服只作工程参考，不是用户默认款决定；[视图规范](design/desk-companion/characters/a1-turnaround-spec.md)记录人物自身左右和原稿未见结构。
- 十图均逐张view_image检查：八张1024×1536、两张1254×1254，共11次内置ImageGen；T06首稿头身方向不一致而重试一次，初始／实际prompt及拒绝图保留。原生与项目PNG字节一致，无像素后期。T05／T06实际角度偏浅，不称精确45度；侧面远侧手／鞋自然重叠。
- 来源、真实提示词和逐图观察见[manifest](design/desk-companion/characters/2026-10-12-a1-turnaround-details/manifest.json)；[本轮QA](output/qa/2026-10-12-a1-turnaround-details/verification.md)继承同任务139份／12,884行全文及相关补读，核对71项保护文件、服装包、图片和链接。

## 未完成与保留

后发分组、外套后缝和裹裙后片为本轮新增提案，跨视角细部仍待统一；二维参考不是共享精确3D几何。九套各自背部、默认服装、E1精修、正式名字／声音、原创VRM与绑定仍待。运行角色仍为pixiv许可样本；本次仅本地保存。

[第2份v5日志](planning/2026-10-11/logsheet-2-review.md)、学校原件、旧A1／B1／C1／E1和所有原提示词／manifest保持；本轮未核实学校提交状态。真实语音、Pi／iPhone／光学、PC／LCU、真人姿态及RIG实物仍按原契约分别完成或实测。

## 唯一下一步

**以本套视角统一A1发束、外套背缝和裹裙结构，整理可制作参考。** 默认服装选择保留，不把本轮V4工作参考擅自定为最终款。
'''
(ROOT / 'handoff.md').write_text(handoff)
changed.add('handoff.md')

append('work-log.md', '''## 2026-10-12 同一美术任务：保存九套服装与A1全方位／细节

- **目标：**按用户最新顺序先保存服装，再做A1全方位形象和细节；不继续增衣服，不要求先选择默认款。
- **阅读：**继承本艺术任务139份／12,884行全文和上一阶段补读；开工盘点142份，补读入口、相关角色规范／资产索引及最新决定。压缩恢复只补入口与当前文件、收尾变更读回；不是重新全库阅读。[本轮记录](output/qa/2026-10-12-a1-turnaround-details/reading-record.json)及closeout-reading保留范围和排除项。
- **先保存：**[九套原图包](output/character-art/2026-10-12/A1_Wardrobe_9_Outfits_20261012.zip)含九PNG、九实际prompt、原V4参考与索引，共21项，CRC及逐项字节读回一致；原目录与历史稿保留。
- **产物：**[六个全身视角与四张细节](design/desk-companion/characters/2026-10-12-a1-turnaround-details/README.md)、[视图规范](design/desk-companion/characters/a1-turnaround-spec.md)、真实prompt／receipt／manifest及共享renderer预览。八图1024×1536、脸部／鞋靴两图1254×1254。V4原服装仅为一致工程参考，用户未选默认衣服。
- **生成与审阅：**复用三个图像代理，先检查T01再侧背面，检查T03再后斜视／后发。11次原生调用，T06首稿回头而重试一次，首稿与追加实际prompt保留；其他九图首次成功。终态均消费并用interrupt确认，工具无销毁句柄API，不冒称销毁。协调代理实际逐张查看十张成稿，原生PNG字节一致，无像素后期。
- **差异：**发扣固定人物自身左侧；侧面远侧手／鞋会自然重叠。T05／T06角度浅于45度目标，按斜视标注。后发／衣缝／裹裙后片为新增设计提案，细部尚待统一；D02／D03取景略宽、D04鞋头分片／高光增强均记录。
- **同步与验证：**product、入口／avatar、简报／表情／服装／视图规范、旧资产当前路由、五研究入口、决定与handoff同步。[QA](output/qa/2026-10-12-a1-turnaround-details/verification.md)核对十图输入／输出／实际prompt哈希、71旧保护项、服装包、内链、空白和实际十图预览加载。纯美术任务不重复应用套件或学校文档渲染。
- **剩余：**统一可制作参考、默认服装、E1精修及原创VRM／绑定；学校、应用源码与运行许可样本保持。本轮本地保存，没有Git写入、硬件操作、采购、签署、上传或对外联系。''')

changed.update({art + '2026-10-12-a1-turnaround-details/README.md', spec})
(ROOT / qa / 'updated-markdown.json').write_text(json.dumps(sorted(changed), ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'updated_markdown_count': len(changed), 'paths': sorted(changed)}, ensure_ascii=False, indent=2))
