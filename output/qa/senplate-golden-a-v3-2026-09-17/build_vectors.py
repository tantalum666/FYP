from pathlib import Path
from math import sqrt
import json,xml.etree.ElementTree as E,copy
R=Path('/Users/tantalum/Documents/ChatGPT/FYP');A=R/'output/brand/2026-09-17-senplate-golden-a-v3';Q=R/'output/qa/senplate-golden-a-v3-2026-09-17';A.mkdir(parents=True,exist_ok=True)
phi=(1+sqrt(5))/2;W=320.;H=W/phi;F=W/phi**2;FH=W/phi**3;D=W/phi**4;gap=W/phi**5;inset=W/phi**6;back=W/phi**7;K=4*(sqrt(2)-1)/3
Y0=H-F;CY=Y0+D;IB=H-gap;CX=W/phi;rad=D/2;capX=W-FH;cr=back/2;midY=Y0+cr;L=(W-F)/2;stem=H/phi;scale=stem/120;wordH=153*scale;wordW=657*scale;wx=W+gap;wy=(H-wordH)/2;logoW=wx+wordW
def n(x):return f'{x:.8f}'.rstrip('0').rstrip('.')
def P(cmd,*xy):return cmd+' '+' '.join(n(x) for x in xy)
def path(d,tr=''):return '<path fill-rule="evenodd" d="'+d+'"'+(' transform="'+tr+'"' if tr else '')+'/>'
def svg(w,h,body,title,color='#163F35'):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(w)}" height="{n(h)}" viewBox="0 0 {n(w)} {n(h)}" fill="{color}"><title>{title}</title>{body}</svg>\n'
dot=' '.join([P('M',CX+rad,rad),P('C',CX+rad,rad+K*rad,CX+K*rad,D,CX,D),P('C',CX-K*rad,D,CX-rad,rad+K*rad,CX-rad,rad),P('C',CX-rad,rad-K*rad,CX-K*rad,0,CX,0),P('C',CX+K*rad,0,CX+rad,rad-K*rad,CX+rad,rad),'Z'])
rim=' '.join([P('M',W/2,Y0),P('C',.22*W,Y0,0,Y0+inset,0,CY),P('C',0,CY+K*(H-CY),W/2*(1-K),H,W/2,H),P('C',W/2*(1+K),H,W,CY+K*(H-CY),W,CY),P('C',W,CY-.55*D,capX+.15*W,Y0,capX,Y0),P('C',capX-K*cr,Y0,capX-cr,midY-K*cr,capX-cr,midY),P('C',capX-cr,midY+K*cr,capX-K*cr,Y0+back,capX,Y0+back),P('C',capX+.11*W,Y0+back,W-inset,CY-.45*D,W-inset,CY),P('C',W-inset,CY+K*(IB-CY),W/2+K*(W/2-inset),IB,W/2,IB),P('C',W/2-K*(W/2-inset),IB,inset,CY+K*(IB-CY),inset,CY),P('C',inset,CY-.45*D,.27*W,Y0+back,W/2-back,Y0+back),'Z'])
portion=' '.join([P('M',0,.90*FH),P('C',0,.86*FH,.03*F,.83*FH,.07*F,.77*FH),P('C',.32*F,.395*FH,.49*F,0,.62*F,0),P('C',.74*F,0,F,.62*FH,F,.88*FH),P('C',F,.95*FH,.75*F,FH,.48*F,FH),P('C',.30*F,FH,0,.96*FH,0,.90*FH),'Z'])
mark=path(dot)+path(rim)+path(portion,f'translate({n(L)} {n(Y0)})')
ns={'s':'http://www.w3.org/2000/svg'}
def raw_children(file):
 e=E.fromstring(file.read_text());return ''.join(E.tostring(x,encoding='unicode').replace('ns0:','').replace(':ns0','') for x in list(e) if x.tag.endswith('path'))
wordSource=R/'output/brand/2026-09-17-senplate-refined-a-v2/senplate-wordmark-green.svg'
word=raw_children(wordSource)
capRoot=E.fromstring((R/'output/brand/2026-09-17-senplate-refined-a-v2/senplate-capital-s-comparison.svg').read_text())
capGroup=capRoot.find('s:g',ns)
cap=''.join(E.tostring(x,encoding='unicode').replace('ns0:','').replace(':ns0','') for x in capGroup)
def positioned(body):return f'<g transform="translate({n(wx-2*scale)} {n(wy-2*scale)}) scale({n(scale)})">{body}</g>'
for name,color in [('green','#163F35'),('black','#000000'),('white','#FFFFFF')]:
 (A/f'senplate-mark-{name}.svg').write_text(svg(W,H,mark,'Senplate golden ratio symbol',color))
 (A/f'senplate-logo-{name}.svg').write_text(svg(logoW,H,mark+positioned(word),'senplate',color))
(A/'senplate-wordmark-green.svg').write_text(svg(wordW,wordH,f'<g transform="scale({n(scale)}) translate(-2 -2)">{word}</g>','senplate wordmark'))
(A/'senplate-capital-s-comparison.svg').write_text(svg(logoW,H,mark+positioned(cap),'Senplate initial capital comparison only'))
grid=f'<g fill="none" stroke="#B48A56" stroke-width="0.6"><rect x="0.3" y="0.3" width="{n(W-.6)}" height="{n(H-.6)}"/><path d="M {n(CX)} 0 V {n(H)} M 0 {n(Y0)} H {n(W)}" stroke-dasharray="2 2"/><rect x="{n(L)}" y="{n(Y0)}" width="{n(F)}" height="{n(FH)}"/><path d="M {n(CX-rad)} {n(rad)} H {n(CX+rad)}"/></g>'
(A/'construction-grid.svg').write_text(svg(W,H,mark+grid,'Golden ratio construction overlay'))
record={'phi':phi,'unit':'vector design units, not hardware millimetres','dimensions':{'symbol_width':W,'symbol_height':H,'plate_height':F,'plate_top':Y0,'portion_width':F,'portion_height':FH,'portion_left':L,'dot_diameter':D,'dot_center_x':CX,'dot_center_y':rad,'logo_gap':gap,'front_rim_thickness':gap,'back_rim_band':back,'inner_front_y':IB,'word_stem_height_l':stem,'word_uniform_scale':scale,'word_visible_width':wordW,'word_visible_height':wordH,'word_offset':[wx,wy],'logo_width':logoW},'ratios':{'symbol_width_over_height':W/H,'portion_width_over_height':F/FH,'dot_left_segment_over_right':CX/(W-CX),'dot_diameter_over_logo_gap':D/gap,'symbol_height_over_l_stem':H/stem},'construction':'Dimensions are evaluated from phi before paths are drawn. Main dimensions use golden divisions; smooth curves and endpoints are optical geometry, not claimed to be generated entirely by a golden spiral.','typecase':'Lowercase retained; initial capital comparison not selected.','old_version':'V2 was optical reconstruction, not a golden ratio design.'}
(Q/'golden-ratio-construction.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False))
