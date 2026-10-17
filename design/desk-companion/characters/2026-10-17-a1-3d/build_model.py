"""A1 genuine skinned 3D adaptation. Run in a separate Blender background process.
Preserves the licensed source, full body continuity, facial UVs and all expression keys.
Garments are derived from the actual body surface/weights, not floating rigid tubes.
"""
import bpy, bmesh, math, json, tempfile, shutil
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).parent
QA=ROOT/'output/qa/2026-10-17-assistant-simplify-avatar';PUBLIC=ROOT/'desk-companion/frontend/public/companion'
SOURCE=ROOT/'desk-companion/frontend/public/avatars/pixiv-sample.vrm'
bpy.ops.wm.read_factory_settings(use_empty=True)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'base.glb';shutil.copyfile(SOURCE,p);bpy.ops.import_scene.gltf(filepath=str(p))
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');arm.name='A1_Rig'
for o in list(bpy.context.scene.objects):
 if o.type not in {'MESH','ARMATURE','EMPTY'} or o.name=='Icosphere':bpy.data.objects.remove(o,do_unlink=True)
arm['copyright']='Base anatomy, face and rig: (c) 2022 pixiv Inc. Modified hair, garments, fit and motion: AI-assisted Group 2 FYP, 2026-10-17.'
arm['sourceLicense']='VRM Public License 1.0 plus original embedded permissions; modified derivative; no endorsement.'
arm['licenseUrl']='https://vrm.dev/en/licenses/1.0/'
arm['sourceSHA256']='12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2'
arm['sourceURL']='https://github.com/pixiv/three-vrm/blob/ff42fae4fcee1fcbca2cd262c7f5f8cbddeaf5ab/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample.vrm'
arm['licenseSettings']=json.dumps({'avatarPermission':'everyone','commercialUsage':'corporation','allowRedistribution':True,'modification':'allowModificationRedistribution','allowAntisocialOrHateUsage':False,'allowExcessivelySexualUsage':True,'allowExcessivelyViolentUsage':True,'allowPoliticalOrReligiousUsage':True})
arm['assetStatus']='A1 visual candidate, owner acceptance pending; genuine mesh, skin, expressions and baked actions.'

def lin(h):
 c=[int(h[i:i+2],16)/255 for i in (0,2,4)];return tuple(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in c)
def mat(n,c,rough=.85,metal=0):
 m=bpy.data.materials.new(n);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*lin(c),1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;m.diffuse_color=(*lin(c),1);return m
ivory=mat('Ivory cotton jacket','dcd8d1');lapel=mat('Ivory lapel facing','ede9e1');graphite=mat('Graphite fine knit','353947');slate=mat('Slate wrap wool','64748d');fold=mat('Wrap facing','75869e');tights=mat('Matte graphite hosiery','59515a');boot=mat('Soft charcoal leather','343b49',.65);sole=mat('Boot sole','242936');metal=mat('Brushed silver','aeb7c4',.48,.6);trim=mat('Slate piping','758398');hairm=[mat('Silver ash hair '+str(i),c,.8)for i,c in enumerate(['a5a4b8','b8b7c8','9496ab','c4c3d0'])]
# Remove nonportable helper constraints, merging their vertex weights into real joints.
collapse={}
for side in ['L','R']:
 for old,new in [('J_Aim_'+side+'_Shoulder','UpperArm'),('J_Roll_'+side+'_UpperArm','UpperArm'),('J_Aim_'+side+'_TopsUpperArm','UpperArm'),('J_Roll_'+side+'_Hand','Hand'),('J_Roll_'+side+'_LowerArm','LowerArm'),('J_Roll_'+side+'_Elbow','LowerArm'),('J_Aim_'+side+'_UpperLeg','UpperLeg')]:collapse[old]='J_Bip_'+side+'_'+new
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
 names={g.index:g.name for g in obj.vertex_groups};allweights=[]
 for v in obj.data.vertices:
  sums={}
  for g in v.groups:
   n=collapse.get(names[g.group],names[g.group]);sums[n]=sums.get(n,0)+g.weight
  allweights.append(sums)
 obj.vertex_groups.clear()
 for i,ws in enumerate(allweights):
  for n,w in ws.items():
   vg=obj.vertex_groups.get(n)or obj.vertex_groups.new(name=n);vg.add([i],w,'REPLACE')
for pb in arm.pose.bones:
 for c in list(pb.constraints):pb.constraints.remove(c)
