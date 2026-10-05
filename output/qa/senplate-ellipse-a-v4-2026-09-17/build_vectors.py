from pathlib import Path
from math import sqrt,sin,cos,asin,pi,hypot
import json,xml.etree.ElementTree as E
R=Path('/Users/tantalum/Documents/ChatGPT/FYP');A=R/'output/brand/2026-09-17-senplate-ellipse-a-v4';Q=R/'output/qa/senplate-ellipse-a-v4-2026-09-17';A.mkdir(parents=True,exist_ok=True)
phi=(1+sqrt(5))/2;W=320.;EH=W/phi**2;PW=EH;PH=PW/phi;D=PH/phi;clear=W/phi**7;Y0=D+clear;H=Y0+EH;CX=W/2;CY=Y0+EH/2;RX=W/2;RY=EH/2;IRX=RX-W/phi**6;IRY=PH/2;opening=PW+2*clear;alpha=asin(opening/W)
left=-pi/2-alpha;right=-pi/2+alpha;scale=EH/120;wordH=153*scale;wordW=657*scale;gap=D/phi;wx=W+gap;wy=(H-wordH)/2;LW=wx+wordW
def n(v):return f'{v:.9f}'.rstrip('0').rstrip('.')
def xy(p):return ' '.join(n(x) for x in p)
def point(rx,ry,t):return (CX+rx*cos(t),CY+ry*sin(t))
ol=point(RX,RY,left);orr=point(RX,RY,right);inner_alpha=alpha;inner_left=left;inner_right=right;il=point(IRX,IRY,inner_left);ir=point(IRX,IRY,inner_right)
handle=2*hypot(orr[0]-ir[0],orr[1]-ir[1])/3
def unit(v):
 length=hypot(*v);return (v[0]/length,v[1]/length)
to=unit((RX*sin(right),-RY*cos(right)));ti=unit((-IRX*sin(right),IRY*cos(right)))
cp1=(orr[0]+handle*to[0],orr[1]+handle*to[1]);cp2=(ir[0]-handle*ti[0],ir[1]-handle*ti[1])
mirror=lambda p:(W-p[0],p[1])
rim=f'M {xy(ol)} A {n(RX)} {n(RY)} 0 1 0 {xy(orr)} C {xy(cp1)} {xy(cp2)} {xy(ir)} A {n(IRX)} {n(IRY)} 0 1 1 {xy(il)} C {xy(mirror(cp2))} {xy(mirror(cp1))} {xy(ol)} Z'
def path(d,tr=''):return '<path fill-rule="evenodd" d="'+d+'"'+(' transform="'+tr+'"' if tr else '')+'/>'
def svg(w,h,body,title,color='#163F35'):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(w)}" height="{n(h)}" viewBox="0 0 {n(w)} {n(h)}" fill="{color}"><title>{title}</title>{body}</svg>\n'
ns='{http://www.w3.org/2000/svg}'
def serial(e):return E.tostring(e,encoding='unicode').replace('ns0:','').replace(':ns0','')
prior=E.fromstring((R/'output/brand/2026-09-17-senplate-golden-a-v3/senplate-mark-green.svg').read_text())
parts=prior.findall(ns+'path');dot=serial(parts[0]);portion=path(parts[2].attrib['d'],f'translate({n((W-PW)/2)} {n(Y0)})')
mark=dot+path(rim)+portion
oldword=E.fromstring((R/'output/brand/2026-09-17-senplate-refined-a-v2/senplate-wordmark-green.svg').read_text());word=''.join(serial(x) for x in list(oldword) if x.tag==ns+'path')
oldcap=E.fromstring((R/'output/brand/2026-09-17-senplate-refined-a-v2/senplate-capital-s-comparison.svg').read_text());cap=''.join(serial(x) for x in oldcap.find(ns+'g'))
def positioned(s):return f'<g transform="translate({n(wx-2*scale)} {n(wy-2*scale)}) scale({n(scale)})">{s}</g>'
for name,color in [('green','#163F35'),('black','#000000'),('white','#FFFFFF')]:
 (A/f'senplate-mark-{name}.svg').write_text(svg(W,H,mark,'Senplate symmetric ellipse rim',color))
 (A/f'senplate-logo-{name}.svg').write_text(svg(LW,H,mark+positioned(word),'senplate',color))
