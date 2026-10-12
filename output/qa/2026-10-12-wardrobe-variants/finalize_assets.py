from pathlib import Path
import json, hashlib, struct, datetime
ROOT=Path('/Users/tantalum/Documents/ChatGPT/FYP')
OUT=ROOT/'design/desk-companion/characters/2026-10-12-wardrobe-variants'
QA=ROOT/'output/qa/2026-10-12-wardrobe-variants'
jobs=json.loads((OUT/'generation-jobs.json').read_text())
observations={
 'A1-W1':{'silhouette':'立领无袖机能裙、斜向裹片与分离袖；青灰滚边、小腰包、半透袜及短靴。','use':'保留柔科技身份，适合较鲜明的常驻造型。','deviations':'分离袖长至上臂，扣件多于简报；鞋跟为适度方跟。'},
 'A1-W2':{'silhouette':'浅沙色短风衣、工装短裤、不透明打底裤与越野运动鞋。','use':'轻便、自在的日常／轻户外方向。','deviations':'衣摆出现短调节绳环；不影响服装结构。'},
 'A1-W3':{'silhouette':'象牙白与暮蓝交叠裙、小披肩、垂片腰带、深灰袜及及膝靴。','use':'安静的星旅轻奇幻；本轮优先细化建议之一。','deviations':'外层下摆及腰带垂片稍长，层次较简报复杂；靴子仍有小方跟。'},
 'C1-W1':{'silhouette':'酒红／炭黑不对称舞台裙、单侧长袖、露肩、侧层片及及膝靴。','use':'更鲜明、有表演感的角色造型。','deviations':'侧裙片较长，额外出现米白裙片；仍有材质渐变。'},
 'C1-W2':{'silhouette':'奶油白短运动外套、酒红短上衣、弧形边运动短裤、罗纹袜及运动鞋。','use':'活泼亲近的周末休闲，适合日常常驻。','deviations':'短上衣留少量腰部，与完整运动穿搭协调；未见明显结构问题。'},
 'C1-W3':{'silhouette':'梅紫短羽织、米白交领内搭、青灰腰封、不对称褶裙、深灰袜及短靴。','use':'现代和风身份较清楚；本轮优先细化建议之一。','deviations':'右袖几何边饰比目标更宽，短靴跟高于很低跟目标。'}
}
manifest=[]; review=[]; checks=[]
for i,j in enumerate(jobs,1):
    r=json.loads(Path(j['receipt_path']).read_text())
    p=Path(j['output_path']); data=p.read_bytes()
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    w,h=struct.unpack('>II',data[16:24]); assert (w,h)==(1024,1536)
    sha=hashlib.sha256(data).hexdigest(); assert sha==r['sha256']
    native=r.get('native_original_path') or r.get('actual_native_output_path') or r.get('native_path')
    assert native and Path(native).read_bytes()==data
    source=Path(j['source_path']); prompt=Path(j['prompt_path'])
    attempts=r.get('attempt_count') or r.get('attempts')
    attempts=len(attempts) if isinstance(attempts,list) else attempts
    assert attempts==1
    item={'id':j['id'],'title_zh':j['title_zh'],'status':'VALID_CONCEPT / USER_SELECTION_PENDING','output':p.name,'width':w,'height':h,'bytes':len(data),'sha256':sha,'native_original_path':native,'reference_image':str(source.relative_to(ROOT)),'reference_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'prompt':str(prompt.relative_to(OUT)),'prompt_sha256':hashlib.sha256(prompt.read_bytes()).hexdigest(),'attempt_count':attempts,'receipt':Path(j['receipt_path']).name,'route':'built-in ImageGen edit with local referenced_image_paths','transparent_background':False,'pixel_postprocessing':False,'coordinator_view_image_review':True,'observations':observations[j['id']]}
    manifest.append(item)
    review.append({'id':j['id'],'index':i,'title':j['id']+' · '+j['title_zh'],'src':p.name,'href':p.name,'imagePath':str(p),'prompt':prompt.read_text(),'routeName':'内置 ImageGen 原生换装','showCaptions':True})
    checks.append({'id':j['id'],'valid_png':True,'nonempty':True,'native_bytes_equal':True,'source_exists':source.exists(),'prompt_exists':prompt.exists(),'dimensions':[w,h],'root_visual_review':'PASS: identifiable adult character, full head/hands/feet, coherent outfit, distinct style','deviations':observations[j['id']]['deviations']})
(OUT/'manifest.json').write_text(json.dumps({'created_date':'2026-10-12','group':'Group 2','task':'A1 V4 and C1 V1 varied wardrobe redesigns','selected_variant':None,'recommended_for_refinement':['A1-W3','C1-W3'],'recommendation_author':'assistant visual judgment, not user selection','source_invariants':'Face/hair/eyes/accessories/expression/pose/proportions and quiet background kept as closely as possible; not a pixel identity guarantee.','items':manifest},ensure_ascii=False,indent=2)+'\n')
(OUT/'review-manifest.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
(QA/'image-validation.json').write_text(json.dumps({'checked_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'images':checks,'image_count':6,'native_calls':6,'retry_count':0,'coordinator_inspected_all':True,'native_image_workers':3,'terminal_results_consumed':3,'interrupt_confirmed_terminal':3,'destroy_handle_api_available':False,'no_additional_workers_opened':True},ensure_ascii=False,indent=2)+'\n')
rows=['| 编号 | 方向与原图 | 实际轮廓 | 提示词 |','|---|---|---|---|']
for j in jobs:
    o=observations[j['id']]
    rows.append(f"| {j['id']} | [{j['title_zh']}]({Path(j['output_path']).name}) | {o['silhouette']} | [完整实际 prompt](prompts/{j['slug']}.txt) |")
readme='''# A1 V4 与 C1 V1 · 服装再设计六版

Group 2 · 2026-10-12。状态：**SIX_VALID_WARDROBE_CONCEPTS / USER_SELECTION_PENDING**。

用户要求为A1 V4与C1再设计几版服装，探索不同风格，不局限都市上班族。两位角色各完成三张独立全身图；脸、头发、眼睛、配饰、表情及站姿以各自原稿作连续性参考，服装、袜子和鞋型允许完整重设计。所有原稿及提示词保留。

[六版并排预览](review-board.html)为共享Creative Production renderer生成的静态检查页，点击图可打开完整原图；它不保存或代替用户选型。原生创意画板的直接工具入口本轮不可用，因此没有经禁止的嵌套路径挂载画板。

'''+ '\n'.join(rows)+'''

## 视觉判断与差异

助手建议优先继续细化 **A1-W3星旅轻奇幻**和**C1-W3现代和风**：前者的披肩与蓝白交叠裙延续安静气质，后者用腰封、袖形与褶裙建立清楚身份。若偏日常常驻，可比较A1-W2与C1-W2。以上是本轮视觉判断，没有用户最终选型或人气／效果测量。

'''+ '\n'.join(f"- **{j['id']}：**{observations[j['id']]['deviations']}" for j in jobs)+'''

六张均由协调代理使用view_image实际查看：单图单人、成年观感、头／双手／双鞋完整，衣物层次和结构可读，主要身份特征稳定。材质和背景仍有柔和渐变，不称严格两级赛璐璐或完全逐像素锁定脸部。没有发现需重生成的无效图，保留每张首次成功结果。

## 来源与保存

- A1三版唯一参考：[A1 Anime V4](../2026-10-10-concepts/a1-silver-mist-anime-v4.png)。
- C1三版唯一参考：[C1 Plum Dusk V1](../2026-10-10-c1-concept/c1-plum-dusk-v1.png)。
- 六次内置ImageGen编辑；三个限定图像工作代理各顺序生成两张。每张1024×1536、1次尝试；无第三方IP参考图输入、CLI/API回退、裁切、拼图、重绘或其他像素后期。
- [资产清单](manifest.json)保存精确输入／输出／prompt哈希与原生路径；各receipt保留工作代理的原始检查。原生与工作区PNG逐字节一致。
- [六份实际提示词](prompts/)及[生成任务](generation-jobs.json)保留；[本轮QA](../../../../output/qa/2026-10-12-wardrobe-variants/verification.md)记录全文恢复、工具边界与保存检查。

这是服装概念探索。原创VRM、侧背面、表情绑定与衣物变形尚未制作；应用仍用pixiv许可样本，学校文件不因换装改变。

当前下一步：依据这六套的比较反馈收敛服装方向，再细化选定款的侧背面与可制作结构；E1表情反馈仍保留为后续。
'''
(OUT/'README.md').write_text(readme)
print('6 images verified byte-identical to native originals; manifests, review inputs and README saved.')