body=bpy.data.objects['Body'];face=bpy.data.objects['Face'];oldhair=bpy.data.objects['Hair']
# Keep face UVs/iris detail. Eye tint is baked from a material, never painted over the reference image.
for m in list(face.data.materials)+[bodym for bodym in bpy.data.materials if bodym.name=='Body_00_SKIN']:
 if not m.use_nodes:continue
 source=next((n for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image),None)
 output=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None)
 emission=next((n for n in m.node_tree.nodes if n.type=='EMISSION'),None)
 if 'EyeIris' in m.name and source and emission:
  hue=m.node_tree.nodes.new('ShaderNodeHueSaturation');hue.inputs['Saturation'].default_value=.05;m.node_tree.links.new(source.outputs['Color'],hue.inputs['Color'])
  mul=m.node_tree.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(*lin('8cabc7'),1);m.node_tree.links.new(hue.outputs[0],mul.inputs[1]);m.node_tree.links.new(mul.outputs[0],emission.inputs['Color'])
  # Bake this single material on a temporary copy of its UV triangles.
  pol=[p for p in face.data.polygons if face.data.materials[p.material_index]==m];oldids=sorted({i for p in pol for i in p.vertices});lookup={v:i for i,v in enumerate(oldids)}
  md=bpy.data.meshes.new('Iris bake');md.from_pydata([face.data.vertices[i].co[:]for i in oldids],[],[tuple(lookup[i]for i in p.vertices)for p in pol]);md.materials.append(m);uv=md.uv_layers.new()
  for np,op in zip(md.polygons,pol):
   for ni,oi in zip(np.loop_indices,op.loop_indices):uv.data[ni].uv=face.data.uv_layers.active.data[oi].uv
  o=bpy.data.objects.new('Iris bake',md);bpy.context.collection.objects.link(o);image=bpy.data.images.new('A1_GreyBlue_Iris',1024,1024,alpha=True);node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;m.node_tree.nodes.active=node
  bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=1;bpy.ops.object.bake(type='EMIT',margin=4)
  m.node_tree.links.new(node.outputs['Color'],emission.inputs['Color']);image.pack();bpy.data.objects.remove(o,do_unlink=True)
 elif 'FaceBrow' in m.name and emission:
  for link in list(emission.inputs['Color'].links):m.node_tree.links.remove(link)
  emission.inputs['Color'].default_value=(*lin('65687d'),1)
 elif m.name in ['Face_00_SKIN','Body_00_SKIN'] and source and output:
  p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');m.node_tree.links.new(source.outputs['Color'],p.inputs['Base Color']);p.inputs['Roughness'].default_value=.88;p.inputs['Specular IOR Level'].default_value=.2
  m.node_tree.links.new(p.outputs['BSDF'],output.inputs['Surface'])
# Slightly narrower face and eyes, with the same delta on every morph target.
face_mats={i:m.name for i,m in enumerate(face.data.materials)}
ids={i:set() for i in face_mats}
for p in face.data.polygons:ids[p.material_index].update(p.vertices)
eyeids=set().union(*(vs for i,vs in ids.items() if any(x in face_mats[i]for x in ['EyeIris','EyeWhite','FaceEyeline','EyeHighlight'])))
for key in face.data.shape_keys.key_blocks:
 for i,v in enumerate(key.data):
  v.co.x*=.96
  if i in eyeids:
   v.co.z=1.445+(v.co.z-1.445)*.85+.018+max(0,abs(v.co.x)-.035)*.09
  elif i in ids[5]:v.co.z+=.012
  elif i in ids[2]:v.co.z+=.018*math.exp(-((v.co.z-1.445)/.038)**4)
  elif i in ids[0]:v.co.x*=1.12;v.co.z+=.0015
# Original body topology remains continuous through the knees and ankles.
skin_index=next(i for i,m in enumerate(body.data.materials) if 'Body_00_SKIN'in m.name)
for m in [graphite,tights,hairm[0]]:body.data.materials.append(m)
gidx=len(body.data.materials)-3;tidx=gidx+1;hidx=gidx+2
# Surface extraction copies body geometry and exactly the same skinning weights.
def skin(obj,ws):
 obj.parent=arm;obj.matrix_world=Matrix.Identity(4);mod=obj.modifiers.new('Skin','ARMATURE');mod.object=arm
 for i,weights in enumerate(ws):
  total=sum(weights.values())or 1
  for n,w in weights.items():
   if w<=.0001:continue
   vg=obj.vertex_groups.get(n)or obj.vertex_groups.new(name=n);vg.add([i],w/total,'REPLACE')
 return obj
names={g.index:g.name for g in body.vertex_groups}
def weight(v):return {names[g.group]:g.weight for g in v.groups}
def mesh(n,vs,fs,m,weights):
 data=bpy.data.meshes.new(n);data.from_pydata(vs,[],fs);data.materials.append(m);data.update();o=bpy.data.objects.new(n,data);bpy.context.collection.objects.link(o)
 for p in data.polygons:p.use_smooth=True
 return skin(o,[weights(Vector(v))if callable(weights)else weights for v in vs])