(A/'senplate-wordmark-green.svg').write_text(svg(wordW,wordH,f'<g transform="scale({n(scale)}) translate(-2 -2)">{word}</g>','senplate wordmark'))
(A/'senplate-capital-s-comparison.svg').write_text(svg(LW,H,mark+positioned(cap),'Senplate initial capital comparison only'))
(A/'bowl-only.svg').write_text(svg(W,EH,path(rim,f'translate(0 {-Y0})'),'Bowl geometry for symmetry inspection'))
grid=f'<g fill="none" stroke="#B48A56" stroke-width="0.7"><ellipse cx="{n(CX)}" cy="{n(CY)}" rx="{n(RX)}" ry="{n(RY)}"/><ellipse cx="{n(CX)}" cy="{n(CY)}" rx="{n(IRX)}" ry="{n(IRY)}"/><path d="M {n(CX)} {n(Y0-12)} V {n(H)} M 0 {n(CY)} H {n(W)}" stroke-dasharray="2 2"/></g>'
(A/'ellipse-construction-grid.svg').write_text(svg(W,H,mark+grid,'Shared ellipse construction overlay'))
errors=[];curvature_errors=[]
def curvature(a,b,t):return a*b/(a*a*sin(t)**2+b*b*cos(t)**2)**1.5
for i in range(361):
 t=i*pi/360
 for a,b in [(RX,RY),(IRX,IRY)]:
  p=point(a,b,t);m=point(a,b,pi-t);errors.append(max(abs(p[0]+m[0]-W),abs(p[1]-m[1])))
  curvature_errors.append(abs(curvature(a,b,t)-curvature(a,b,pi-t)))
record={'phi':phi,'method':'Two concentric axis-aligned ellipses, mirrored cut angles and matched rounded terminals tangent to both ellipse boundaries. Whole symbol intentionally retains asymmetric portion and sensing dot.','dimensions':{'symbol_width':W,'symbol_height':H,'outer_ellipse_width':W,'outer_ellipse_height':EH,'ellipse_center':[CX,CY],'outer_radii':[RX,RY],'inner_radii':[IRX,IRY],'portion_width':PW,'portion_height':PH,'portion_top':Y0,'dot_diameter':D,'dot_center_x':W/phi,'dot_to_portion_vertical_gap':clear,'opening_span_outer':opening,'outer_cap_angles_degrees':[left*180/pi,right*180/pi],'inner_cap_angles_degrees':[inner_left*180/pi,inner_right*180/pi],'right_cap_controls':[cp1,cp2],'left_cap_controls':[mirror(cp2),mirror(cp1)],'outer_endpoints':[ol,orr],'inner_endpoints':[il,ir],'front_rim_thickness':RY-IRY,'side_rim_thickness':RX-IRX,'logo_gap':gap,'logo_width':LW,'word_height':wordH,'word_stem_height':EH},'ratios':{'outer_ellipse_width_over_height':W/EH,'outer_ellipse_height_over_inner_height':EH/(2*IRY),'portion_width_over_height':PW/PH,'portion_height_over_dot_diameter':PH/D,'dot_diameter_over_logo_gap':D/gap},'symmetry':{'axis_x':CX,'sample_pairs':722,'max_mirror_coordinate_error':max(errors),'max_curvature_error':max(curvature_errors),'both_caps':'same tangent rounded cap mirrored across x=160'},'superseded_v3_constraints':['Whole-mark outer box no longer forced to phi.','Separate left/right freeform rim and one round cap removed.'],'typecase':'Lowercase logo retained; iOS app display name Senplate. Initial capital comparison not selected.'}
(Q/'ellipse-construction.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False))
