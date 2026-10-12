from pathlib import Path
import json,hashlib,struct,datetime
ROOT=Path('/Users/tantalum/Documents/ChatGPT/FYP'); OUT=ROOT/'design/desk-companion/characters/2026-10-12-a1-wardrobe-round2'; QA=ROOT/'output/qa/2026-10-12-a1-wardrobe-round2'
jobs=json.loads((OUT/'generation-jobs.json').read_text())
obs={
'A1-W4':('立领斜襟、短肩披与交叠裙，蓝白配色和云纹形成新中式轮廓。','云纹较宽，盘扣及流苏较多，鞋跟高于很低跟目标。'),
'A1-W5':('方领、绒感上身、短泡袖、烟紫分层A字裙与系带短靴。','蕾丝边较宽，绒面纹理／高光较强，短靴为适度方跟。'),
'A1-W6':('燕麦白针织开衫、灰蓝高领上衣、炭灰短裤、过膝袜与便鞋。','开衫长至下臀／大腿上部，比高髋目标稍长；腰线与短裤仍清楚。'),
'A1-W7':('象牙白灰蓝连身服、封闭拉链、腰带、完整长裤和厚底短靴。','袖袋、腿袋和腰带环比简报多；衣料仍有自然余量，未变成紧身胶衣。'),
'A1-W8':('条纹船领上衣、雾蓝中长交叠裙、腰带及平底凉鞋。','腰部新增小圆扣，垂带稍长；首图开口高于本套简报范围，第二次生成后保留。'),
'A1-W9':('午夜蓝不对称露肩礼服、局部缎面饰边、银扣及少量裙摆几何装饰。','银灰鞋跟较低跟目标高，长侧裙尖略超过膝下。')}
items=[];reviews=[];checks=[]
for i,j in enumerate(jobs,1):
    r=json.loads(Path(j['receipt_path']).read_text()); p=Path(j['output_path']); d=p.read_bytes()
    assert d[:8]==b'\x89PNG\r\n\x1a\n'; w,h=struct.unpack('>II',d[16:24]); assert (w,h)==(1024,1536)
    native=r['native_original_path']; sha=hashlib.sha256(d).hexdigest(); assert sha==r['sha256'] and Path(native).read_bytes()==d
    pp=Path(j['prompt_path']); assert hashlib.sha256(pp.read_bytes()).hexdigest()==j['prompt_sha256']
    assert hashlib.sha256(Path(j['source_path']).read_bytes()).hexdigest()==j['source_sha256']
    n=r['attempt_count']; assert n in (1,2)
    if j['id']=='A1-W8': assert n==2 and r['same_prompt_for_both_attempts']
    else: assert n==1
    item={'id':j['id'],'title_zh':j['title_zh'],'status':'VALID_CONCEPT / OUTFIT_SELECTION_PENDING','character':'A1_USER_SELECTED','output':p.name,'width':w,'height':h,'bytes':len(d),'sha256':sha,'native_original_path':native,'source_path':j['source_path'],'source_sha256':j['source_sha256'],'prompt':str(pp.relative_to(OUT)),'prompt_sha256':j['prompt_sha256'],'receipt':Path(j['receipt_path']).name,'attempt_count':n,'coordinator_view_image_review':True,'description_zh':obs[j['id']][0],'deviations_zh':obs[j['id']][1],'pixel_postprocessing':False}
    items.append(item); reviews.append({'id':j['id'],'index':i,'title':j['id']+' · '+j['title_zh'],'src':p.name,'href':p.name,'imagePath':str(p),'prompt':pp.read_text(),'routeName':'内置ImageGen · A1换装'})
    checks.append({'id':j['id'],'dimensions':[w,h],'native_bytes_equal':True,'prompt_unchanged':True,'source_unchanged':True,'coordinator_visual_review':'PASS: recognizable adult A1, complete head/hands/feet, coherent outfit, different silhouette','attempt_count':n})