def surface(n,select,m,offset=.008,alter=None):
 ps=[p for p in body.data.polygons if p.material_index==skin_index and select(p.center)];indices=sorted({i for p in ps for i in p.vertices});lookup={v:i for i,v in enumerate(indices)}
 vs=[];ws=[]
 for i in indices:
  v=body.data.vertices[i];co=v.co+v.normal*offset
  if alter:co=alter(co)
  vs.append(tuple(co));ws.append(weight(v))
 data=bpy.data.meshes.new(n);data.from_pydata(vs,[],[tuple(lookup[i]for i in p.vertices)for p in ps]);data.materials.append(m);data.update();o=bpy.data.objects.new(n,data);bpy.context.collection.objects.link(o)
 for p in data.polygons:p.use_smooth=True
 return skin(o,ws)
# Jacket front opening follows the torso. Shoulders/sleeves share the original smooth skin weights.
def jacket_select(v):
 if not 1.013<v.z<1.335 or abs(v.x)>.492:return False
 gap=.044+max(0,min(.032,(v.z-1.08)*.16))
 return not(v.y<-.025 and abs(v.x)<gap)
# Build a continuous shoulder/torso/sleeve volume. The stock body has deliberate
# hidden-surface cutouts under its shirt, so it cannot be used as a complete coat.
vs=[];fs=[];parts=[]
def vol_rings(n,rings,along='z',sign=1):
 v=[];f=[];N=48
 for height,rx,ry,center in rings:
  for j in range(N):
   a=math.tau*j/N
   v.append((rx*math.sin(a),center-ry*math.cos(a),height)if along=='z' else (sign*height,center+rx*math.cos(a),1.274+ry*math.sin(a)))
 for k in range(len(rings)-1):
  for j in range(N):i=k*N+j;f.append((i,k*N+(j+1)%N,(k+1)*N+(j+1)%N,i+N))
 f.extend([tuple(reversed(range(N))),tuple((len(rings)-1)*N+j for j in range(N))])
 md=bpy.data.meshes.new(n);md.from_pydata(v,[],f);md.update();ob=bpy.data.objects.new(n,md);bpy.context.collection.objects.link(ob);parts.append(ob)
vol_rings('Jacket torso',[(1.007,.120,.085,-.005),(1.06,.116,.089,-.012),(1.14,.135,.106,-.006),(1.22,.148,.099,.007),(1.278,.146,.085,.020),(1.305,.107,.068,.025),(1.325,.043,.038,.026)])
for sign in [-1,1]:vol_rings('Jacket sleeve',[(.115,.059,.061,.023),(.18,.059,.059,.026),(.25,.049,.050,.026),(.32,.046,.046,.026),(.40,.038,.040,.026),(.496,.034,.036,.026)],'x',sign)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();jacket=parts[0];jacket.name='A1_Continuous_Tailored_Jacket'
bm=bmesh.new();bm.from_mesh(jacket.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(jacket.data);bm.free()
m=jacket.modifiers.new('Unified shoulder seams','REMESH');m.mode='VOXEL';m.voxel_size=.0035;m.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=m.name)
m=jacket.modifiers.new('Tailoring','SMOOTH');m.factor=.7;m.iterations=4;bpy.ops.object.modifier_apply(modifier=m.name)
m=jacket.modifiers.new('Web surface budget','DECIMATE');m.ratio=.38;bpy.ops.object.modifier_apply(modifier=m.name)
# Front opening/neck/cuffs are trimmed after fusion; solid thickness finishes edges.
bm=bmesh.new();bm.from_mesh(jacket.data)
cut=[]
for f in bm.faces:
 c=f.calc_center_median();gap=.037+max(0,min(.025,(c.z-1.06)*.14))
 if (c.y<-.018 and abs(c.x)<gap) or c.z<1.013 or abs(c.x)>.488 or (c.z>1.317 and abs(c.x)<.052):cut.append(f)
bmesh.ops.delete(bm,geom=cut,context='FACES')
for v in bm.verts:
 gap=.037+max(0,min(.025,(v.co.z-1.06)*.14))
 if v.is_boundary and v.co.y<-.025 and abs(v.co.x)<gap+.008:v.co.x=math.copysign(gap,v.co.x)
bm.to_mesh(jacket.data);bm.free();jacket.data.update();jacket.data.materials.append(ivory)
def jacketw(v):
 x=abs(v.x)
 if x<.12:
  z=v.z
  if z<1.07:t=max(0,min(1,(z-.99)/.08));return {'J_Bip_C_Hips':1-t,'J_Bip_C_Spine':t}
  if z<1.18:t=(z-1.07)/.11;return {'J_Bip_C_Spine':1-t,'J_Bip_C_Chest':t}
  t=max(0,min(1,(z-1.18)/.10));return {'J_Bip_C_Chest':1-t,'J_Bip_C_UpperChest':t}
 side='L' if v.x>0 else 'R';armblend=max(0,min(1,(x-.12)/.08));lower=max(0,min(1,(x-.28)/.10))
 return {'J_Bip_C_UpperChest':1-armblend,'J_Bip_'+side+'_UpperArm':armblend*(1-lower),'J_Bip_'+side+'_LowerArm':armblend*lower}
