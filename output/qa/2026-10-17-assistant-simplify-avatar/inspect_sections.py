import bpy,json
from pathlib import Path
q=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(q/'base-inspected.blend'))
b=bpy.data.objects['Body'];out={}
for i,m in enumerate(b.data.materials):
 ids={v for p in b.data.polygons if p.material_index==i for v in p.vertices};vs=[b.data.vertices[j].co for j in ids]
 out[m.name]={'bounds':[[min(v[k] for v in vs),max(v[k] for v in vs)]for k in range(3)],'sections':{str(z):[[round(x,5)for x in v] for v in vs if abs(v.z-z)<.008 and abs(v.x)<.2][:20]for z in [.1,.26,.5,.75,.85,.95,1.05,1.15,1.25,1.31]}}
(q/'base-sections.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
