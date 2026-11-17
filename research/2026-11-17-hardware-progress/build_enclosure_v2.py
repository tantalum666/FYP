"""Run with Blender --background --python; dimensions are millimetres."""
import bpy, bmesh, math, json, sys
from mathutils import Vector, Matrix
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'enclosure_320mm_v2'
ROOT.mkdir(exist_ok=True)
W,D,H,T=320,200,200,3
MID=W/2
XL,XR,OPEN_Z,BAY_D=MID-75,MID+75,100,160
Z0=108
TH=math.radians(45)
SS,CC=math.sin(TH),math.cos(TH)
YTOP=(H-Z0)*math.tan(TH)
STOP=(H-Z0)/CC
SCREEN=(MID-78.5,MID+78.5,25,116)
SCREEN_KEEP=(MID-92.5,MID+92.5,5.5,135.5,10.5,14.5)
ARM_WIRE=(80,173,198.5)
COIL_Z=49
RX_FACE_Y,TX_FACE_Y=154,158
RX_W,RX_H,RX_D=86,54,6
TX_W,TX_H,TX_D=56,56,6
X=(1,0,0); Y=(0,1,0); Z=(0,0,1)
S=(0,SS,CC); N=(0,CC,-SS)
S0=(0,0,Z0)

def V(a): return Vector(a)
def minus(a): return -V(a)
def add(origin,*terms):
    point=V(origin)
    for axis,d in terms: point+=V(axis)*d
    return point

def mat(name,c):
    m=bpy.data.materials.new(name); m.diffuse_color=(*c,1)
    return m

def new_col(title):
    col=bpy.data.collections.new(title)
    bpy.context.scene.collection.children.link(col)
    return col

def start(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.name=name
    scene.unit_settings.system='METRIC'
    scene.unit_settings.length_unit='MILLIMETERS'
    scene.unit_settings.scale_length=0.001
    return scene, {x:mat(x,c) for x,c in {
        'Ivory shell':(.86,.89,.88), 'Shell joint':(.65,.76,.75),
        'Slate screen preview':(.025,.105,.148), 'Touch display rim':(.12,.28,.31),
        'Dock clearance':(.16,.52,.59), 'Fasteners under cover':(.16,.45,.46),
        'Q charging preview':(.17,.26,.27), 'Arm footprint preview':(.34,.40,.43),
        'Air and Pi clearance':(.39,.69,.35), 'DC inlet blank':(.38,.55,.58),
        'Mini RX copper':(.92,.42,.12), 'Dock TX copper':(.15,.77,.63),
        'Cable clearance':(.75,.71,.35),
    }.items()}

def poly(name,outline,o,axis_a,axis_b,axis_c,h0,h1,col,m=None):
    n=len(outline)
    verts=[add(o,(axis_a,a),(axis_b,b),(axis_c,h)) for h in (h0,h1) for a,b in outline]
    faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces)
    bm=bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free(); mesh.update()
    obj=bpy.data.objects.new(name,mesh); col.objects.link(obj)
    if m: obj.data.materials.append(m); obj.color=m.diffuse_color
    return obj

def box(name,b,col,m=None,o=(0,0,0),a=X,baxis=Y,c=Z):
    x0,x1,y0,y1,z0,z1=b
    return poly(name,[(x0,y0),(x1,y0),(x1,y1),(x0,y1)],o,a,baxis,c,z0,z1,col,m)

def cutter_box(b,o=(0,0,0),a=X,baxis=Y,c=Z):
    return box('Tool',b,tools,o=o,a=a,baxis=baxis,c=c)

def cyl(center,axis,r,depth,col,name='Tool',m=None):
    a=V(axis).normalized()
    u=a.cross(V(Z if abs(a.z)<0.8 else X)).normalized()
    v=a.cross(u).normalized()
    return poly(name,[(r*math.cos(i*math.tau/24),r*math.sin(i*math.tau/24)) for i in range(24)],
                center,u,v,a,-depth/2,depth/2,col,m)

def cut(obj,shape,op='DIFFERENCE'):
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Machined feature','BOOLEAN'); mod.operation=op; mod.solver='EXACT'; mod.object=shape
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(shape,do_unlink=True)