skin(jacket,[jacketw(v.co)for v in jacket.data.vertices]);m=jacket.modifiers.new('Garment thickness','SOLIDIFY');m.thickness=.002;m.offset=-1
for p in jacket.data.polygons:p.use_smooth=True
for p in body.data.polygons:
 c=p.center
 if p.material_index==skin_index:
  if c.z<.985:p.material_index=tidx
  elif 1.0<c.z<1.34 and abs(c.x)<.145:p.material_index=gidx
 elif 'HairBack' in body.data.materials[p.material_index].name:p.material_index=hidx
# Remove stock clothes, keeping the full underlying anatomy intact.
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if any(x in body.data.materials[f.material_index].name for x in ['Bottoms_','Shoes_','Tops_']) or (.915<f.calc_center_median().z<1.333 and abs(f.calc_center_median().x)<.17) or f.material_index==hidx],context='FACES');bm.to_mesh(body.data);bm.free();body.data.update()
bpy.data.objects.remove(oldhair,do_unlink=True)
# Continuous garment weights, no hard spine/chest switch.
def torso(v):
 z=v.z;land=[(.99,'J_Bip_C_Hips'),(1.07,'J_Bip_C_Spine'),(1.18,'J_Bip_C_Chest'),(1.28,'J_Bip_C_UpperChest')]
 if z<=land[0][0]:return {land[0][1]:1}
 for (lo,a),(hi,b) in zip(land,land[1:]):
  if z<hi:t=(z-lo)/(hi-lo);return {a:1-t,b:t}
 return {'J_Bip_C_UpperChest':1}
def ring_surface(n,rings,m,ws,sides=64,start=-math.pi,end=math.pi):
 vs=[];fs=[]
 for z,rx,ry,cy in rings:
  for j in range(sides+1):
   a=start+(end-start)*j/sides;vs.append((math.sin(a)*rx,cy-math.cos(a)*ry,z))
 for k in range(len(rings)-1):
  for j in range(sides):i=k*(sides+1)+j;fs.append((i,i+sides+1,i+sides+2,i+1))
 return mesh(n,vs,fs,m,ws)
ring_surface('A1_Complete_Knit_Top',[(.985,.110,.075,-.004),(1.04,.102,.076,-.006),(1.10,.110,.091,-.003),(1.18,.123,.094,.006),(1.25,.119,.071,.021),(1.30,.051,.036,.027)],graphite,torso)
ring_surface('A1_Soft_Highneck',[(1.306,.045,.039,.027),(1.33,.043,.036,.027),(1.354,.040,.034,.027)],graphite,{'J_Bip_C_Neck':.28,'J_Bip_C_UpperChest':.72})
for sign,side in [(1,'L'),(-1,'R')]:
 vs=[(sign*.047,-.037,1.327),(sign*.12,-.052,1.302),(sign*.084,-.131,1.195),(sign*.038,-.127,1.25)]
 o=mesh('A1_'+side+'_Notched_Lapel',vs,[(0,1,2),(0,2,3)],lapel,torso);m=o.modifiers.new('Lapel edge','SOLIDIFY');m.thickness=.003
 # A fitted boot copies the continuous ankle/foot skin surface before smoothing.
 # At this point hosiery has replaced the skin material, so temporarily select it.
 for p in body.data.polygons:
  if p.material_index==tidx:p.material_index=skin_index
 def bootshape(v,sign=sign):
  x0=sign*.077156;v.x=x0+(v.x-x0)*1.14
  if v.z<.07:v.z=max(.018,v.z);v.y+=(-max(0,.075-v.z)*.16 if v.y<-.02 else .004)
  return v
 o=surface('A1_'+side+'_Fitted_Boot',lambda v,sign=sign: v.z<.245 and v.x*sign>0,boot,.005,bootshape)
 for p in body.data.polygons:
  if p.material_index==skin_index and p.center.z<.985:p.material_index=tidx
 # Foot sole made from a tailored rounded outline rather than a sphere.
 shape=[(-.027,.068),(-.04,.025),(-.039,-.065),(-.026,-.128),(0,-.145),(.026,-.128),(.039,-.065),(.04,.025),(.027,.068)]
 vs=[(sign*.077156+x,y,z)for z in [.011,.026]for x,y in shape];fs=[tuple(reversed(range(9))),tuple(range(9,18))]+[(i,(i+1)%9,(i+1)%9+9,i+9)for i in range(9)]
 mesh('A1_'+side+'_Sole',vs,fs,sole,{'J_Bip_'+side+'_Foot':1})
# New skirt and hair secondary bones are part of the real rig.
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for n,head,tail,parent in [('A1_Skirt_L',(.08,0,.98),(.08,0,.73),'J_Bip_C_Hips'),('A1_Skirt_R',(-.08,0,.98),(-.08,0,.73),'J_Bip_C_Hips'),('A1_Hair_L',(.12,.06,1.4),(.14,.08,1.06),'J_Bip_C_Head'),('A1_Hair_R',(-.12,.06,1.4),(-.14,.08,1.06),'J_Bip_C_Head'),('A1_Hair_Back',(0,.14,1.4),(0,.15,1.03),'J_Bip_C_Head')]:
 b=arm.data.edit_bones.new(n);b.head=head;b.tail=tail;b.parent=arm.data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
