import bpy,json,tempfile,shutil
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path('/Users/tantalum/Documents/ChatGPT/FYP')
QA=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'base.glb';shutil.copyfile(ROOT/'desk-companion/frontend/public/avatars/pixiv-sample.vrm',p);bpy.ops.import_scene.gltf(filepath=str(p))
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
report={'objects':[],'bones':{b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None} for b in arm.data.bones}}
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 report['objects'].append({'name':o.name,'verts':len(o.data.vertices),'bounds':[[min((o.matrix_world@v.co)[i] for v in o.data.vertices),max((o.matrix_world@v.co)[i] for v in o.data.vertices)] for i in range(3)],'matrix':[list(x) for x in o.matrix_world],'materials':[m.name for m in o.data.materials],'polygons_by_material':{m.name:sum(1 for p in o.data.polygons if p.material_index==i) for i,m in enumerate(o.data.materials)},'keys':list(o.data.shape_keys.key_blocks.keys()) if o.data.shape_keys else [],'modifiers':[m.type for m in o.modifiers]})
(QA/'base-geometry.json').write_text(json.dumps(report,indent=2))
for label,angle in [('L',1.28),('R',-1.28)]:
 pb=arm.pose.bones['J_Bip_'+label+'_UpperArm'];w=(arm.matrix_world@pb.bone.matrix_local).to_quaternion();pb.rotation_mode='QUATERNION';pb.rotation_quaternion=w.inverted()@Quaternion(Vector((0,1,0)),angle)@w
bpy.context.view_layer.update()
for o in list(bpy.context.scene.objects):
 if o.type not in ['MESH','ARMATURE','EMPTY'] or o.name=='Icosphere':bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.object.camera_add(location=(0,-3,.84));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.72;cam.rotation_euler=(Vector((0,0,.84))-cam.location).to_track_quat('-Z','Y').to_euler()
s=bpy.context.scene;s.camera=cam;s.render.engine='CYCLES';s.cycles.samples=16;s.render.resolution_x=600;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.film_transparent=True;s.view_settings.view_transform='AgX'
for loc,power in [((1.5,-3,3),150),((-2,-1,2),70)]:
 bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=power;l.data.size=3;l.rotation_euler=(Vector((0,0,.9))-l.location).to_track_quat('-Z','Y').to_euler()
s.world=bpy.data.worlds.new('Review');s.world.color=(.15,.15,.15)
s.render.filepath=str(QA/'base-front.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(QA/'base-inspected.blend'))
print('BASE_INSPECTION_DONE')
