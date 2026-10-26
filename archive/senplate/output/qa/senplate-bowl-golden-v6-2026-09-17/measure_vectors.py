from pathlib import Path
import re,json,numpy as np
Q=Path(__file__).parent
g=json.loads((Q/'figma-geometry.json').read_text());p=json.loads((Q/'golden-construction.json').read_text());mark=next(v for v in g['vectors'] if v['id']=='78:9')
def parse(data):
 tokens=re.findall(r'[MLCHVZ]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?',data);i=0;cur=None;start=None;loops=[];loop=[]
 while i<len(tokens):
  cmd=tokens[i];i+=1
  if cmd=='M':
   if loop:loops.append(loop);loop=[]
   cur=np.array([float(tokens[i]),float(tokens[i+1])]);i+=2;start=cur.copy()
  elif cmd=='C':
   xy=np.array([float(x) for x in tokens[i:i+6]]).reshape(3,2);i+=6;loop.append(np.vstack([cur,xy]));cur=xy[-1]
  elif cmd=='L':
   end=np.array([float(tokens[i]),float(tokens[i+1])]);i+=2;loop.append(np.vstack([cur,end]));cur=end
  elif cmd in ['H','V']:
   end=cur.copy();end[0 if cmd=='H' else 1]=float(tokens[i]);i+=1;loop.append(np.vstack([cur,end]));cur=end
  elif cmd=='Z':
   if np.linalg.norm(cur-start)>1e-9:loop.append(np.vstack([cur,start]))
   loops.append(loop);loop=[];cur=start
  else:raise ValueError(cmd)
 if loop:loops.append(loop)
 return loops
loops=[]
for item in mark['paths']:loops+=parse(item['data'])
def at(seg,t):
 if len(seg)==2:return seg[0]*(1-t)+seg[1]*t
 return (1-t)**3*seg[0]+3*(1-t)**2*t*seg[1]+3*(1-t)*t*t*seg[2]+t**3*seg[3]
ys=[]
for loop in loops:
 for seg in loop:
  if len(seg)==2:
   if abs(seg[1,0]-seg[0,0])<1e-10:continue
   roots=[(160-seg[0,0])/(seg[1,0]-seg[0,0])]
  else:
   x=seg[:,0];co=[-x[0]+3*x[1]-3*x[2]+x[3],3*x[0]-6*x[1]+3*x[2],-3*x[0]+3*x[1],x[0]-160]
   while len(co)>1 and abs(co[0])<1e-10:co.pop(0)
   roots=np.roots(co)
  for root in roots:
   if abs(np.imag(root))<1e-8 and -1e-8<=np.real(root)<=1+1e-8:ys.append(float(at(seg,float(np.real(root)))[1]))
unique=[]
for y in sorted(ys):
 if not unique or abs(y-unique[-1])>1e-5:unique.append(y)
assert len(unique)==8,unique
footwalls=[]
for seg in loops[0]:
 if len(seg)==2 and abs(seg[1,0]-seg[0,0])<1e-8 and max(seg[:,1])>190 and abs(seg[1,1]-seg[0,1])>15:footwalls.append(float(seg[0,0]))
assert len(footwalls)==2,footwalls
sig=g['signature'];ch=sig['children'];measured={'A_rim_width':mark['w'],'B_body_height':unique[5],'C_foot_width':max(footwalls)-min(footwalls),'D_mouth_ellipse_height':unique[3],'E_signature_gap':ch[1]['x']-ch[0]['x']-ch[0]['w'],'F_foot_below_body':unique[-1]-unique[5]}
values=list(measured.values());ratios=[values[i]/values[i+1] for i in range(5)];phi=p['phi'];errors=[abs(v-phi) for v in ratios]
assert max(errors)<0.0001,ratios
pts=np.array([at(seg,t) for seg in loops[0] for t in np.linspace(0,1,41)])
mirrored=pts.copy();mirrored[:,0]=320-mirrored[:,0]
distances=np.sqrt(((mirrored[:,None,:]-pts[None,:,:])**2).sum(axis=2)).min(axis=1)
assert float(distances.max())<.005,float(distances.max())
target=p['dimensions'];expected=[target['rim_width'],target['body_height_including_back_rim'],target['foot_width'],target['mouth_ellipse_height'],target['signature_gap'],target['foot_extension_below_body']]
dimension_errors=[abs(a-b) for a,b in zip(values,expected)]
assert max(dimension_errors)<.001,dimension_errors
report={'method':'Independent measurement from production Figma vector paths, not the target-parameter JSON. Vertical-line intersections identify actual cavity, rim seam, body-base seam and foot; outer-profile vertical edges identify foot width.','centerline_x':160,'centerline_intersections_y':unique,'measured_design_units':measured,'successive_ratios':ratios,'absolute_phi_errors':errors,'target_dimension_absolute_errors':dimension_errors,'dimension_tolerance':.001,'ratio_tolerance':.0001,'outer_profile_mirror_sample_count':len(pts),'outer_profile_mirror_max_distance':float(distances.max()),'note':'Small differences reflect native Boolean/path rounding. Body height excludes the foot. Only the outer profile is symmetric; the level notch is intentionally offset.'}
(Q/'measured-golden-ratios.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
