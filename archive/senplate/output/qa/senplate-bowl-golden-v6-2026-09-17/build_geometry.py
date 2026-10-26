from pathlib import Path
from math import sqrt
import json
R=Path('/Users/tantalum/Documents/ChatGPT/FYP');Q=R/'output/qa/senplate-bowl-golden-v6-2026-09-17';A=R/'output/brand/2026-09-17-senplate-bowl-golden-v6';A.mkdir(parents=True,exist_ok=True)
phi=(1+sqrt(5))/2;W=320.;BH=W/phi;FW=W/phi**2;MH=W/phi**3;G=W/phi**4;FH=W/phi**5;T=W/phi**7;S=W/phi**8;cx=W/2;cy=MH/2;RADIUS=W/2;H=BH+FH;fx0=cx-FW/2;fx1=cx+FW/2;fy=cy+sqrt(RADIUS**2-(FW/2)**2);footSide=H-FH/2
irx=W/2-T;iry=MH/2-T/phi;stepx=W/phi;stepR=stepx+T;levelY=MH/phi
def n(x):return f'{x:.9f}'.rstrip('0').rstrip('.')
def pt(x,y):return n(x)+' '+n(y)
def lower(rx,ry,x):return cy+ry*sqrt(1-((x-cx)/rx)**2)
outline=f'M {pt(0,cy)} A {pt(W/2,MH/2)} 0 0 1 {pt(W,cy)} A {pt(RADIUS,RADIUS)} 0 0 1 {pt(fx1,fy)} L {pt(fx1,footSide)} A {pt(FW/2,FH/2)} 0 0 1 {pt(fx0,footSide)} L {pt(fx0,fy)} A {pt(RADIUS,RADIUS)} 0 0 1 {pt(0,cy)} Z'
xl=cx-irx*sqrt(1-((levelY-cy)/iry)**2)
cavity=f'M {pt(T,cy)} A {pt(irx,iry)} 0 0 1 {pt(W-T,cy)} A {pt(irx,iry)} 0 0 1 {pt(stepx,lower(irx,iry,stepx))} L {pt(stepx,levelY)} L {pt(xl,levelY)} A {pt(irx,iry)} 0 0 1 {pt(T,cy)} Z'
rim=f'M {pt(T,lower(W/2,MH/2,T))} A {pt(W/2,MH/2)} 0 0 0 {pt(W-T,lower(W/2,MH/2,W-T))} L {pt(W-T,lower(W/2,MH/2+S,W-T))} A {pt(W/2,MH/2+S)} 0 0 1 {pt(T,lower(W/2,MH/2+S,T))} Z'
footL=fx0+T;footR=fx1-T
foot=f'M {pt(footL,lower(RADIUS,RADIUS,footL))} A {pt(RADIUS,RADIUS)} 0 0 0 {pt(footR,lower(RADIUS,RADIUS,footR))} L {pt(footR,lower(RADIUS,RADIUS+S,footR))} A {pt(RADIUS,RADIUS+S)} 0 0 1 {pt(footL,lower(RADIUS,RADIUS+S,footL))} Z'
bridge=f'M {pt(stepx,levelY)} H {n(stepR)} V {n(lower(W/2,MH/2+S,stepR))} H {n(stepx)} Z'
paths={'outer-body':outline,'mouth-cavity':cavity,'rim-seam':rim,'foot-seam':foot,'level-bridge':bridge}
body=''.join(f'<path id="{name}" d="{d}" fill="'+('#163F35' if name=='outer-body' else '#D85159')+'"/>' for name,d in paths.items())
svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(W)}" height="{n(H)}" viewBox="0 0 {n(W)} {n(H)}">{body}</svg>\n'
(Q/'boolean-source.svg').write_text(svg)
params={'phi':phi,'units':'vector design units','dimensions':{'rim_width':W,'body_height_including_back_rim':BH,'body_base_seam_y':BH,'foot_width':FW,'mouth_ellipse_height':MH,'signature_gap':G,'foot_extension_below_body':FH,'total_symbol_height':H,'body_semicircle_radius':RADIUS,'ellipse_center':[cx,cy],'rim_side_inset':T,'rim_vertical_inset':T/phi,'seam_center_thickness':S,'step_x':stepx,'step_width':T,'step_level_y':levelY,'foot_side_start':[fx0,fx1,fy],'foot_lower_ellipse_center_y':footSide,'wordmark_ink_height_target':BH},'ratios':{'rim_width_over_body_height':W/BH,'body_height_over_foot_width':BH/FW,'foot_width_over_mouth_height':FW/MH,'mouth_height_over_signature_gap':MH/G,'signature_gap_over_foot_extension':G/FH},'construction_note':'Upper rim is half ellipse; lower body is a mirrored semicircle. Boolean subtraction unites the cavity, measurement notch and seams. Main dimensions follow a golden sequence; exact body height ends at the body-base seam, excluding the foot.','glyph_note':'Typeface chosen for a clean editable reconstruction; not claimed to identify the raster font.'}
(Q/'golden-construction.json').write_text(json.dumps(params,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(params,ensure_ascii=False))
