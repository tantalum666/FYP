"""Image-region boundary alerts and reference-image change candidates.

These functions report visual evidence; they do not certify physical clearance.
"""
import cv2
import numpy as np


def desk_region(normalized, result, layout, width, height):
    if normalized is not None:
        points = np.asarray(normalized, dtype=np.float32)
        if points.shape != (4, 2) or not np.isfinite(points).all() or (points < 0).any() or (points > 1).any():
            raise ValueError('桌面范围需由画面内四个角点组成。')
        points = points * [width, height]
        points = points.astype(np.float32)
        if not cv2.isContourConvex(points) or abs(cv2.contourArea(points)) < width*height*.002:
            raise ValueError('请沿桌面边缘按顺序点选四个角，避免交叉或范围过小。')
        return points, 'manual_image_region'
    if result.get('homography') is not None:
        world = np.float32([[0,0],[layout['table_width_mm'],0],
                            [layout['table_width_mm'],layout['table_depth_mm']],[0,layout['table_depth_mm']]])
        inverse = np.linalg.inv(np.asarray(result['homography'],dtype=np.float64))
        points = cv2.perspectiveTransform(world[None],inverse)[0]
        if np.isfinite(points).all() and cv2.isContourConvex(points):
            return points, 'calibrated_test_area_projection' if layout.get('reference_layout_mode') == 'l_shape' else 'calibrated_table_projection'
    return None, None


def edge_monitor(markers, result, polygon, width, height):
    state = {'edge_status':'NOT_SET','edge_distance_px':None,
             'edge_message':'未设置桌面范围，暂不能判断 ID 4 是否越界。'}
    if polygon is None:
        return state
    targets = [c for i,c in markers if i == 4]
    entry = next((m for m in result['marker_positions'] if m['id']==4),None)
    if len(targets)!=1 or not entry or entry['image_px'] is None:
        state.update(edge_status='TARGET_LOST',edge_message='ID 4 丢失或重复，无法判断是否越界；丢失不等于已离桌。')
        return state
    centre = tuple(map(float,entry['image_px']))
    centre_distance = cv2.pointPolygonTest(polygon,centre,True)
    distances = [cv2.pointPolygonTest(polygon,tuple(map(float,p)),True) for p in targets[0]]
    closest = min(distances)
    state['edge_distance_px'] = round(closest,1)
    margin = max(8., np.hypot(width,height)*.012)
    if centre_distance < 0:
        state.update(edge_status='OUTSIDE',edge_message='越界：ID 4 码中心已超出设定的桌面范围。')
    elif closest < 0:
        state.update(edge_status='CROSSING_EDGE',edge_message='触边：ID 4 的部分码面已越过桌面边界。')
    elif closest < margin:
        state.update(edge_status='NEAR_EDGE',edge_message='接近桌边：ID 4 码面距离设定边界较近。')
    else:
        state.update(edge_status='INSIDE',edge_message='ID 4 码面位于设定桌面范围内。')
    return state


def intersects_region(box, polygon):
    if polygon is None:
        return True
    x1,y1,x2,y2 = box
    rectangle = np.float32([[x1,y1],[x2,y1],[x2,y2],[x1,y2]])
    area,_ = cv2.intersectConvexConvex(rectangle,polygon)
    return area > 1