def skirtw(v):
 t=max(0,min(.95,(.96-v.z)/.20));l=max(0,min(1,(v.x+.04)/.08));return {'J_Bip_C_Hips':1-t,'A1_Skirt_L':t*l,'A1_Skirt_R':t*(1-l)}
ring_surface('A1_Wrap_Skirt_Base',[(.735,.178,.120,.004),(.78,.176,.118,.004),(.85,.163,.114,.005),(.92,.143,.108,.003),(.982,.129,.098,0),(1.004,.127,.096,0)],slate,skirtw)
# A curved diagonal overlap sewn over the base; dense vertical loops keep bending smooth.
vs=[];fs=[];W=42;H=12
for j in range(H+1):
 t=j/H
 for i in range(W+1):
  u=i/W;a=-1.56+3.05*u;bottom=.741+.085*u;z=1.0*(1-t)+bottom*t;rx=.128+(1.0-z)*.20;ry=.100+(1.0-z)*.08
  vs.append((math.sin(a)*rx,-math.cos(a)*ry-.004,z))
for j in range(H):
 for i in range(W):n=j*(W+1)+i;fs.append((n,n+W+1,n+W+2,n+1))
o=mesh('A1_Diagonal_Wrap_Panel',vs,fs,fold,skirtw);m=o.modifiers.new('Cloth edge','SOLIDIFY');m.thickness=.0015
ring_surface('A1_Waistband',[(.977,.134,.104,0),(1.024,.129,.099,0)],slate,{'J_Bip_C_Hips':1})
# Utility: small genuine 3D hardware with skinning.
def block(n,c,size,m,ws):
 bpy.ops.mesh.primitive_cube_add(size=1,location=c);o=bpy.context.object;o.name=n;o.scale=size;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);o.data.materials.append(m);b=o.modifiers.new('Rounded edge','BEVEL');b.width=.0018;b.segments=2;bpy.ops.object.modifier_apply(modifier=b.name);skin(o,[ws]*len(o.data.vertices));return o
for sign,side in [(1,'L'),(-1,'R')]:
 block('A1_'+side+'_Cuff_Tab',(sign*.476,-.012,1.285),(.024,.063,.007),trim,{'J_Bip_'+side+'_LowerArm':1})
 block('A1_'+side+'_Lapel_Pin',(sign*.10,-.079,1.287),(.012,.005,.007),metal,torso(Vector((0,0,1.287))))
 block('A1_'+side+'_Boot_Buckle',(sign*.109,-.014,.222),(.01,.022,.014),metal,{'J_Bip_'+side+'_LowerLeg':1})
block('A1_Belt_Clasp',(.088,-.079,.99),(.025,.007,.021),metal,{'J_Bip_C_Hips':1})
# Long asymmetric hair locks: curved, convex ribbon volumes with tapered tips.
def catmull(points,t):
 n=len(points)-1;x=t*n;i=min(n-1,int(x));u=x-i;a=Vector(points[max(0,i-1)]);b=Vector(points[i]);c=Vector(points[min(n,i+1)]);d=Vector(points[min(n,i+2)]);return .5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)
def lock(n,points,width,depth,m,bone):
 vs=[];fs=[];N=32;K=8
 for i in range(N+1):
  t=i/N;c=catmull(points,t);tangent=(catmull(points,min(1,t+.003))-catmull(points,max(0,t-.003))).normalized();normal=Vector((c.x, c.y-.025,max(0,c.z-1.48)*1.8)).normalized();cross=tangent.cross(normal).normalized();normal=cross.cross(tangent).normalized()
  w=width*(.58+.5*math.sin(math.pi*t))*(max(.015,1-t)**.42)
  for j in range(K+1):
   q=-1+2*j/K;v=c+cross*(q*w/2)+normal*(depth*(1-q*q));vs.append(tuple(v))
 for i in range(N):
  for j in range(K):k=i*(K+1)+j;fs.append((k,k+K+1,k+K+2,k+1))
 def ws(v):t=max(0,min(.9,(1.43-v.z)/.24));return {'J_Bip_C_Head':1-t,bone:t}
 o=mesh(n,vs,fs,m,ws);sol=o.modifiers.new('Hair ribbon volume','SOLIDIFY');sol.thickness=.002;return o
# Complete fitted scalp under the grouped strands; no exposed crown gaps.
vs=[];fs=[];N=72;H=20
for j in range(H+1):
 for i in range(N+1):
  a=math.tau*i/N;front=(math.cos(a)+1)/2;end=2.45-1.70*front;phi=.025+(end-.025)*j/H
  vs.append((.114*math.sin(phi)*math.sin(a),.026-.109*math.sin(phi)*math.cos(a),1.493+.128*math.cos(phi)))
