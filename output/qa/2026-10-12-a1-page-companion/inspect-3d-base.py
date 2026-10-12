import bpy, json, math, tempfile, shutil
from pathlib import Path
from mathutils import Vector

root = Path('/Users/tantalum/Documents/ChatGPT/FYP')
out = root / 'output/qa/2026-10-12-a1-page-companion'
bpy.ops.wm.read_factory_settings(use_empty=True)
with tempfile.TemporaryDirectory() as folder:
    file = Path(folder) / 'base.glb'
    shutil.copyfile(root / 'desk-companion/frontend/public/avatars/pixiv-sample.vrm', file)
    bpy.ops.import_scene.gltf(filepath=str(file))
data = {'objects': [], 'armatures': []}
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        parts = []
        for i, mat in enumerate(obj.data.materials):
            vertices = {v for p in obj.data.polygons if p.material_index == i for v in p.vertices}
            points = [obj.matrix_world @ obj.data.vertices[v].co for v in vertices]
            parts.append({'material': mat.name, 'faces': sum(p.material_index == i for p in obj.data.polygons), 'min': [min(p[a] for p in points) for a in range(3)], 'max': [max(p[a] for p in points) for a in range(3)]})
        data['objects'].append({'name': obj.name, 'vertices': len(obj.data.vertices), 'parts': parts})
    if obj.type == 'ARMATURE':
        data['armatures'].append({'name': obj.name, 'bones': {b.name: {'head': list(obj.matrix_world @ b.head_local), 'tail': list(obj.matrix_world @ b.tail_local)} for b in obj.data.bones if 'J_Bip' in b.name}})
out.joinpath('base-3d-inspection.json').write_text(json.dumps(data, indent=2))
bpy.ops.object.camera_add(location=(0, -3.5, .85))
cam = bpy.context.object
cam.rotation_euler = (Vector((0, 0, .85)) - cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.9
bpy.context.scene.camera = cam
for location, energy, size in [((2,-3,3), 400, 3), ((-2,-1,2), 180, 2)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    light=bpy.context.object;light.data.energy=energy;light.data.shape='DISK';light.data.size=size
    light.rotation_euler=(Vector((0,0,.9))-light.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.samples=16
scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.view_settings.view_transform='Standard'
scene.render.filepath=str(out/'base-3d-preview.png')
bpy.ops.render.render(write_still=True)
