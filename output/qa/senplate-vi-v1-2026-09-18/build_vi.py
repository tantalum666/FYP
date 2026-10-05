from pathlib import Path
import sys, json, copy, math, html

ROOT = Path('/Users/tantalum/Documents/ChatGPT/FYP')
QA = ROOT / 'output/qa/senplate-vi-v1-2026-09-18'
ASSETS = ROOT / 'output/brand/2026-09-18-senplate-vi-v1'
sys.path.insert(0, str(QA / 'python_packages'))
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

W, H = landscape(A4)
G = '#163F35'; C = '#F3F1E7'; S = '#B8C9BC'; I = '#202B26'; WHITE = '#FFFFFF'; ERROR = '#B7473F'
for name in ['M400', 'M500', 'M600', 'M700', 'SC400', 'SC700', 'TC400']:
    pdfmetrics.registerFont(TTFont(name, str(QA / 'render-fonts' / (name + '.ttf'))))

OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
GUIDE = OUT / 'Senplate_VI_Guidelines_v1.pdf'
MASTER = OUT / 'Senplate_Vector_Assets_Master_v1.pdf'
cache = {}
checks = []
page_no = 0
c = None

def colour(value):
    return colors.HexColor(value)

def rect(x, y, w, h, fill=None, stroke=None, sw=0.6):
    c.setLineWidth(sw)
    if fill: c.setFillColor(colour(fill))
    if stroke: c.setStrokeColor(colour(stroke))
    c.rect(x, H-y-h, w, h, fill=bool(fill), stroke=bool(stroke))

def line(x1, y1, x2, y2, col=S, sw=0.6):
    c.setStrokeColor(colour(col)); c.setLineWidth(sw)
    c.line(x1, H-y1, x2, H-y2)

def txt(text, x, y, size=12, font='SC400', col=I, align='left'):
    c.setFont(font, size); c.setFillColor(colour(col))
    if align == 'right': c.drawRightString(x, H-y-size, text)
    elif align == 'center': c.drawCentredString(x, H-y-size, text)
    else: c.drawString(x, H-y-size, text)
    width = pdfmetrics.stringWidth(text, font, size)
    left = x-width if align == 'right' else x-width/2 if align == 'center' else x
    checks.append({'page':page_no,'kind':'text','text':text,'box':[left,y,width,size*1.35]})

def para(text, x, y, w, size=11, font='SC400', col=I, leading=None):
    style=ParagraphStyle('body',fontName=font,fontSize=size,leading=leading or size*1.6,
                         textColor=colour(col),wordWrap='CJK',spaceAfter=0)
    p=Paragraph(html.escape(text).replace('\n','<br/>'),style)
    pw,ph=p.wrap(w,H)
    p.drawOn(c,x,H-y-ph)
    checks.append({'page':page_no,'kind':'paragraph','text':text,'box':[x,y,pw,ph]})
    return ph

def drawing(path):
    path=str(path)
    if path not in cache:
        d=svg2rlg(path)
        if d is None: raise ValueError('Unreadable SVG '+path)
        cache[path]=d
    return copy.deepcopy(cache[path])

def recolour(n, fill=None, outline=False):
    if hasattr(n,'fillColor'):
        n.fillColor=None if outline else colour(fill)
        if hasattr(n,'strokeColor'): n.strokeColor=colour(fill) if outline else None
        if hasattr(n,'strokeWidth') and outline: n.strokeWidth=1.2
    if hasattr(n,'contents'):
        for child in n.contents: recolour(child,fill,outline)

def svg(path,x,y,w,h=None,override=None,stretch=False,outline=False):
    d=drawing(path)
    h=h if h is not None else w*d.height/d.width
    if override: recolour(d,override,outline)
    sx=w/d.width; sy=h/d.height
    if not stretch: sx=sy=min(sx,sy)
    dx=(w-d.width*sx)/2; dy=(h-d.height*sy)/2
    d.scale(sx,sy)
    renderPDF.draw(d,c,x+dx,H-y-h+dy)
    return h

def logo(form,col,x,y,w,h=None,**kw):
    return svg(ASSETS/'01_Logos/SVG'/f'{form}-{col}.svg',x,y,w,h,**kw)