def slant_cut(b):
    return cutter_box(b,S0,X,S,N)

def vent_cut(obj,where):
    for zz in (123,131,139,147,155):
        b=(W-4,W+1,68,132,zz,zz+3.4) if where=='side' else (W-72,W-28,196,201,zz,zz+3.4)
        cut(obj,cutter_box(b))

def puzzle_bracket(name,o,t,u,v,a,b,col,mat):
    # Leg A lies on panel A and is normal to v; leg B lies on B, normal to u.
    bracket=poly(name,[(0,0),(14,0),(14,3),(3,3),(3,14),(0,14)],o,u,v,t,-9,9,col,mat)
    for p,d,face in [(add(o,(u,8.5)),v,a),(add(o,(v,8.5)),u,b)]:
        cut(face,cyl(p,d,1.7,12,tools)); cut(bracket,cyl(p,d,1.7,12,tools))
    bracket['Fasteners']='2× M3 clearance Ø3.4; use matched M3 bolts, washers and nuts'
    return bracket

def splice(name,o,u,t,n,a,b,col,mat):
    splice_part=box(name,(-18,18,-7,7,0,3),col,mat,o,u,t,n)
    for j,pl in ((-10,a),(10,b)):
        p=add(o,(u,j))
        cut(pl,cyl(p,n,1.7,12,tools));cut(splice_part,cyl(p,n,1.7,12,tools))
    splice_part['Fasteners']='2× M3 clearance Ø3.4'
    return splice_part

def side_shape(z0,z1):
    f=lambda z:max(0,(z-Z0)*math.tan(TH))
    out=[(f(z0),z0),(D,z0),(D,z1),(f(z1),z1)]
    if z0<Z0<z1: out.append((0,Z0))
    return out

def dimension_bounds(objs):
    pts=[o.matrix_world@v.co for o in objs for v in o.data.vertices]
    return [[round(min(v[i] for v in pts),3) for i in range(3)],
            [round(max(v[i] for v in pts),3) for i in range(3)]]