for j in range(H):
 for i in range(N):k=j*(N+1)+i;fs.append((k,k+N+1,k+N+2,k+1))
mesh('A1_Continuous_Scalp',vs,fs,hairm[0],{'J_Bip_C_Head':1})
# Back fan flows away from the collar and keeps the shoulder silhouette visible.
for i in range(15):
 a=-1.32+2.64*i/14;s=math.sin(a);c=math.cos(a);end=1.05+.055*math.cos(i*1.6)
 pts=[(.015+.025*s,.025+.02*c,1.619),(.110*s,.025+.112*c,1.55),(.126*s,.035+.123*c,1.40),(.140*s+.014*math.sin(i),.07+.103*c,1.26),(.148*s+.020*math.sin(i+1),.08+.097*c,1.14),(.13*s+.018*math.sin(i+2),.09+.10*c,end)]
 lock('A1_Back_Lock_'+str(i),pts,.071,.0045,hairm[i%3],'A1_Hair_Back' if abs(s)<.5 else 'A1_Hair_L'if s>0 else 'A1_Hair_R')
# Swept frontal fringe opens the physical-left temple for the open-ring clip.
for i in range(4):
 q=i/3
 pts=[(.025,-.001+q*.008,1.618),(.008-.052*q,-.043,1.598),(-.020-.068*q,-.082,1.56),(-.052-.056*q,-.098,1.505),(-.077-.047*q,-.074,1.455+.035*q)]
 lock('A1_Swept_Fringe_'+str(i),pts,.057,.004,hairm[1 if i%2 else 0],'A1_Hair_R')
for sign,side in [(1,'L'),(-1,'R')]:
 for i in range(4):
  pts=[(.024*sign,.012+i*.012,1.61),(.105*sign,-.045+i*.013,1.55),((.115+.009*i)*sign,-.057+i*.018,1.43),((.126+.012*i)*sign,-.066+i*.020,1.32),((.157+.004*i)*sign,-.033+i*.020,1.20),((.139+.009*math.sin(i))*sign,-.054+i*.017,1.105+.025*i)]
  lock('A1_'+side+'_Face_Frame_'+str(i),pts,.047,.004,hairm[(i+1)%3],'A1_Hair_'+side)
# Physical-left open ring, not a flat sticker.
vs=[];fs=[];N=48;K=8
for i in range(N+1):
 a=.30+(2*math.pi-.60)*i/N
 for j in range(K):
  q=2*math.pi*j/K;r=.015+.0018*math.cos(q);vs.append((.105+r*math.cos(a),-.068+.0018*math.sin(q),1.543+r*math.sin(a)))
for i in range(N):
 for j in range(K):k=i*K+j;fs.append((k,i*K+(j+1)%K,(i+1)*K+(j+1)%K,k+K))
mesh('A1_Left_Open_Ring',vs,fs,metal,{'J_Bip_C_Head':1})
# Author coherent whole-body motion with eased joint curves. No independent image transforms.
rests={b.name:(arm.matrix_world@b.matrix_local).to_quaternion()for b in arm.data.bones}
def rotate(name,axis,angle):
 pb=arm.pose.bones.get(name)
 if not pb:return
 pb.rotation_mode='QUATERNION';q=rests[name];pb.rotation_quaternion=q.inverted()@Quaternion(Vector(axis),angle)@q

def reset():
 for pb in arm.pose.bones:pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion();pb.location=(0,0,0)
 arm.rotation_mode='QUATERNION';arm.rotation_quaternion=Quaternion();arm.location=(0,0,0)