def png(path,x,y,w,h=None):
    from PIL import Image
    with Image.open(path) as im: iw,ih=im.size
    h=h if h is not None else w*ih/iw
    c.drawImage(str(path),x,H-y-h,width=w,height=h,mask='auto')
    return h

def link(label,url,x,y,size=10):
    txt(label,x,y,size,'SC400',G)
    width=pdfmetrics.stringWidth(label,'SC400',size)
    c.linkURL(url,(x,H-y-size*1.4,x+width,H-y+2),relative=0,thickness=0)

def footer(total=11):
    txt('Senplate  /  VI V1  /  2026.09',48,H-31,8.5,'M500',G)
    txt(f'{page_no:02d} / {total:02d}',W-48,H-31,8.5,'M500',G,'right')

def page(n,title,sub=''):
    global page_no
    page_no=n
    rect(0,0,W,H,WHITE)
    txt('Senplate / Visual identity',48,26,9,'M500',G)
    txt(title,48,59,27,'SC700',G)
    if sub: para(sub,48,106,W-96,10.3,col=I)
    footer()

def done(): c.showPage()

def contrast(a,b):
    def lum(s):
        vals=[int(s[i:i+2],16)/255 for i in (1,3,5)]
        vals=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in vals]
        return sum(x*y for x,y in zip(vals,[.2126,.7152,.0722]))
    la,lb=sorted([lum(a),lum(b)],reverse=True)
    return (la+.05)/(lb+.05)

def rgb_cmyk(hexv):
    vals=[int(hexv[i:i+2],16) for i in (1,3,5)]
    r,g,b=[v/255 for v in vals]; k=1-max(r,g,b)
    cs=[0,0,0] if k==1 else [(1-r-k)/(1-k),(1-g-k)/(1-k),(1-b-k)/(1-k)]
    return vals,[round(v*100) for v in cs+[k]]

