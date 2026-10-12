"""Reproducible A1 engineering model. Licensed pixiv anatomy/rig; new garments and details.

Run with Blender in a separate background process. Never edits the bundled source VRM.
"""
import bpy, bmesh, json, math, shutil, tempfile
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
QA = ROOT / 'output/qa/2026-10-12-a1-page-companion'
SOURCE = ROOT / 'desk-companion/frontend/public/avatars/pixiv-sample.vrm'
bpy.ops.wm.read_factory_settings(use_empty=True)
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'licensed-base.glb'
    shutil.copyfile(SOURCE, path)
    bpy.ops.import_scene.gltf(filepath=str(path))
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
for o in list(bpy.context.scene.objects):
    if o.type not in {'MESH','ARMATURE','EMPTY'} or o.name == 'Icosphere':
        bpy.data.objects.remove(o, do_unlink=True)
arm.name = 'A1_Rig'
arm['sourceAuthor'] = 'pixiv Inc. (anatomy, face and base rig); FYP AI-assisted garment adaptation'
arm['sourceSHA256'] = '12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2'
arm['sourceLicense'] = 'VRM Public License 1.0 with original embedded modification/redistribution permissions'
arm['sourceURL'] = 'https://github.com/pixiv/three-vrm/tree/ff42fae4fcee1fcbca2cd262c7f5f8cbddeaf5ab/packages/three-vrm/examples/models'
arm['assetStatus'] = 'A1 engineering derivative, not final character art approval'