def validate_mesh(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    ok=bool(bm.faces) and all(e.is_manifold for e in bm.edges) and abs(bm.calc_volume())>1e-2
    bm.free()
    if not ok: raise ValueError('Non-solid part '+o.name)

def validate_reservations(structure,connectors,carrier,modular):
    def hit(objects,origin,axis,distance):
        return any(o.ray_cast(V(origin),V(axis),distance=distance)[0] for o in objects)

    deck=structure if not modular else [o for o in structure if o.name=='Top L']
    assert not hit(deck,(ARM_WIRE[0],ARM_WIRE[1],205),minus(Z),10)
    assert hit(deck,(ARM_WIRE[0]+12,ARM_WIRE[1],205),minus(Z),10)

    def front_hit(x,s):
        return hit(structure,add(S0,(X,x),(S,s),(N,-1)),N,8)

    left,right,bottom,top=SCREEN
    for x in (left+.25,right-.25):
        for s in (bottom+.25,top-.25):
            assert not front_hit(x,s)
    for x,s in ((left-.25,50),(right+.25,50),(left+10,bottom-.25),(right-10,top+.25)):
        assert front_hit(x,s)

    # Sample the 110 × 95 mm Mini outline along the approach, including near the desk.
    for x in (MID-54.9,MID,MID+54.9):
        for z in (.1,47.5,94.9):
            assert not hit(structure+connectors+[carrier],(x,-1,z),Y,RX_FACE_Y+1)
    assert hit(structure,(MID-1,-1,OPEN_Z+.25),Y,4)

    aft_splice=next((o for o in connectors if o.name=='Floor seam aft'),None)
    if aft_splice:
        assert dimension_bounds([aft_splice])[0][1]-dimension_bounds([carrier])[1][1]==2
    assert TX_FACE_Y-RX_FACE_Y==4 and OPEN_Z-95==5
    assert RX_W<110 and COIL_Z+RX_H/2<95 and COIL_Z-RX_H/2>0

def setup_view(scene):
    world=bpy.data.worlds.new('Background')
    world.color=(.76,.80,.84); scene.world=world
    scene.render.engine='BLENDER_WORKBENCH'
    shading=scene.display.shading
    shading.light='STUDIO'; shading.studiolight_rotate_z=.18
    shading.color_type='MATERIAL'; shading.show_shadows=True; shading.show_cavity=True
    shading.cavity_type='BOTH'; shading.background_type='WORLD'; shading.show_specular_highlight=True
    scene.view_settings.view_transform='Standard'
    scene.render.resolution_x=1340; scene.render.resolution_y=920
    scene.render.resolution_percentage=100
    cd=bpy.data.cameras.new('Catalog camera')
    camera=bpy.data.objects.new('Catalog camera',cd); scene.collection.objects.link(camera)
    camera.location=(W+170,-550,405)
    camera.rotation_euler=(V((MID,85,97))-camera.location).to_track_quat('-Z','Y').to_euler()
    cd.type='ORTHO'; cd.ortho_scale=540; cd.clip_end=3000
    scene.camera=camera
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type=='VIEW_3D':
                sp=area.spaces.active; sp.clip_end=4000; sp.clip_start=0.1
                sp.region_3d.view_perspective='ORTHO'; sp.region_3d.view_distance=520
                sp.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
                sp.region_3d.view_location=(MID,90,100)
                sp.shading.color_type='MATERIAL'
                sp.overlay.show_floor=False; sp.overlay.show_axis_x=False; sp.overlay.show_axis_y=False
    return camera

def refs(scene,mats):
    c=new_col('03 OCCUPANCY & CLEARANCE — NOT PARTS')
    bx,tx,bs,ts=SCREEN
    ss=box('Touchscreen visible mockup — 157 x 91 draft', (bx-.8,tx+.8,bs-.8,ts+.8,3.25,4),c,mats['Slate screen preview'],S0,X,S,N)
    ss['Fit']='Visible window geometry is provisional. Measure actual display border and PCB.'
    screen_keep=box('Screen PCB and ears — reserve 185 x 130', SCREEN_KEEP,c,mats['Cable clearance'],S0,X,S,N)
    screen_keep.display_type='WIRE'
    screen_keep.hide_render=True
    screen_keep['Fit']='Keep-out envelope, not a final mounting hole pattern. Check module thickness and screen centre.'
    plug_keep=box('Screen HDMI and USB plug space — draft',(200,267,24,102,106,152),c,mats['Cable clearance'])
    plug_keep.display_type='WIRE'
    plug_keep.hide_render=True
    # Nonprinting silhouettes; never treat as fabricated components.
    qi=box('Phone Qi zone 95 x 82 (separate from Mini dock)',(W-123,W-28,101,183,200,201),c,mats['Q charging preview'])
    arm=cyl((80,146,200.75),Z,53,1.5,c,'Luwu base planning envelope Ø106',mats['Arm footprint preview'])
    cut(arm,cyl((ARM_WIRE[0],ARM_WIRE[1],201),Z,11,10,tools))
    arm['Fit']='Top opening is a provisional cable hole. No Luwu bolt pattern has been machined.'
    dock=box('Illustrative assembled Mini 110 x 100 x 95',(MID-55,MID+55,54,RX_FACE_Y-6,0,95),c,mats['Dock clearance'])
    dock['Fit']='Illustrative assembled envelope including rear receiver: 110 W x 100 D x 95 H. Bare body approx 70 mm cube from user.'
    rx=box(f'Mini rear RX keep-out {RX_W} x {RX_H} x {RX_D}',
        (MID-RX_W/2,MID+RX_W/2,RX_FACE_Y-RX_D,RX_FACE_Y,COIL_Z-RX_H/2,COIL_Z+RX_H/2),
        c,mats['Mini RX copper'])
    rx.display_type='WIRE';rx.hide_render=True
    rx_coil=cyl((MID,RX_FACE_Y-1.4,COIL_Z),Y,22,2.0,c,'Mini rear Qi RX — prototype envelope',mats['Mini RX copper'])
    tx=box(f'Dock rear TX keep-out {TX_W} x {TX_H} x {TX_D}',
        (MID-TX_W/2,MID+TX_W/2,TX_FACE_Y,TX_FACE_Y+TX_D,COIL_Z-TX_H/2,COIL_Z+TX_H/2),
        c,mats['Dock TX copper'])
    tx.display_type='WIRE';tx.hide_render=True
    tx_coil=cyl((MID,TX_FACE_Y+1.4,COIL_Z),Y,25,2.0,c,'Dock Qi TX — prototype envelope',mats['Dock TX copper'])
    rx_pcb=box('Mini RX electronics and cable reserve 40 x 25 x 12',(MID-20,MID+20,117,142,23,35),c,mats['Cable clearance'])
    rx_pcb.display_type='WIRE';rx_pcb.hide_render=True
    vent=box('Pi 5 / cooler / cable clearance zone',(W-86,W-7,94,185,108,129),c,mats['Air and Pi clearance'])
    inlet=box('Removable blank, 40 × 23 (no connector cut)',(W-66,W-26,197.5,199.5,44,67),c,mats['DC inlet blank'])
    inlet['Electrical']='Low voltage DC from external adapter. Keep UK AC upstream of adapter.'
    for o in (ss,screen_keep,plug_keep,qi,arm,dock,vent,inlet,rx,rx_coil,rx_pcb,tx,tx_coil):
        o['Prototype']='REFERENCE OBJECT — DO NOT SLICE'
    return c,dock,rx_coil,tx_coil

def dock_bracket(panelL,panelR,col,material):
    # The face of the prototype metal-free carrier is behind the TX stack.
    u=poly('Dock TX removable trial carrier — remeasure coil',
        [(160,3),(177,3),(177,7),(168,7),(168,80),(164,80),(164,7),(160,7)],
        (0,0,0),Y,Z,X,MID-35,MID+35,col,material)
    for x,panel in ((MID-27,panelL),(MID+27,panelR)):
        d=(x,172,3)
        cut(panel,cyl(d,Z,1.7,12,tools))
        cut(u,cyl(d,Z,1.7,12,tools))
    u['Fit']='Prototype rear TX carrier; secure coil and plastic cover after actual stack-up is known. M3 fasteners at the base only.'
    return u

def make_model(modular):
    global tools
    scene,mats=start(f'FYP V2 {W} × {D} × {H} | '+('Panels' if modular else 'One piece'))
    shell=new_col('01 ENCLOSURE PANELS' if modular else '01 ONE-PIECE SHELL')
    fast=new_col('02 M3 CONNECTIONS — prototype') if modular else None
    tools=new_col('_tools')
    dock_parts=new_col('04 DOCK TX CARRIER — prototype')
    m=mats['Ivory shell']; tight=mats['Fasteners under cover']
    structure=[]; connectors=[]
    if not modular:
        body=poly(f'Single piece shell · {W} × {D} × {H}',side_shape(0,H),(0,0,0),Y,Z,X,0,W,shell,m)
        inner=[(3,3),(197,3),(197,197),((197-Z0)*math.tan(TH)+T/CC,197),(3,Z0+(3-T/CC)/math.tan(TH))]
        cut(body,poly('Tool',inner,(0,0,0),Y,Z,X,3,W-3,tools))
        cut(body,cutter_box((XL,XR,-2,BAY_D,-2,OPEN_Z)))
        cut(body,slant_cut((*SCREEN,-2,13)))
        cut(body,cyl(ARM_WIRE,Z,11,12,tools))
        cut(body,cutter_box((W-67,W-25,196,201,43,68)))
        vent_cut(body,'side');vent_cut(body,'rear')
        tx_mount=dock_bracket(body,body,dock_parts,tight)
        structure.append(body)
    else:
        p={}
        for tag,(x0,x1) in {'L':(3,MID-.2),'R':(MID+.2,W-3)}.items():
            p['top'+tag]=box('Top '+tag,(x0,x1,YTOP,197,197,200),shell,m)
            p['rear'+tag]=box('Rear '+tag,(x0,x1,197,200,3,197),shell,m)
            p['bottom'+tag]=box('Bottom '+tag+' with open dock', (x0,x1,0,200,0,3),shell,m)
            cut(p['bottom'+tag],cutter_box((XL,XR,-2,BAY_D,-2,5)))
            p['fLow'+tag]=box('Front lower '+tag,(x0,x1,0,3,3,Z0),shell,m)
            cut(p['fLow'+tag],cutter_box((XL,XR,-2,5,-2,OPEN_Z)))
            # Mitered section ends at the top-cap plane (no overlapping solids).
            outline=[(0,Z0),(YTOP,200),(YTOP,200-T/SS),(T/CC,Z0)]
            p['fUp'+tag]=poly('Sloped display surround '+tag,outline,(0,0,0),Y,Z,X,x0,x1,shell,m)
            cut(p['fUp'+tag],slant_cut((*SCREEN,-2,13)))
        for tag,(x0,x1) in {'L':(0,3),'R':(W-3,W)}.items():
            p['sideLo'+tag]=poly('Side lower '+tag,side_shape(0,99.8),(0,0,0),Y,Z,X,x0,x1,shell,m)
            p['sideHi'+tag]=poly('Side upper '+tag,side_shape(100.2,200),(0,0,0),Y,Z,X,x0,x1,shell,m)
        cut(p['rearR'],cutter_box((W-67,W-25,196,201,43,68)))
        cut(p['topL'],cyl(ARM_WIRE,Z,11,12,tools))
        vent_cut(p['sideHiR'],'side');vent_cut(p['rearR'],'rear')
        tx_mount=dock_bracket(p['bottomL'],p['bottomR'],dock_parts,tight)
        for tag,x,xx in [('L',3,X),('R',W-3,minus(X))]:
            def bracket(label,o,t,u,v,aa,bb):
                connectors.append(puzzle_bracket(tag+' '+label,o,t,u,v,p[aa+tag],p[bb+tag],fast,tight))
            bracket('top corner',(x,149,197),Y,xx,minus(Z),'top','sideHi')
            for y in (39,144):
                bracket('floor corner '+str(y),(x,y,3),Y,xx,Z,'bottom','sideLo')
            bracket('rear corner',(x,197,143),Z,xx,minus(Y),'rear','sideHi')
            bracket('front lower corner',(x,3,51),Z,xx,Y,'fLow','sideLo')
            for s in (32,89):
                bracket('sloped panel '+str(s),add((x,0,Z0),(S,s),(N,T)),S,xx,N,'fUp','sideHi')
            bracket('lower front to floor',(48 if tag=='L' else W-48,3,3),X,Y,Z,'bottom','fLow')
            for y in (45,155):
                connectors.append(splice(tag+' side seam '+str(y),(x,y,100),Z,Y,xx,
                                         p['sideLo'+tag],p['sideHi'+tag],fast,tight))
        for name,o,u,v,n,aa,bb in [
            ('Top seam forward',(MID,115,197),X,Y,minus(Z),'topL','topR'),
            ('Top seam aft',(MID,163,197),X,Y,minus(Z),'topL','topR'),
            ('Rear seam lower',(MID,197,57),X,Z,minus(Y),'rearL','rearR'),
            ('Rear seam upper',(MID,197,143),X,Z,minus(Y),'rearL','rearR'),
            ('Floor seam aft',(MID,186,3),X,Y,Z,'bottomL','bottomR')]:
            connectors.append(splice(name,o,u,v,n,p[aa],p[bb],fast,tight))
        structure=list(p.values())
        # Flat projection sizes from part orientation, not assembled bounding boxes.
        for key,o in p.items():
            if key.startswith('fUp'): footprint=[round(MID-3.2,2),round(STOP,2)]
            else:
                b=dimension_bounds([o])
                footprint=sorted([round(y-x,2) for x,y in zip(*b)],reverse=True)[:2]
            o['Flat print envelope (mm)']=str(footprint)
    all_geom=structure+connectors+[tx_mount]
    bpy.context.view_layer.update()
    for o in all_geom: validate_mesh(o)
    bounds=dimension_bounds(structure)
    if bounds!=[[0,0,0],[W,D,H]]: raise ValueError(bounds)
    assert len(structure)==(14 if modular else 1)
    validate_reservations(structure,connectors,tx_mount,modular)
    reference_collection,dock_proxy,rx_coil,tx_coil=refs(scene,mats)
    for obj in all_geom+list(reference_collection.objects):
        bb=dimension_bounds([obj])
        center=V([(hi+lo)*.5 for lo,hi in zip(*bb)])
        obj.data.transform(Matrix.Translation(-center))
        obj.location=center
    bpy.data.collections.remove(tools)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    cam=setup_view(scene)
    scene['Prototype']='Layout study. Final mounts, clearances and thermal capacity need physical verification.'
    scene['Envelope (mm)']=f'{W} × {D} × {H}; arm excluded'
    scene['Screen reservation (mm)']='Draft 157 x 91 viewing window; rear keep-out 185 x 130 before connectors; face 45° from vertical'
    scene['Dock reservation (mm)']='150 W × 160 D × 100 entry H, floor open to desk; aim assembled Mini H ≤95'
    scene['Mini wireless charge (mm)']=(f'Rear vertical RX {RX_W} × {RX_H} × {RX_D}; '
        f'bay vertical TX {TX_W} × {TX_H} × {TX_D}. Common height {COIL_Z}; mockup surface gap 4; physical verification required.')
    scene['Luwu']='Ø22 trial cable opening through deck. No manufacturer mounting hole pattern.'
    scene['Service opening (mm)']='42 × 25 rear service slot with blank; not the final DC socket cut'
    scene['Print limit']='Panel version largest flat piece ~200 × 157 mm before brim; bed 320 × 320 nominal.'
    bpy.context.scene.cursor.location=(MID,100,0)
    tag='panels' if modular else 'one_piece'
    bpy.context.view_layer.update()
    assert dimension_bounds(structure)==bounds
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(f'FYP_enclosure_{W}x{D}x{H}_V2_{tag}.blend')))
    summary=dict(version=bpy.app.version_string,body_bounds=bounds,
        exterior_meshes=len(structure),connector_meshes=len(connectors),dock_carrier_parts=1,manifold=len(all_geom),
        geometry_checks=['cable hole passes through deck','screen opening and border sample points',
                         'Mini approach sample paths clear through entry','clearance from rear splice when fitted'],
        qi_reservations_mm={'receiver':[RX_W,RX_H,RX_D],'transmitter':[TX_W,TX_H,TX_D],
                            'centre_height':COIL_Z,'draft_face_gap':TX_FACE_Y-RX_FACE_Y},
        exteriors=[{'name':o.name,'bounds':dimension_bounds([o]),'flat_footprint':o.get('Flat print envelope (mm)')} for o in structure])
    (ROOT/(f'{tag}_qa.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print('QA',json.dumps(summary,ensure_ascii=False))
    if 'render' in sys.argv:
        scene.render.filepath=str(ROOT/(f'{tag}_preview.png'))
        bpy.ops.render.render(write_still=True)
        if modular:
            # Highlight the relative charging positions separately from the printed case.
            for o in all_geom+list(reference_collection.objects):
                o.hide_render=o not in [tx_mount,dock_proxy,rx_coil,tx_coil]
            cam.location=(410,130,154)
            cam.rotation_euler=(V((MID,115,47))-cam.location).to_track_quat('-Z','Y').to_euler()
            cam.data.ortho_scale=222
            scene.render.filepath=str(ROOT/'qi_dock_detail.png')
            bpy.ops.render.render(write_still=True)
            for o in all_geom: o.hide_render=False
            cam.location=(W+350,-620,460)
            cam.rotation_euler=(V((MID,92,106))-cam.location).to_track_quat('-Z','Y').to_euler()
            cam.data.ortho_scale=648
            reference_collection.hide_render=True
            for key,o in p.items():
                l=-1 if key.endswith('L') else 1
                if key.startswith('top'): offset=(l*21,15,41)
                elif key.startswith('rear'): offset=(l*24,79,0)
                elif key.startswith('bottom'): offset=(l*20,5,-40)
                elif key.startswith('fUp'): offset=(l*16,-56,15)
                elif key.startswith('fLow'): offset=(l*16,-56,-8)
                elif key.startswith('sideHi'): offset=(l*60,10,17)
                else: offset=(l*60,10,-17)
                o.location+=V(offset)
            scene.render.filepath=str(ROOT/'panels_exploded.png')
            bpy.ops.render.render(write_still=True)

if __name__=='__main__':
    modes=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['one_piece','panels']
    if 'one_piece' in modes: make_model(False)
    if 'panels' in modes: make_model(True)