def guide():
    global c,page_no
    c=canvas.Canvas(str(GUIDE),pagesize=(W,H),pageCompression=1)
    c.setTitle('Senplate Visual Identity Guidelines V1')
    c.setAuthor('Senplate / Group 2')
    page_no=1;rect(0,0,W,H,G)
    txt('Senplate / Brand system / V1',64,49,10,'M500',C)
    logo('horizontal','white',64,143,W-128)
    txt('视觉识别规范',64,340,31,'SC700',C)
    txt('Visual identity guidelines',64,391,17,'M400',C)
    txt('Group 2  /  Final Year Project',64,H-65,10,'M500',C)
    txt('2026.09.18',W-64,H-65,10,'M500',C,'right');done()

    page(2,'标志系统','采用已确定的无刻度纯碗。图形、字标与两种组合分别使用，各版本共用相同的基础路径。')
    specs=[('01  独立图形','symbol',48,155,344,148),('02  独立字标','wordmark',450,155,344,148),
           ('03  横向组合','horizontal',48,350,344,164),('04  上下组合','stacked',450,350,344,164)]
    for label,form,x,y,w,h in specs:
        txt(label,x,y,12,'SC700',G)
        if form=='symbol':logo(form,'green',x+88,y+32,160,114)
        elif form=='wordmark':logo(form,'green',x+12,y+49,w-24,90)
        elif form=='horizontal':logo(form,'green',x+8,y+50,w-16,86)
        else:logo(form,'green',x+71,y+29,202,132)
    line(420,152,420,520);line(48,326,W-48,326);done()

    page(3,'颜色版本','优先使用绿色主版本；受印刷或背景限制时，使用黑色或反白文件。保持图形与文字颜色一致。')
    for y,col,bg,title,desc in [(149,'green',C,'绿色主版本','浅色界面、文档与常规品牌展示。'),
                              (283,'black',WHITE,'黑色单色版','单色打印、复印及限制颜色的介质。'),
                              (417,'white',G,'反白版本','深绿色或其他具有足够对比的深色背景。')]:
        rect(48,y,536,112,bg,S if bg==WHITE else None)
        logo('horizontal',col,86,y+15,460,82)
        txt(title,613,y+10,16,'SC700',G)
        para(desc,613,y+43,177,10.5)
    done()

    page(4,'留白、比例与最小尺寸','使用矢量母版等比缩放。以下留白与尺寸是 VI V1 的建议规则，核心标志的几何路径保持。')
    w=630;x=102;y=215;h=w*227/1205;unit=w*320/1205/8
    rect(x-unit,y-unit,w+2*unit,h+2*unit,C)
    c.setDash(3,3);rect(x-unit,y-unit,w+2*unit,h+2*unit,None,S);rect(x,y,w,h,None,G);c.setDash()
    logo('horizontal','green',x,y,w,h)
    txt('x',x-unit/2,y+h/2-5,10,'M600',G,'center')
    txt('x',x+w/2,y-unit+3,10,'M600',G,'center')
    para('组合与独立图形：x = 碗图形宽度的 1/8。上下左右至少保留 x。',48,150,W-96,11)
    para('独立字标：四周至少保留字标可见高度的 1/4。不要按文本框的额外行距计算。',48,367,W-96,10.5)
    rows=[('独立图形','32 px','8 mm'),('独立字标','96 px','24 mm'),('横向组合','160 px','40 mm'),('上下组合','96 px','24 mm')]
    for i,(name,px,mm) in enumerate(rows):
        xx=48+i*192
        txt(name,xx,418,12,'SC700',G);txt(px,xx,444,18,'M600',G);txt('印刷建议 '+mm,xx,473,9.5,'SC400',I)
    para('以上为建议起点。小尺寸优先使用独立图形，并在最终显示设备、纸张或加工材料上确认清晰度。',48,515,W-96,9.5)
    done()

    page(5,'品牌色彩','深绿与米白沿用已选方向；辅助浅绿与墨色用于底色、分区及正文，不替代 Logo 主色。')
    palette=[('深绿','Deep green',G,True,'主色'),('米白','Warm ivory',C,False,'主背景'),
             ('辅助浅绿','Soft sage',S,False,'辅助底色'),('墨色','Ink',I,True,'正文色')]
    for i,(cn,en,hx,dark,role) in enumerate(palette):
        x=48+i*192;fc=C if dark else G
        rect(x,158,168,168,hx,S if hx==C else None)
        txt(cn,x+18,178,16,'SC700',fc);txt(en,x+18,207,10,'M400',fc)
        txt(hx,x+18,253,19,'M600',fc);txt(role,x+18,293,10,'SC400',fc)
        rgb,cm=rgb_cmyk(hx)
        txt('RGB '+ ' / '.join(map(str,rgb)),x,347,10,'M500',G)
        txt('CMYK '+ ' / '.join(map(str,cm)),x,371,9.2,'M400',I)
    rect(48,419,W-96,75,C)
    txt(f'深绿 / 米白对比度：{contrast(G,C):.2f} : 1',67,434,15,'SC700',G)
    para('优先作为文字与背景的组合。辅助浅绿用于底色，不用于小号反白文字。',67,461,W-134,10.3)
    para('CMYK 为不含 ICC 配置的数学换算参考。正式印刷按承印材料、输出配置与样张确认。',48,515,W-96,9.5)
    done()

    page(6,'字体与文字层级','Logo 字标使用 Manrope Bold。正文与标题按内容语言使用 Manrope、Noto Sans TC 或 Noto Sans SC。')
    txt('Manrope',48,155,15,'M600',G);txt('Aa 0123456789',48,185,37,'M700',G)
    txt('ABCDEFGHIJKLMNOPQRSTUVWXYZ',48,240,11,'M400',I)
    txt('Noto Sans TC / 繁体',48,288,13,'SC700',G);txt('食物與營養監測',48,316,27,'TC400',G)
    txt('Noto Sans SC / 简体',48,378,13,'SC700',G);txt('食物与营养监测',48,406,27,'SC400',G)
    line(431,155,431,477)
    txt('数字界面建议层级（px）',471,155,15,'SC700',G)
    for j,(a,b,dsc) in enumerate([('一级标题','32-40 / Bold','用于页面与章节标题'),('二级标题','20-24 / Medium','用于模块或分组'),('正文','14-16 / Regular','行高建议约 1.5 倍'),('说明','11-12 / Regular','只放辅助信息')]):
        yy=195+j*66;txt(a,471,yy,12,'SC700',G);txt(b,580,yy,12,'M500',G);txt(dsc,471,yy+25,10,'SC400',I)
    para('Logo 的字标请优先使用现有轮廓文件，保持字距与比例；字体示例不用于重新排版或替代 Logo 字标。',48,513,W-96,9.5)
    done()

    page(7,'App 图标基础稿','提供 1024 × 1024 方形底图、透明前景与纯色背景。圆角由系统处理，源图层不预先裁切。')
    png(ASSETS/'04_Applications/app-icon-green-1024.png',55,164,233)
    png(ASSETS/'04_Applications/app-icon-ivory-1024.png',316,164,233)
    txt('主版本',55,414,12,'SC700',G);txt('浅色备选',316,414,12,'SC700',G)
    txt('图层交付',591,163,14,'SC700',G)
    rect(591,202,106,106,'#687D70')
    png(ASSETS/'04_Applications/app-icon-foreground-1024.png',591,202,106)
    txt('透明白色前景',591,321,10,'SC400',G)
    rect(591,361,106,61,G);txt('深绿背景',591,434,10,'SC400',G)
    para('这些是视觉资产与基础图层，不是已配置完成的 Icon Composer 或 App 工程。平台的深色、透明与着色外观在接入阶段再核对。',48,474,W-96,10)
    link('Apple App icons 官方说明','https://developer.apple.com/design/human-interface-guidelines/app-icons',48,526,9.5)
    done()

    page(8,'应用模板','用于项目演示、菜单立牌和设备标贴。模板中的文字与 QR 区域可在 Figma 源稿内替换。')
    txt('演示封面',48,149,12,'SC700',G)
    svg(ASSETS/'04_Applications/presentation-cover.svg',48,179,466)
    txt('菜单立牌',568,149,12,'SC700',G)
    svg(ASSETS/'04_Applications/menu-sign.svg',590,179,173)
    txt('设备标贴比例',48,462,11,'SC700',G)
    svg(ASSETS/'04_Applications/equipment-nameplate.svg',48,485,285)
    para('菜单模板内的 QR 为明确占位区域，使用前替换为正式餐单码。设备标贴展示排版比例，实际尺寸按外壳可用平面确认。',374,469,389,9.5)
    done()

    page(9,'禁止用法','保持纯碗、字标路径、比例与配色。以下示例仅用于说明错误做法，不属于可用资产。')
    modes=[('不拉伸','stretch'),('不旋转','rotate'),('不随意换色','color'),('不使用低对比','low'),('不改成空心描边','outline'),('不裁切标志','crop')]
    for j,(title,mode) in enumerate(modes):
        x=48+(j%3)*255;y=157+(j//3)*188
        rect(x,y,235,151,C)
        txt('×',x+12,y+10,20,'SC700',ERROR);txt(title,x+39,y+15,11,'SC700',G)
        if mode=='stretch':logo('horizontal','green',x+19,y+55,197,76,stretch=True)
        elif mode=='rotate':
            c.saveState();cx=x+117;cy=H-y-94;c.translate(cx,cy);c.rotate(14);d=drawing(ASSETS/'01_Logos/SVG/horizontal-green.svg');sc=196/d.width;d.scale(sc,sc);renderPDF.draw(d,c,-98,-d.height*sc/2);c.restoreState()
        elif mode=='color':logo('horizontal','green',x+19,y+71,197,override='#4D77CF')
        elif mode=='low':logo('horizontal','green',x+19,y+71,197,override='#CED7CF')
        elif mode=='outline':logo('horizontal','green',x+19,y+71,197,override=G,outline=True)
        else:
            c.saveState();p=c.beginPath();p.rect(x+48,H-y-127,144,72);c.clipPath(p,stroke=0);logo('horizontal','green',x+15,y+73,212);c.restoreState()
    done()

    page(10,'字体商用许可核查','核查日期：2026-09-18。当前字标与所选中文字体均采用 SIL Open Font License 1.1。')
    for x,t in [(48,'字体'),(235,'在本套中的角色'),(500,'许可'),(688,'官方依据')]:txt(t,x,157,11,'SC700',G)
    line(48,182,W-48,182)
    fonts=[('Manrope','Logo / 英文排版','https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/OFL.txt'),
           ('Noto Sans TC','繁体中文','https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/OFL.txt'),
           ('Noto Sans SC','简体中文','https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/OFL.txt'),
           ('Inter','历史对照标注，非当前主字体','https://raw.githubusercontent.com/rsms/inter/master/LICENSE.txt')]
    for j,(name,role,url) in enumerate(fonts):
        y=200+j*55;txt(name,48,y,12,'M600',G);txt(role,235,y,10,'SC400',I);txt('OFL 1.1',500,y,11,'M500',G);link('官方许可',url,688,y,10);line(48,y+34,W-48,y+34)
    bullets=['可用于商业 Logo、网站、App 和印刷，无需另付字体授权费。',
             '随包分发字体文件时保留版权和完整 OFL；不要单独出售字体文件。',
             '字体许可不会要求把 Logo 或设计作品按 OFL 开源；修改字库另按许可执行。']
    for j,t in enumerate(bullets):para('• '+t,48,436+j*26,W-96,10)
    link('SIL OFL FAQ：Logo、图形与字体再分发','https://openfontlicense.org/ofl-faq/',48,522,9.5)
    done()

    page(11,'文件交付与使用','生产文件、应用模板、字体许可与可编辑源信息分开整理，方便组内协作与供应商使用。')
    folders=[('01_Logos','12 个基础版本的 SVG 与透明 PNG'),('02_Guidelines','本规范、矢量资产总表及 VI 总览图'),('03_Tokens','颜色、字体和间距的 JSON / CSS 设计令牌'),('04_Applications','App 图标与图层、演示封面、菜单立牌、设备标贴'),('05_Fonts_and_Licences','原始字体、完整许可、官方来源及校验信息'),('06_Source','可编辑字标 SVG、Figma 源稿位置与规则说明')]
    for j,(folder,desc) in enumerate(folders):
        y=155+j*49;txt(folder,48,y,13,'M600',G);para(desc,268,y+1,W-316,11);line(48,y+34,W-48,y+34)
    rect(48,467,W-96,68,C)
    para('放大或加工选 SVG；插入文档选 PNG；阅读规范选 PDF。正式字标已转轮廓，可编辑文字另存，编辑前安装随包的 Manrope 字体。',65,483,W-130,10.5)
    done();c.save()

def master():
    global c,page_no
    c=canvas.Canvas(str(MASTER),pagesize=(W,H),pageCompression=1)
    c.setTitle('Senplate Vector Assets Master V1');c.setAuthor('Senplate / Group 2')
    for n,(form,title) in enumerate([('symbol','独立图形'),('wordmark','独立字标'),('horizontal','横向组合'),('stacked','上下组合')],1):
        page_no=n;rect(0,0,W,H,WHITE);txt('Senplate / Vector assets master',48,27,9,'M500',G);txt(title,48,65,27,'SC700',G)
        para('标志为矢量路径。反白版本放在深绿参考底上；单独使用时请取同名透明 SVG。',48,111,W-96,10.5)
        for j,(col,bg,label) in enumerate([('green',C,'GREEN'),('black',WHITE,'BLACK'),('white',G,'REVERSE')]):
            x=48+j*255;rect(x,181,235,272,bg,S if bg==WHITE else None)
            fc=WHITE if col=='white' else G;txt(label,x+17,197,10,'M600',fc)
            if form=='symbol':logo(form,col,x+42,270,150,107)
            elif form=='wordmark':logo(form,col,x+19,281,197,70)
            elif form=='horizontal':logo(form,col,x+18,292,199,48)
            else:logo(form,col,x+20,260,195,128)
            txt(form+'-'+col+'.svg',x+17,472,9,'M400',G)
        footer(4);done()
    c.save()

guide();master()
bad=[r for r in checks if r['box'][0]<-1 or r['box'][1]<0 or r['box'][0]+r['box'][2]>W+1 or r['box'][1]+r['box'][3]>H+1]
(QA/'pdf-layout-checks.json').write_text(json.dumps({'page_size':[W,H],'text_boxes':len(checks),'outside_page':bad},ensure_ascii=False,indent=2))
print(json.dumps({'guide':str(GUIDE),'master':str(MASTER),'outside_page_text_boxes':len(bad),'contrast_green_ivory':contrast(G,C)},ensure_ascii=False))
if bad: raise RuntimeError('Text outside page bounds')