def linear(hex_color):
    rgb = [int(hex_color[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb)

def material(name, color, roughness=.9, metallic=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*linear(color),1)
    p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=roughness
    m.diffuse_color=(*linear(color),1)
    return m

ivory=material('A1_Ivory_Jacket','e4e0d8')
lapel=material('A1_Lapel','f0ece4')
graphite=material('A1_Graphite_Knit','333742')
slate=material('A1_Slate_Wrap','64798f')
wrap=material('A1_Wrap_Fold','7c8fa2')
tights=material('A1_Matte_Tights','57565e')
boot=material('A1_Graphite_Boots','363d49',.76)
sole=material('A1_Boot_Sole','222832')
metal=material('A1_Brushed_Metal','a3adb7',.45,.45)
trim=material('A1_Seam_Trim','68727e')
iris=material('A1_Grey_Blue_Iris','7999ab')
pupil=material('A1_Pupil','172c3b')
silver=material('A1_Silver_Hair','adb1c1')
brow=material('A1_Gray_Brows','626779')

# Colour is changed through 3D material nodes; source texture pixels remain untouched.
for m in bpy.data.materials:
    if not m.use_nodes: continue
    p=m.node_tree.nodes.get('Principled BSDF')
    if not p: continue
    p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=.9
    color=None
    if 'HAIR' in m.name: color='adb1c1'
    if 'FaceBrow' in m.name: color='626779'
    if 'EyeIris' in m.name: color='7999ab'
    if color:
        for link in list(p.inputs['Base Color'].links):m.node_tree.links.remove(link)
        p.inputs['Base Color'].default_value=(*linear(color),1)
        m.diffuse_color=(*linear(color),1)

body=bpy.data.objects['Body']
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    for i,m in enumerate(obj.data.materials):
        if 'HAIR' in m.name:obj.data.materials[i]=silver
        elif 'EyeIris' in m.name:obj.data.materials[i]=iris
        elif 'FaceBrow' in m.name:obj.data.materials[i]=brow
    # VRM constraint helpers are not portable glTF constraints. Collapse their skin weights
    # onto the corresponding real joints before export, so the rig works independently.
    mapping={}
    for side in ['L','R']:
        for old,new in [('J_Aim_'+side+'_Shoulder','UpperArm'),('J_Roll_'+side+'_UpperArm','UpperArm'),('J_Aim_'+side+'_TopsUpperArm','UpperArm'),('J_Roll_'+side+'_Hand','Hand'),('J_Roll_'+side+'_LowerArm','LowerArm'),('J_Roll_'+side+'_Elbow','LowerArm'),('J_Aim_'+side+'_UpperLeg','UpperLeg')]:
            mapping[old]='J_Bip_'+side+'_'+new
    names={g.index:g.name for g in obj.vertex_groups}
    changes=[]
    for v in obj.data.vertices:
        sums={}
        for group in v.groups:
            name=mapping.get(names[group.group],names[group.group])
            sums[name]=sums.get(name,0)+group.weight
        changes.append(sums)
    for old in mapping:
        group=obj.vertex_groups.get(old)
        if group:obj.vertex_groups.remove(group)
    for i,sums in enumerate(changes):
        for name,value in sums.items():
            group=obj.vertex_groups.get(name)or obj.vertex_groups.new(name=name)
            group.add([i],value,'REPLACE')
remove_indices=[i for i,m in enumerate(body.data.materials) if m and any(tag in m.name for tag in ['Bottoms_','Tops_','Shoes_'])]
bm=bmesh.new();bm.from_mesh(body.data)
covered=[]
for f in bm.faces:
    points=[body.matrix_world@v.co for v in f.verts]
    center=sum(points,Vector())/len(points)
    if f.material_index in remove_indices or (.80<center.z<1.335 and abs(center.x)<.505) or center.z<.255:
        covered.append(f)
bmesh.ops.delete(bm,geom=covered,context='FACES_ONLY')
bm.to_mesh(body.data);bm.free();body.data.update()
body.data.materials.append(tights);tight_index=len(body.data.materials)-1
for p in body.data.polygons:
    points=[body.matrix_world@body.data.vertices[i].co for i in p.vertices]
    if max(v.z for v in points)<.815 and max(abs(v.x)for v in points)<.18:
        p.material_index=tight_index

# Retain geometric hair strips; introduce grouped waves below the cheek rather than bending a picture.
hair=bpy.data.objects['Hair']
for v in hair.data.vertices:
    p=hair.matrix_world@v.co
    amount=max(0,min(1,(1.38-p.z)/.30))
    p.x += math.sin((1.38-p.z)*17+(1 if p.x>0 else -1))*.013*amount
    p.y += math.sin((1.38-p.z)*12)*.012*amount
    v.co=hair.matrix_world.inverted()@p

def skin(obj, weights):
    obj.parent=arm;obj.matrix_world=Matrix.Identity(4)
    mod=obj.modifiers.new('A1_Armature','ARMATURE');mod.object=arm
    for index, groups in enumerate(weights):
        total=sum(groups.values())
        for name,value in groups.items():
            if value<=0:continue
            vg=obj.vertex_groups.get(name)or obj.vertex_groups.new(name=name)
            vg.add([index],value/total,'REPLACE')
    return obj

def mesh(name, vertices, faces, mat, weight):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.materials.append(mat);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    for p in data.polygons:p.use_smooth=True
    weights=[weight(Vector(v)) if callable(weight) else weight for v in vertices]
    return skin(obj,weights)

def torso_weights(v):
    if v.z<1.05:return {'J_Bip_C_Hips':max(.1,(1.08-v.z)/.12),'J_Bip_C_Spine':max(.1,(v.z-.96)/.12)}
    if v.z>1.28:return {'J_Bip_C_UpperChest':1}
    return {'J_Bip_C_Chest':1}

def tube(name, rings, mat, weight, start=-math.pi, end=math.pi, sides=48, closed=False):
    vertices=[];faces=[]
    for z,rx,ry,cy in rings:
        for i in range(sides+1):
            a=start+(end-start)*i/sides
            vertices.append((math.sin(a)*rx,cy+math.cos(a)*ry,z))
    for j in range(len(rings)-1):
        for i in range(sides):
            a=j*(sides+1)+i;b=a+sides+1;faces.append((a,a+1,b+1,b))
    if closed:
        faces.append(tuple(reversed(range(sides))))
        faces.append(tuple((len(rings)-1)*(sides+1)+i for i in range(sides)))
    return mesh(name,vertices,faces,mat,weight)

tube('A1_Turtleneck',[(.96,.117,.076,.012),(1.04,.117,.077,.012),(1.14,.133,.093,.010),(1.23,.137,.087,.018),(1.278,.125,.071,.020),(1.305,.044,.040,.014),(1.35,.039,.035,.013)],graphite,torso_weights)
tube('A1_Cropped_Jacket',[(1.025,.139,.095,.014),(1.10,.139,.100,.014),(1.20,.152,.103,.018),(1.285,.147,.084,.020)],ivory,torso_weights,-math.pi+.50,math.pi-.50)
for sign,label in [(1,'L'),(-1,'R')]:
    panel=[(sign*.041,-.060,1.305),(sign*.127,-.069,1.282),(sign*.091,-.110,1.185),(sign*.051,-.111,1.235)]
    mesh('A1_'+label+'_Lapel',panel,[(0,1,2,3)],lapel,torso_weights)
    vertices=[];faces=[];sides=24
    for x,r in [(.125,.064),(.18,.057),(.26,.049),(.31,.044),(.35,.040),(.43,.035),(.50,.032)]:
        for i in range(sides):
            a=2*math.pi*i/sides;vertices.append((sign*x,.025+math.cos(a)*r,1.274+math.sin(a)*r))
    for j in range(6):
        for i in range(sides):
            a=j*sides+i;b=j*sides+(i+1)%sides;faces.append((a,b,b+sides,a+sides))
    def sleeve_weights(v,sign=sign,label=label):
        x=abs(v.x);lower=max(0,min(1,(x-.29)/.075));chest=max(0,min(.95,(.20-x)/.08))
        return {'J_Bip_C_UpperChest':chest,'J_Bip_'+label+'_UpperArm':(1-lower)*(1-chest),'J_Bip_'+label+'_LowerArm':lower*(1-chest)}
    mesh('A1_'+label+'_Jacket_Sleeve',vertices,faces,ivory,sleeve_weights)
    for xa,xb,mat in [(.476,.490,trim),(.493,.505,ivory)]:
        vs=[];fs=[]
        for x in [xa,xb]:
            for i in range(sides):
                a=2*math.pi*i/sides;vs.append((sign*x,.025+math.cos(a)*.034,1.274+math.sin(a)*.034))
        for i in range(sides):fs.append((i,(i+1)%sides,(i+1)%sides+sides,i+sides))
        mesh('A1_'+label+'_Cuff_'+str(xa),vs,fs,mat,sleeve_weights)

tube('A1_Underskirt',[(.746,.159,.102,.012),(.86,.159,.109,.012),(.978,.123,.086,.012)],graphite,{'J_Bip_C_Hips':1})
tube('A1_Wrap_Skirt',[(.775,.166,.109,.012),(.865,.164,.114,.012),(.945,.143,.100,.012),(.991,.126,.090,.012)],slate,{'J_Bip_C_Hips':1})
mesh('A1_Front_Wrap_Fold',[(.116,-.085,.985),(-.118,-.070,.788),(.143,-.045,.778),(.153,-.060,.905)],[(0,1,2,3)],wrap,{'J_Bip_C_Hips':1})
mesh('A1_Wrap_Light_Edge',[(.128,-.070,.975),(.147,-.060,.974),(.160,-.026,.779),(.146,-.045,.779)],[(0,1,2,3)],ivory,{'J_Bip_C_Hips':1})

def primitive_skin(obj,name,mat,groups):
    obj.name=name;obj.data.materials.clear();obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for p in obj.data.polygons:p.use_smooth=True
    skin(obj,[groups.copy()for _ in obj.data.vertices])
    obj.select_set(False)
    return obj

def ellipsoid(name,center,scale,mat,groups):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=center)
    obj=bpy.context.object;obj.scale=scale
    return primitive_skin(obj,name,mat,groups)

def cube(name,center,scale,mat,groups,bevel=.004):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    obj=bpy.context.object;obj.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=obj.modifiers.new('Soft garment edges','BEVEL');mod.width=bevel;mod.segments=2
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return primitive_skin(obj,name,mat,groups)

for sign,label in [(1,'L'),(-1,'R')]:
    foot={'J_Bip_'+label+'_Foot':1};lower={'J_Bip_'+label+'_LowerLeg':1}
    x=sign*.077
    toe=ellipsoid('A1_'+label+'_Boot_Foot',(x,-.028,.060),(.041,.099,.048),boot,foot)
    ellipsoid('A1_'+label+'_Outsole',(x,-.028,.023),(.044,.107,.017),sole,foot)
    heel=cube('A1_'+label+'_Heel',(x,.045,.031),(.055,.046,.057),boot,foot)
    shaft=tube('A1_'+label+'_Boot_Shaft',[(.085,.039,.052,.025),(.125,.036,.045,.025),(.19,.033,.039,.020),(.27,.038,.041,.012)],boot,lower,sides=32,closed=True)
    # The tube generator is centred on the torso; translate this garment's coordinates to its ankle.
    for v in shaft.data.vertices:v.co.x+=x
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [toe,heel,shaft]:
        for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
        obj.select_set(True)
    bpy.context.view_layer.objects.active=toe;bpy.ops.object.join()
    toe.name='A1_'+label+'_Continuous_Boot'
    remesh=toe.modifiers.new('Watertight boot surface','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.003;remesh.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=toe.modifiers.new('Boot surface cleanup','SMOOTH');smooth.factor=.5;smooth.iterations=2
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    decimate=toe.modifiers.new('Web boot budget','DECIMATE');decimate.ratio=.45
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    toe.vertex_groups.clear()
    weights=[]
    for v in toe.data.vertices:
        blend=max(0,min(1,(v.co.z-.105)/.055))
        weights.append({'J_Bip_'+label+'_Foot':1-blend,'J_Bip_'+label+'_LowerLeg':blend})
    skin(toe,weights)
    band=tube('A1_'+label+'_Boot_Cuff',[(.252,.040,.043,.012),(.270,.040,.043,.012)],trim,lower,sides=32)
    for v in band.data.vertices:v.co.x+=x
    cube('A1_'+label+'_Boot_Buckle',(x,-.034,.244),(.025,.005,.014),metal,lower,bevel=.002)
    ellipsoid('A1_'+label+'_Pupil',(sign*.039,-.0605,1.4435),(.0044,.0013,.0080),pupil,{'J_Bip_'+label+'_Eye':1})
    ellipsoid('A1_'+label+'_Ear_Stud',(sign*.105,-.004,1.409),(.004,.003,.004),metal,{'J_Bip_C_Head':1})

# Physical left / viewer right open-ring clip. A true solid C-shaped tube.
vertices=[];faces=[];steps=40;around=8
for i in range(steps+1):
    a=.32+(2*math.pi-.64)*i/steps
    for j in range(around):
        b=2*math.pi*j/around;r=.014+.0022*math.cos(b)
        vertices.append((.103+r*math.cos(a),-.057+.0022*math.sin(b),1.532+r*math.sin(a)))
for i in range(steps):
    for j in range(around):faces.append((i*around+j,i*around+(j+1)%around,(i+1)*around+(j+1)%around,(i+1)*around+j))
mesh('A1_Left_Open_Ring_Clip',vertices,faces,metal,{'J_Bip_C_Head':1})
cube('A1_Waist_Buckle',(.105,-.085,.983),(.027,.007,.022),metal,{'J_Bip_C_Hips':1},bevel=.002)

for obj in bpy.context.scene.objects:
    obj.select_set(obj.type in {'MESH','ARMATURE'})
bpy.context.view_layer.objects.active=arm
bpy.context.view_layer.update()
GLB=OUT/'a1-engineering-v1.glb'
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_extras=True,export_animations=False,export_morph=True,export_skins=True,export_materials='EXPORT')
shutil.copyfile(GLB,ROOT/'desk-companion/frontend/public/companion/a1-engineering-v1.glb')

# Posed inspection renders are made only after the neutral bind asset is exported.
for label,angle in [('L',1.28),('R',-1.28)]:
    pb=arm.pose.bones['J_Bip_'+label+'_UpperArm']
    world=(arm.matrix_world@pb.bone.matrix_local).to_quaternion()
    pb.rotation_mode='QUATERNION';pb.rotation_quaternion=world.inverted()@Quaternion(Vector((0,1,0)),angle)@world
bpy.context.view_layer.update()
bpy.ops.object.camera_add(location=(0,-3.5,.82));cam=bpy.context.object;cam.name='A1_Review_Camera'
cam.data.type='ORTHO';cam.data.ortho_scale=1.78
cam.rotation_euler=(Vector((0,0,.82))-cam.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene;scene.camera=cam
for location,energy,size in [((2,-3,3),300,3),((-2,-1,2),160,2),((0,2,2),230,2)]:
    bpy.ops.object.light_add(type='AREA',location=location)
    light=bpy.context.object;light.data.energy=energy;light.data.shape='DISK';light.data.size=size
    light.rotation_euler=(Vector((0,0,.9))-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=768;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.view_settings.view_transform='Standard'
if not scene.world:scene.world=bpy.data.worlds.new('A1_Review_World')
scene.world.color=(.4,.4,.4)
for name,location in [('front',(0,-3.5,.82)),('three-quarter',(2.0,-3.0,.82)),('back',(0,3.5,.82))]:
    cam.location=location;cam.rotation_euler=(Vector((0,0,.82))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(QA/('a1-3d-'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'a1-engineering-v1.blend'))
report={'source':str(SOURCE.relative_to(ROOT)),'blender':bpy.app.version_string,'glb_bytes':GLB.stat().st_size,'meshes':sum(o.type=='MESH'for o in scene.objects),'bones':len(arm.data.bones),'morph_keys':{o.name:list(o.data.shape_keys.key_blocks.keys())for o in scene.objects if o.type=='MESH'and o.data.shape_keys},'status':'Engineering derivative, pending A1 visual refinement; real skinned geometry, no image-plane deformation'}
(QA/'a1-3d-build.json').write_text(json.dumps(report,indent=2))
