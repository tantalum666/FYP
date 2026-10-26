import runpy,json,numpy as np,xml.etree.ElementTree as E
from pathlib import Path
Q=Path(__file__).parent;R=Q.parents[2];A=R/'output/brand/2026-09-17-senplate-bowl-golden-v6'
m=runpy.run_path(str(Q/'measure_vectors.py'));parse=m['parse'];at=m['at'];phi=m['phi'];ns='{http://www.w3.org/2000/svg}'
def loops_of(file):return [loop for p in E.fromstring(file.read_text()).findall('.//'+ns+'path') for loop in parse(p.attrib['d'])]
def center_hits(loops,x):
 ys=[]
 for loop in loops:
  for seg in loop:
   if len(seg)==2:
    if abs(seg[1,0]-seg[0,0])<1e-10:continue
    roots=[(x-seg[0,0])/(seg[1,0]-seg[0,0])]
   else:
    v=seg[:,0];co=[-v[0]+3*v[1]-3*v[2]+v[3],3*v[0]-6*v[1]+3*v[2],-3*v[0]+3*v[1],v[0]-x]
    while len(co)>1 and abs(co[0])<1e-10:co.pop(0)
    roots=np.roots(co)
   for t in roots:
    if abs(np.imag(t))<1e-8 and -1e-8<=np.real(t)<=1+1e-8:ys.append(float(at(seg,float(np.real(t)))[1]))
 unique=[]
 for y in sorted(ys):
  if not unique or abs(y-unique[-1])>1e-5:unique.append(y)
 return unique
def bounds(loops):
 values=[]
 for loop in loops:
  for seg in loop:
   ts=[0,1]
   if len(seg)==4:
    for axis in [0,1]:
     v=seg[:,axis];co=[3*(-v[0]+3*v[1]-3*v[2]+v[3]),2*(3*v[0]-6*v[1]+3*v[2]),-3*v[0]+3*v[1]]
     while len(co)>1 and abs(co[0])<1e-10:co.pop(0)
     for t in np.roots(co):
      if abs(np.imag(t))<1e-8 and 0<np.real(t)<1:ts.append(float(np.real(t)))
   values.extend(at(seg,t) for t in ts)
 points=np.array(values);return [float(points[:,0].min()),float(points[:,1].min()),float(points[:,0].max()),float(points[:,1].max())]
loops=loops_of(A/'senplate-symbol-green.svg');ys=center_hits(loops,160);assert len(ys)==8,ys
walls=[float(seg[0,0]) for seg in loops[0] if len(seg)==2 and abs(seg[1,0]-seg[0,0])<1e-8 and max(seg[:,1])>190 and abs(seg[1,1]-seg[0,1])>15]
assert len(walls)==2,walls
paths=E.fromstring((A/'senplate-logo-green.svg').read_text()).findall('.//'+ns+'path');assert len(paths)==9,len(paths)
mark_box=bounds(parse(paths[0].attrib['d']));word_box=bounds([loop for path in paths[1:] for loop in parse(path.attrib['d'])])
values=[mark_box[2]-mark_box[0],ys[5],max(walls)-min(walls),ys[3],word_box[0]-mark_box[2],ys[-1]-ys[5]]
ratios=[values[i]/values[i+1] for i in range(5)];target=m['expected'];errors=[abs(a-b) for a,b in zip(values,target)]
assert max(errors)<.001,errors
assert max(abs(v-phi) for v in ratios)<.0001,ratios
out={'artifact':'Delivered SVG files','measured_A_to_F':values,'centerline_intersections_y':ys,'signature_mark_bounds':mark_box,'signature_word_bounds':word_box,'successive_ratios':ratios,'target_dimension_absolute_errors':errors,'max_dimension_error':max(errors),'dimension_tolerance':.001,'ratio_tolerance':.0001}
(Q/'measured-svg-export.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
