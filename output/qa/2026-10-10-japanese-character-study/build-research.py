# -*- coding: utf-8 -*-
"""Reproduce the attributed public-reference index and static study board."""
from pathlib import Path
import html
import json

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'research/2026-10-10-avatar-art'
SOURCES = [
 ('VIVY_PROFILE','Vivy official character profile','https://vivy-portal.com/character/detail/?id=vivy','official profile',None,'Full character text; official still and character visual inspected in browser.'),
 ('VIVY_VOICE','Vivy official cast interview','https://vivy-anime.com/special/interview/','primary cast interview','2021-04-05','Interview text read; no audio interview heard.'),
 ('VIVY_PRODUCTION','Vivy original story and production roundtable','https://vivy-portal.com/special/talk0227/','primary production interview','2021-02-27','Main interview read through end; design and acting process.'),
 ('YOR_VISUAL','Yor official character visual','https://spy-family.net/news/?p=1978','official visual release','2025-04-25','Release and poster inspected; later visual is separate from 2022 acting interview.'),
 ('YOR_VOICE','Saori Hayami interview, page 1','https://www.animatetimes.com/news/details.php?id=1648804152','primary cast interview','2022-04-08','Page 1 main interview read; pages 2-4 not read or relied upon.'),
 ('AOI_PROFILE','SHIROBAKO TV Aoi Miyamori','http://shirobako-anime.com/character-01.html','official TV character profile',None,'Reached from official studio site through TV character menu. Text, front/back sheet and four facial views inspected.'),
 ('SHIROBAKO_STUDIO','P.A.WORKS SHIROBAKO','https://www.pa-works.jp/works/shirobako/','official studio work page',None,'Story and credits read; linked original TV site followed. Not the film version.'),
 ('AKANE_PROFILE','PSYCHO-PASS 2 Akane Tsunemori','https://psycho-pass.com/archive/sp/character/tv2.php','official character profile',None,'Akane section and visual inspected; no season-3 age or story imported.'),
 ('MOMOKA_PROFILE','Girls Band Cry Momoka Kawaragi','https://girls-band-cry.com/character/momoka/','official character profile',None,'Profile and visual inspected; explicitly states age 20.'),
 ('GBC_DIRECTOR_P1','Kazuo Sakai on Girls Band Cry, page 1','https://febri.jp/topics/girls-band-cry_int_02_01/','primary director interview',None,'Main interview read; character choices, life and 3D drama.'),
 ('GBC_DIRECTOR_P2','Kazuo Sakai on Girls Band Cry, page 2','https://febri.jp/topics/girls-band-cry_int_02_01/2/','primary director interview',None,'Main interview read, including motion/texture and shot-specific facial changes. Exact publication date not asserted.'),
 ('MERYL_VISUAL','TRIGUN STAMPEDE Meryl visual and profile','https://trigun-anime.com/news/?p=210','official visual release','2022-12-17','Original STAMPEDE poster and reporter profile inspected. Site header now mentions STARGAZE; release itself is dated 2022.'),
 ('ORANGE_CG','Orange facial R&D interview for TRIGUN STAMPEDE','https://cgworld.jp/article/202304-triguns1.html','primary CG production interview','2023-04-26','Main interview read; angle diagram inspected. Parts 2-3 and linked test videos not watched.'),
]
VISUALS = [
 dict(id='vivy',name='Vivy',work='Vivy · 2021',source='VIVY_PROFILE',image='https://vivy-portal.com/assets/img/character/img/img_vivy.png',observation='大组发束、清楚眉眼与少量AI识别线索。',lesson='身份与行为动机要一致。',rights='©Vivy Score / Aniplex・WIT STUDIO'),
 dict(id='yor',name='约尔·福杰',work='SPY×FAMILY · 2025官方视觉',source='YOR_VISUAL',image='https://spy-family.net/wp/wp-content/uploads/2025/04/news_character_visual_0425_2100_yor.jpg',observation='黑发、红眼和少量金色配饰集中识别。',lesson='表情随情境变化，亲近感有具体原因。',rights='©遠藤達哉／集英社・SPY×FAMILY製作委員会'),
 dict(id='aoi',name='宫森葵',work='SHIROBAKO · 2014 TV设定',source='AOI_PROFILE',image='http://shirobako-anime.com/images/character/1main.png',observation='正背面保持同一轮廓，外套与运动鞋体现日常活动。',lesson='可靠应体现在核对、协调与处理事情。',rights='©「SHIROBAKO」製作委員会'),
 dict(id='akane',name='常守朱',work='PSYCHO-PASS 2 · 第二季档案',source='AKANE_PROFILE',image='https://psycho-pass.com/archive/sp/images/character_tv201_main_sp.png',observation='动漫眉眼、短发和职业服装仍有专业感。',lesson='成熟不必依赖写实皮肤和鼻梁。',rights='©サイコパス製作委員会'),
 dict(id='momoka',name='河原木桃香',work='GIRLS BAND CRY · TV角色',source='MOMOKA_PROFILE',image='https://girls-band-cry.com/wp-content/themes/gbc_v1-1/assets/webp/common/character/img_body-momoka.webp',observation='宽松深色上衣与放松重心形成直率气质。',lesson='简洁服装与日常姿态也能有辨识度。',rights='©東映アニメーション'),
 dict(id='meryl',name='梅丽鲁·史崔夫',work='TRIGUN STAMPEDE · 2023版',source='MERYL_VISUAL',image='https://trigun-anime.com/news/wp-content/uploads/2022/12/MERYL-F%E2%80%BB12%E6%9C%8817%E6%97%A5%E5%9C%9F23%E6%99%82%E8%A7%A3%E7%A6%81_re-1.png',observation='笔记本、手势与服装共同交代记者的目的。',lesson='动作应回应任务；宣传图不等于实时模型。',rights='©2023 内藤泰弘・少年画報社／TRIGUN STAMPEDE製作委員会'),
]
EXTRAS = [
 dict(id='aoi-expressions',source='AOI_PROFILE',image='http://shirobako-anime.com/images/character/1circle.png',caption='宫森葵官方表情与侧脸。看眉眼／嘴角怎样变化，轮廓仍保持同一角色。'),
 dict(id='orange-angle',source='ORANGE_CG',image='https://cgworld.jp/article/c2303fa7e2b7efa6ac93a193ccb4387f58e49260.jpg',caption='Orange公开的视角修形示意：工作空间中的脸与目标镜头呈现不同。不是FYP必须复刻的技术规格。'),
]
source_map={s[0]:s[2] for s in SOURCES}
payload=dict(group='Group 2',accessed_date='2026-10-10',timezone='Asia/Hong_Kong',scope='Japanese anime appearance, characterization and 3D acting; existing concepts preserved',sources=[dict(id=i,title=t,url=u,kind=k,published_date=d,access=a) for i,t,u,k,d,a in SOURCES],visuals=VISUALS,extra_visuals=EXTRAS,limitations=['No complete episode viewing or new voice listening','No IP character model downloaded or reused','No new ImageGen, pixel edits, runtime changes or hardware tests','Visual observations and A1 proposals are author analysis, not creator intent or user approval'])
(DEST/'japanese-character-sources.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
e=html.escape
cards='\n'.join(f'<article id="{v["id"]}"><div class="image"><img src="{e(v["image"])}" alt="{e(v["name"])}官方角色视觉"></div><div class="copy"><small>{e(v["work"])}</small><h2>{e(v["name"])}</h2><p>{e(v["observation"])}</p><p class="lesson">{e(v["lesson"])}</p><a href="{e(source_map[v["source"]])}">官方来源 ↗</a><div class="rights">{e(v["rights"])}</div></div></article>' for v in VISUALS)
extras='\n'.join(f'<figure><img src="{e(v["image"])}" alt="{e(v["caption"])}"><figcaption>{e(v["caption"])} <a href="{e(source_map[v["source"]])}">原始资料 ↗</a></figcaption></figure>' for v in EXTRAS)
page='''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Group 2 · 日本动画角色研究</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f0ea;color:#252d34;font:16px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1240px;margin:auto;padding:44px 32px}header{padding:12px 0 30px;border-bottom:1px solid #c8cbc9;margin-bottom:28px}small,.eyebrow{font-size:12px;letter-spacing:.08em;color:#64716f}h1{font-size:38px;letter-spacing:-.04em;line-height:1.2;margin:14px 0}h2{font-size:23px;margin:5px 0 10px}p{margin:8px 0}a{color:#356b74;text-underline-offset:4px}nav{display:flex;gap:24px;flex-wrap:wrap;margin-top:18px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:30px 24px}article{min-width:0;background:#faf9f5;border:1px solid #deded5}.image{height:380px;background:#e7e9e4;display:flex;justify-content:center;padding:16px}.image img{height:100%;width:100%;object-fit:contain}.copy{padding:18px 20px}.lesson{font-weight:600}.rights{font-size:10px;color:#77817e;line-height:1.45;margin-top:10px}.details{display:grid;grid-template-columns:1fr 2fr;align-items:center;gap:28px;margin:40px 0}figure{margin:0;min-width:0}figure img{max-width:100%;max-height:430px;object-fit:contain;display:block;margin:auto}figcaption{font-size:13px;margin-top:14px}.note{padding:22px 0;border-top:1px solid #c8cbc9;margin-top:20px}footer{font-size:12px;color:#64716f;margin-top:24px}@media(max-width:850px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.details{grid-template-columns:1fr}main{padding:24px 18px}}@media(max-width:520px){.grid{grid-template-columns:1fr}.image{height:420px}h1{font-size:30px}}
</style>
</head>
<body>
<main>
<header>
<div class="eyebrow">GROUP 2 / DESK COMPANION / CHARACTER STUDY · 2026.10.10</div>
<h1>让外形与性格一起成立</h1>
<p>保留A1 V1–V4与B1。这轮研究日本动画怎样让角色具有身份、反应和日常存在感。下方是有出处的参考；观察与A1建议属于本组分析。</p>
<nav>
<a href="japanese-character-study.md">完整研究 ↗</a>
<a href="japanese-character-sources.json">来源记录 ↗</a>
<a href="character-concepts.md">五版原稿索引 ↗</a>
</nav>
</header>
<section class="grid" aria-label="六个日本动画角色参考">'''+cards+'''</section>
<section class="details" aria-label="表情和3D制作示例">'''+extras+'''</section>
<div class="note">
<h2>对A1的建议</h2>
<p>安静、敏锐、做事有条理，熟悉后偶尔有轻巧幽默。保留银发、灰蓝眼和既有服装方向，先明确中性脸、六种表情与有原因的动作转换，再微调造型。</p>
<p>这是研究提议，尚未定稿；没有生成V5或替换应用模型。</p>
</div>
<footer>第三方角色图片版权归原权利人，仅用于私人研究，不是本组原创或可复用的应用资产。图片保留官方远程来源，需要联网；没有下载原模型。未完整观看剧集或试听访谈。当前案例不构成人气排名或用户偏好测量。</footer>
</main>
</body>
</html>'''
(DEST/'japanese-character-board.html').write_text(page)
print(f'Wrote {len(SOURCES)} sources, {len(VISUALS)} character visuals and {len(EXTRAS)} detail references.')