manifest={'created_date':'2026-10-12','group':'Group 2','character_selection':'A1 confirmed by user as continuing character','outfit_selection':None,'recommended_for_refinement':['A1-W4','A1-W6'],'recommendation_author':'assistant visual judgment only','reference':'Original A1 Anime V4 only','items':items,'rejected_attempts':[{'id':'A1-W8-attempt1','path':'a1-w8-seaside-attempt1-rejected.png','reason':'Wrap opening extended above the lower-leg-only brief; retained as generation evidence, not a displayed candidate.'}]}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');(OUT/'review-manifest.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n')
(QA/'image-validation.json').write_text(json.dumps({'image_count':6,'native_calls':sum(x['attempt_count'] for x in items),'retry_count':1,'images':checks,'native_workers_reused':3,'new_worker_handles':0,'terminal_results_consumed':True,'interrupt_confirmed_terminal':True,'destroy_handle_api_available':False,'completed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()},ensure_ascii=False,indent=2)+'\n')
rows=['| 编号 | 原图与方向 | 实际轮廓 | 完整实际提示词 |','|---|---|---|---|']
for j in jobs: rows.append(f"| {j['id']} | [{j['title_zh']}]({Path(j['output_path']).name}) | {obs[j['id']][0]} | [prompt](prompts/{j['slug']}.txt) |")
readme='''# A1 · 第二轮服装六套

Group 2 · 2026-10-12。状态：**A1_CHARACTER_SELECTED / SIX_NEW_OUTFITS_COMPLETE / OUTFIT_SELECTION_PENDING**。

用户明确“确定A1为后续形象，再设计几套A1的服装”。A1成为后续角色身份，C1转为历史对照；没有据此擅自选定上一轮A1-W1／W2／W3中的任何一套服装。本轮继续银灰长发、灰蓝眼、开环发扣及既有成年脸型／性格，以[A1 V4](../2026-10-10-concepts/a1-silver-mist-anime-v4.png)为唯一参考，完整探索六套新衣服。

[六套并排预览](review-board.html)／[A1全部九套总索引](../a1-wardrobe-index.md)。

'''+ '\n'.join(rows)+'''

## 实际检查与建议

协调代理逐张使用view_image检查全部六图：A1身份和原站姿基本稳定，成年观感、完整头／双手／双鞋与服装结构通过。六套明确改变领口、裙裤长度、袖形、材质和鞋型；背景与材质仍有柔和渐变，不能称完全两级赛璐璐或逐像素相同。

助手建议优先比较 **A1-W4新中式**与**A1-W6居家针织**：前者有清楚的服装身份，后者适合安静亲近的日常常驻。W9可作更正式的主题装。只是本轮视觉建议，具体默认服装未由用户选定。

'''+ '\n'.join(f"- **{j['id']}：**{obs[j['id']][1]}" for j in jobs)+'''

## 原图、提示词与范围

[manifest](manifest.json)及每项receipt保存精确输入／输出／prompt哈希、原生路径与尝试数。六张成稿均1024×1536，原生与工作区PNG逐字节一致，无裁切、缩放、拼图或像素后期。

三个现有图像代理各顺序生成两款，未新增代理句柄。共七次内置ImageGen：W8首图交叠开口高于本套“小腿范围”的简报，使用完全相同提示词重试一次；[首图](a1-w8-seaside-attempt1-rejected.png)与两次真实路径保留在receipt，不显示为正式候选。其余五张首次成功，没有再生成已合格图。无IP参考图、CLI/API回退或C1新图。

原生Creative Production画板的直接调用仍不可用，遵守禁止嵌套挂载的要求；共享renderer生成静态检查页。原A1／B1／C1／E1及上轮六图原文件与提示词均保留。角色选择不等于原创VRM或对应3D服装已完成；运行许可模型与学校文件保持。

[本次QA](../../../../output/qa/2026-10-12-a1-wardrobe-round2/verification.md)继承同一美术任务的全文阅读并记录本次补读、视觉、来源、保护与链接检查。当前下一步：比较A1九套服装、收敛默认款及备选，再细化选定款侧背面与可制作结构。
'''
(OUT/'README.md').write_text(readme)
old=ROOT/'design/desk-companion/characters/2026-10-12-wardrobe-variants/manifest.json'; olditems=json.loads(old.read_text())['items']
allrows=['| 编号 | 方向与原图 | 阶段 |','|---|---|---|']
for x in olditems:
    if x['id'].startswith('A1-'): allrows.append(f"| {x['id']} | [{x['title_zh']}](2026-10-12-wardrobe-variants/{x['output']}) | 第一轮，原图保留 |")
for x in items: allrows.append(f"| {x['id']} | [{x['title_zh']}](2026-10-12-a1-wardrobe-round2/{x['output']}) | 第二轮新款 |")
(ROOT/'design/desk-companion/characters/a1-wardrobe-index.md').write_text('''# A1 · 后续角色与服装总索引

Group 2 · 2026-10-12。**角色身份A1已由用户确定；具体默认服装未选定。**

身份基准：[A1 Anime V4](2026-10-10-concepts/a1-silver-mist-anime-v4.png)；性格与外形见[角色简报](a1-character-brief.md)。银灰长发、灰蓝眼、圆环发扣及安静敏锐的成年气质持续保留。C1原图和三套换装留作历史参考，不再与A1并列作为当前待选角色。

[本轮六套并排预览](2026-10-12-a1-wardrobe-round2/review-board.html)／[第二轮原图与实际提示词](2026-10-12-a1-wardrobe-round2/README.md)／[第一轮三套A1与历史C1](2026-10-12-wardrobe-variants/README.md)。

'''+ '\n'.join(allrows)+'''

助手本轮优先建议W4与W6，W9可作正式主题装；这是视觉判断，不替用户选衣服。每张是独立全身概念，原生文件、提示词、hash与实际偏差见各阶段资产目录。侧背面、原创VRM与服装绑定仍待制作，运行时仍为许可样本。

当前下一步：从九套里收敛默认服装和备选款，再细化选定款的侧背面与制作要求。
''')
print(json.dumps({'valid_images':6,'native_calls':7,'A1_wardrobe_total':9,'character':'A1 user selected','outfit':'pending'},ensure_ascii=False))