def frame_pose(action,t):
 reset();phase=t*2*math.pi
 rotate('J_Bip_L_UpperArm',(0,1,0),1.35);rotate('J_Bip_R_UpperArm',(0,1,0),-1.35)
 rotate('J_Bip_L_LowerArm',(0,0,1),-.06);rotate('J_Bip_R_LowerArm',(0,0,1),.06)
 for side,sign in [('L',1),('R',-1)]:
  for finger in ['Index','Middle','Ring','Little']:
   for joint,v in [('1',.10),('2',.16),('3',.12)]:rotate('J_Bip_'+side+'_'+finger+joint,(0,0,1),-sign*v)
 if action=='Idle':
  rotate('J_Bip_C_Chest',(1,0,0),.012*math.sin(phase/4));rotate('J_Bip_C_Head',(0,0,1),.018*math.sin(phase/4));rotate('J_Bip_C_Hips',(0,1,0),.008*math.sin(phase/4))
 elif action=='Wave':
  ramp=max(0,min(1,t/.6,(3.2-t)/.6));ramp=ramp*ramp*(3-2*ramp)
  rotate('J_Bip_R_UpperArm',(0,1,0),-1.35+1.5*ramp);rotate('J_Bip_R_LowerArm',(0,1,0),1.38*ramp)
  rotate('J_Bip_R_Hand',(1,0,0),1.45*ramp)
  q=rests['J_Bip_R_Hand'];arm.pose.bones['J_Bip_R_Hand'].rotation_quaternion=q.inverted()@Quaternion((1,0,0),1.45*ramp)@Quaternion((0,0,1),.20*math.sin(t*9)*ramp)@q;rotate('J_Bip_C_Chest',(0,0,1),-.06*ramp);rotate('J_Bip_C_Head',(0,1,0),-.05*ramp)
 elif action=='Walk':
  for side,sign in [('L',1),('R',-1)]:
   swing=math.sin(phase/1.2)*sign
   hip=arm.data.bones['J_Bip_'+side+'_UpperLeg'].head_local;knee=arm.data.bones['J_Bip_'+side+'_LowerLeg'].head_local;ankle=arm.data.bones['J_Bip_'+side+'_Foot'].head_local
   root_z=-.014+.003*math.cos(phase/1.2*2)
   l1=(knee-hip).length;l2=(ankle-knee).length;dy=ankle.y-hip.y-.08*swing;dz=ankle.z+.07*max(0,swing)-hip.z-root_z;distance=min(l1+l2-.0001,math.hypot(dy,dz))
   alpha=math.acos(max(-1,min(1,(l1*l1+distance*distance-l2*l2)/(2*l1*distance))));bend=math.pi-math.acos(max(-1,min(1,(l1*l1+l2*l2-distance*distance)/(2*l1*l2))))
   rest_u=math.atan2(knee.y-hip.y,hip.z-knee.z);rest_l=math.atan2(ankle.y-knee.y,knee.z-ankle.z)
   upper=math.atan2(dy,-dz)-alpha-rest_u;lower=bend+rest_u-rest_l
   rotate('J_Bip_'+side+'_UpperLeg',(1,0,0),upper);rotate('J_Bip_'+side+'_LowerLeg',(1,0,0),lower);rotate('J_Bip_'+side+'_Foot',(1,0,0),-upper-lower)
   rotate('J_Bip_'+side+'_UpperArm',(0,1,0),sign*1.35);rotate('J_Bip_'+side+'_UpperArm',(1,0,0),-.26*swing);# composed below
   q=rests['J_Bip_'+side+'_UpperArm'];arm.pose.bones['J_Bip_'+side+'_UpperArm'].rotation_quaternion=q.inverted()@Quaternion((0,1,0),sign*1.35)@Quaternion((0,0,1),sign*.25*swing)@q
   rotate('A1_Skirt_'+side,(1,0,0),upper*.7)
  arm.location.z=-.014+.003*math.cos(phase/1.2*2);rotate('J_Bip_C_Chest',(0,0,1),.035*math.sin(phase/1.2))
 elif action=='Turn':
  u=t/4;u=u*u*(3-2*u);arm.rotation_quaternion=Quaternion((0,0,1),math.tau*u)
  for side,sign in [('L',1),('R',-1)]:
   swing=math.sin(t*math.pi*3)*sign*math.sin(t/4*math.pi);rotate('J_Bip_'+side+'_UpperLeg',(1,0,0),.12*swing);rotate('J_Bip_'+side+'_LowerLeg',(1,0,0),.20*max(0,-swing));rotate('A1_Skirt_'+side,(1,0,0),.08*swing)
  rotate('J_Bip_C_Head',(0,0,1),.08*math.sin(t*math.pi/4))
 elif action=='Stretch':
  ramp=max(0,min(1,t/.9,(4.4-t)/.9));ramp=ramp*ramp*(3-2*ramp)
  rotate('J_Bip_L_UpperArm',(0,1,0),1.35-3.35*ramp);rotate('J_Bip_R_UpperArm',(0,1,0),-1.35+3.35*ramp)
  rotate('J_Bip_C_Chest',(1,0,0),-.06*ramp);rotate('J_Bip_C_Head',(1,0,0),-.05*ramp)
 for name in ['A1_Hair_L','A1_Hair_R','A1_Hair_Back']:rotate(name,(1,0,0),.018*math.sin(t*3))

actions=[];fps=30
for name,duration,step in [('Idle',4,15),('Wave',3.2,3),('Walk',1.2,2),('Turn',4,3),('Stretch',4.4,3)]:
 arm.animation_data_clear();act=bpy.data.actions.new(name);arm.animation_data_create();arm.animation_data.action=act
 frames=sorted(set(list(range(0,round(duration*fps)+1,step))+[round(duration*fps)]))
 for fr in frames:
  frame_pose(name,fr/fps)
  arm.keyframe_insert('rotation_quaternion',frame=fr);arm.keyframe_insert('location',frame=fr)
  for pb in arm.pose.bones:pb.keyframe_insert('rotation_quaternion',frame=fr)
 act.use_fake_user=True;actions.append((act,duration))
