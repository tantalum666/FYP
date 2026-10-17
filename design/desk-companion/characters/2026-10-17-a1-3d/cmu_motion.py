"""Bounded ASF/AMC retargeting for one CMU motion excerpt, not arbitrary code loading.
Data: CMU Motion Capture Database, subject 14 trial 26, 120 Hz.
Finger/thumb convenience channels are deliberately ignored (not captured by CMU).
"""
import math
from pathlib import Path
from mathutils import Matrix, Vector, Euler, Quaternion
import bpy

def add_gesture(arm, source, reset):
    bones={};hier={};mode='';row=None;inside=False
    for line in (source/'14.asf').read_text().splitlines():
        a=line.split()
        if not a or a[0].startswith('#'):continue
        if a[0].startswith(':'):mode=a[0];continue
        if mode==':bonedata':
            if a[0]=='begin':row={}
            elif a[0]=='end':bones[row['name']]=row
            elif a[0]=='name':row['name']=a[1]
            elif a[0]=='direction':row['direction']=Vector([float(x)for x in a[1:]])
            elif a[0]=='length':row['length']=float(a[1])
            elif a[0]=='axis':row['axis']=Euler([math.radians(float(x))for x in a[1:4]],'XYZ').to_matrix()
            elif a[0]=='dof':row['dof']=a[1:]
        elif mode==':hierarchy':
            if a[0]in ['begin','end']:continue
            hier[a[0]]=a[1:]
    frames=[];row=None
    for line in (source/'14_26.amc').read_text().splitlines():
        a=line.split()
        if not a or a[0].startswith(('#',':')):continue
        if a[0].isdigit():row={};frames.append(row)
        else:row[a[0]]=[float(x)for x in a[1:]]
    convert=Matrix.Rotation(math.pi/2,3,'X');invconvert=convert.inverted()
    def forward(frame):
        root=frame['root'];rot={'root':Euler([math.radians(x)for x in root[3:6]],'XYZ').to_matrix()}
        def descend(parent):
            for n in hier.get(parent,[]):
                b=bones[n];angle={d:v for d,v in zip(b.get('dof',[]),frame.get(n,[]))};m=Euler([math.radians(angle.get(d,0))for d in ['rx','ry','rz']],'XYZ').to_matrix();c=b['axis'];rot[n]=rot[parent]@c@m@c.inverted();descend(n)
        descend('root');return rot
    mapping={'J_Bip_C_Hips':'root','J_Bip_C_Spine':'lowerback','J_Bip_C_Chest':'upperback','J_Bip_C_UpperChest':'thorax','J_Bip_C_Neck':'upperneck','J_Bip_C_Head':'head'}
    for side,c in [('L','l'),('R','r')]:
        mapping.update({'J_Bip_'+side+'_Shoulder':c+'clavicle','J_Bip_'+side+'_UpperArm':c+'humerus','J_Bip_'+side+'_LowerArm':c+'radius','J_Bip_'+side+'_Hand':c+'hand',})
    rest={b.name:b.matrix_local.to_quaternion()for b in arm.data.bones}
    # Source T-pose directions are X for arms; femurs have a calibrated 20-degree stance.
    direction_children={'UpperArm':'LowerArm','LowerArm':'Hand','UpperLeg':'LowerLeg','LowerLeg':'Foot','Foot':'ToeBase'}
    alignment={}
    for name,src in mapping.items():
        if src=='root':alignment[name]=Quaternion();continue
        suffix=name.split('_')[-1];side=name.split('_')[-2];child=arm.data.bones.get('J_Bip_'+side+'_'+direction_children.get(suffix,''))
        if child:
            target=(child.head_local-arm.data.bones[name].head_local).normalized();base=(convert@bones[src]['direction']).normalized();alignment[name]=base.rotation_difference(target)
        else:alignment[name]=Quaternion()
    act=bpy.data.actions.new('Gesture');act.use_fake_user=True;arm.animation_data_create();arm.animation_data.action=act
    start,end=1080,2160;prev={};reference_y=frames[start]['root'][1];scale=.908/max(1,reference_y)
    for i in range(start,end+1,4):
        reset();g=forward(frames[i]);desired={}
        for name,src in mapping.items():
            q=(convert@g[src]@invconvert).to_quaternion();align=alignment[name];desired[name]=align@q@align.inverted()@rest[name]
        for name in mapping:
            b=arm.data.bones[name];parent=b.parent.name if b.parent else None;restlocal=rest[parent].inverted()@rest[name]if parent else rest[name];parentq=desired.get(parent,rest.get(parent,Quaternion()))
            local=restlocal.inverted()@parentq.inverted()@desired[name]
            if name in prev:local=prev[name].slerp(local,.65)
            prev[name]=local.copy();pb=arm.pose.bones[name];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=local
        arm.location=(0,0,0)  # Upper-body excerpt: retain the authored planted stance.
        # Preserve authored modest finger curvature, rather than the uncaptured channels.
        fr=(i-start)//4
        arm.keyframe_insert('location',frame=fr);arm.keyframe_insert('rotation_quaternion',frame=fr)
        for pb in arm.pose.bones:pb.keyframe_insert('rotation_quaternion',frame=fr)
    return act,(end-start)/120