def change_candidates(image, reference, polygon, markers, known):
    if polygon is None:
        return [],'waiting_boundary','先标出桌面范围，再记录空桌面参考。'
    if reference is None:
        return [],'waiting_reference','已设范围；请清空桌面后点击“记录空桌面”。'
    if image.shape != reference.shape:
        return [],'reference_mismatch','画面尺寸已改变，请重新标范围并记录空桌面。'
    height,width = image.shape[:2]
    roi = np.zeros((height,width),np.uint8)
    # Clipping huge off-frame projections prevents integer overflow in rasterisation.
    safe_polygon = np.clip(polygon,[-width*4,-height*4],[width*5,height*5]).astype(np.int32)
    cv2.fillConvexPoly(roi,safe_polygon,255)
    roi = cv2.erode(roi,np.ones((3,3),np.uint8))
    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50))
    previous_corners, previous_ids, _ = detector.detectMarkers(reference)
    exclusions = [c for _,c in markers]
    if previous_ids is not None:
        exclusions += [c.reshape(4,2) for c in previous_corners]
    for corners in exclusions:
        centre = np.mean(corners,axis=0)
        expanded = ((corners-centre)*1.45+centre).astype(np.int32)
        cv2.fillConvexPoly(roi,expanded,0)
    usable = roi > 0
    if np.count_nonzero(usable) < 50:
        return [],'waiting_boundary','可检测桌面区域太小，请重新标记范围。'
    current = cv2.GaussianBlur(image,(3,3),0).astype(np.int16)
    baseline = cv2.GaussianBlur(reference,(3,3),0).astype(np.int16)
    difference = current-baseline
    light_shift = np.clip(np.median(difference[usable],axis=0),-20,20)
    delta = np.max(np.abs(difference-light_shift),axis=2)
    changed = np.where((delta > 35)&usable,255,0).astype(np.uint8)
    changed_fraction = float(np.count_nonzero(changed)/np.count_nonzero(usable))
    changed = cv2.morphologyEx(changed,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    changed[~usable] = 0
    contours,_ = cv2.findContours(changed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    minimum = max(35.,np.count_nonzero(usable)*.00025)
    contours = sorted([c for c in contours if cv2.contourArea(c)>=minimum],key=cv2.contourArea,reverse=True)
    result = []
    for contour in contours[:60]:
        x,y,w,h = cv2.boundingRect(contour)
        covered = False
        for obj in known:
            x1,y1,x2,y2 = obj['box_px']
            overlap = max(0,min(x+w,x2)-max(x,x1))*max(0,min(y+h,y2)-max(y,y1))
            if overlap/(w*h) > .65:
                covered = True
                break
        if covered:
            continue
        result.append({'class_id':None,'name':'unknown_obstacle','label':'未知障碍／疑似变化',
                       'confidence':None,'source':'background_difference',
                       'box_px':[float(x),float(y),float(x+w),float(y+h)],
                       'changed_area_px':round(cv2.contourArea(contour),1),'table_polygon_mm':None})
    if changed_fraction > .55 or len(contours)>60:
        return result,'scene_changed','画面变化较大或区域过多；请确认手机未移动、光线稳定，必要时重新记录空桌面。'
    return result,'ready',f'空桌对比已开启，发现 {len(result)} 个未归类变化区域；阴影或反光也可能触发。'


def _point_segment_distance(point, first, second):
    vector = second-first
    length_squared = float(np.dot(vector,vector))
    if length_squared < 1e-9:
        return float(np.linalg.norm(point-first))
    fraction = np.clip(np.dot(point-first,vector)/length_squared,0,1)
    return float(np.linalg.norm(point-(first+fraction*vector)))


def proximity_monitor(markers, objects, width, height):
    threshold = max(20.,float(np.hypot(width,height)*.04))
    output = {'proximity_status':'TARGET_LOST','nearest_distance_px':None,
              'proximity_threshold_px':round(threshold,1),'nearest_obstacle_index':None,
              'proximity_message':'ID 4 丢失或重复，无法判断与障碍物的距离。'}
    targets = [corners for marker_id,corners in markers if marker_id==4]
    if len(targets)!=1:
        return output
    if not objects:
        output.update(proximity_status='NO_CANDIDATES',proximity_message='当前没有可用于距离判断的障碍候选区域；不代表桌面没有障碍。')
        return output
    target = targets[0].astype(np.float32)
    distances = []
    for obj in objects:
        x1,y1,x2,y2 = obj['box_px']
        rectangle = np.float32([[x1,y1],[x2,y1],[x2,y2],[x1,y2]])
        area,_ = cv2.intersectConvexConvex(target,rectangle)
        touching = area>0 or any(cv2.pointPolygonTest(rectangle,tuple(map(float,p)),False)>=0 for p in target)
        if touching:
            distance = 0.
        else:
            distance = min(
                [_point_segment_distance(p,rectangle[i],rectangle[(i+1)%4]) for p in target for i in range(4)] +
                [_point_segment_distance(p,target[i],target[(i+1)%4]) for p in rectangle for i in range(4)])
        obj['target_distance_px'] = round(distance,1)
        obj['near_target'] = distance <= threshold
        obj['overlap_target'] = distance == 0
        distances.append(distance)
    index = int(np.argmin(distances));distance=distances[index];label=objects[index]['label']
    output.update(nearest_distance_px=round(distance,1),nearest_obstacle_index=index)
    if distance==0:
        output.update(proximity_status='OVERLAPPING',proximity_message=f'重叠提示：ID 4 与“{label}”的识别框重叠，可能接触障碍。')
    elif distance<=threshold:
        output.update(proximity_status='NEAR_OBSTACLE',proximity_message=f'靠近障碍：ID 4 距“{label}”识别框约 {distance:.1f} px，请留意。')
    else:
        output.update(proximity_status='FAR',proximity_message=f'最近候选“{label}”距 ID 4 约 {distance:.1f} px，尚未进入提示范围。')
    return output