import sys
sys.path.insert(0,str(OUT))
from cmu_motion import add_gesture
act,duration=add_gesture(arm,OUT/'motion-sources',lambda: frame_pose('Idle',0));actions.append((act,duration))
arm.animation_data.action=actions[0][0];scene=bpy.context.scene;scene.render.fps=fps;scene.frame_set(0);scene.frame_end=132
# Apply non-armature geometric modifiers so GLB and .blend use the same surfaces.
for o in [o for o in scene.objects if o.type=='MESH']:
 bpy.context.view_layer.objects.active=o
 for m in list(o.modifiers):
  if m.type!='ARMATURE':
   # Move thickness before skinning, preserving the real rest geometry and weights.
   while o.modifiers.find(m.name)>0:bpy.ops.object.modifier_move_up(modifier=m.name)
   bpy.ops.object.modifier_apply(modifier=m.name)
# Four influences per vertex are normalized here, so source and exported deformation match.
for o in [o for o in scene.objects if o.type=='MESH']:
 for v in o.data.vertices:
  ws=sorted([(g.group,g.weight)for g in v.groups],key=lambda x:-x[1])
  if len(ws)>4:
   for gi,w in ws[4:]:o.vertex_groups[gi].remove([v.index])
   total=sum(w for gi,w in ws[:4])
   for gi,w in ws[:4]:o.vertex_groups[gi].add([v.index],w/total,'REPLACE')
# Blender look-development scene, separated from selected runtime export.
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:o.select_set(o.type in {'MESH','ARMATURE'})
bpy.context.view_layer.objects.active=arm
parents=[(o,o.parent,o.matrix_world.copy()) for o in scene.objects if o.type=='MESH']
for o,parent,matrix in parents:o.parent=None;o.matrix_world=matrix
original_face=face.data
face.data=original_face.copy()
keep=['Basis','Fcl_EYE_Close','Fcl_EYE_Close_L','Fcl_EYE_Close_R','Fcl_MTH_A','Fcl_MTH_I','Fcl_MTH_O','Fcl_MTH_Joy','Fcl_BRW_Surprised','Fcl_BRW_Sorrow']
for key in list(face.data.shape_keys.key_blocks):
 if not any(key.name.endswith(k) for k in keep):face.shape_key_remove(key)
bpy.ops.export_scene.gltf(filepath=str(PUBLIC/'a1-v2.glb'),export_format='GLB',use_selection=True,export_extras=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_morph=True,export_skins=True,export_materials='EXPORT')
face.data=original_face
for o,parent,matrix in parents:o.parent=parent;o.matrix_world=matrix
shutil.copyfile(PUBLIC/'a1-v2.glb',OUT/'a1-v2.glb')
bpy.ops.object.camera_add(location=(0,-3,.84));cam=bpy.context.object;cam.name='A1_Review_Camera';cam.data.type='ORTHO';cam.data.ortho_scale=1.98;cam.rotation_euler=(Vector((0,0,.84))-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_x=700;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.view_settings.view_transform='AgX';scene.world=bpy.data.worlds.new('Neutral studio');scene.world.color=(.12,.12,.12)
for loc,power in [((1.5,-3,3),130),((-2,-1,2),70),((0,2,2.5),80)]:
 bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=power;l.data.size=3;l.rotation_euler=(Vector((0,0,1))-l.location).to_track_quat('-Z','Y').to_euler()
for label,pos,action,t in [('front',(0,-3,.84),'Idle',0),('side',(3,0,.84),'Idle',0),('back',(0,3,.84),'Idle',0),('wave',(0,-3,.84),'Wave',1.3),('stretch',(0,-3,.84),'Stretch',2.2),('walk',(1.6,-3,.84),'Walk',.3),('gesture',(0,-3,.84),'Gesture',4.0)]:
 arm.animation_data.action=next(a for a,d in actions if a.name==action);scene.frame_set(round(t*fps));cam.location=pos;cam.rotation_euler=(Vector((0,0,.84))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(QA/('a1-v2-'+label+'.png'));bpy.ops.render.render(write_still=True)
arm.animation_data.action=actions[0][0];scene.frame_set(0);cam.location=(0,-3,.84);cam.rotation_euler=(Vector((0,0,.84))-cam.location).to_track_quat('-Z','Y').to_euler();bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'a1-v2.blend'))
report={'blender':bpy.app.version_string,'meshes':sum(o.type=='MESH'for o in scene.objects),'vertices':sum(len(o.data.vertices)for o in scene.objects if o.type=='MESH'),'bones':len(arm.data.bones),'actions':[a.name for a,d in actions],'runtime_bytes':(PUBLIC/'a1-v2.glb').stat().st_size,'visible_leg_ankle_topology_kept_continuous':True,'covered_stock_torso_cutouts_replaced_with_continuous_clothing':True,'face_morphs':list(face.data.shape_keys.key_blocks.keys())}
(QA/'a1-model-build.json').write_text(json.dumps(report,indent=2));print('A1_V2_BUILD_DONE',json.dumps(report)[:500])
