const $ = (id) => document.getElementById(id);
const video = $('inputVideo');
const cameraCanvas = $('cameraCanvas');
const cameraContext = cameraCanvas.getContext('2d');
const captureCanvas = $('captureCanvas');
const captureContext = captureCanvas.getContext('2d');
const mapCanvas = $('mapCanvas');
const mapContext = mapCanvas.getContext('2d');
const recordCanvas = $('recordCanvas');
const recordContext = recordCanvas.getContext('2d');
const columns = ['frame','source_time_s','ids','status','coordinate_mode','x_mm','y_mm','x_px','y_px','heading_deg',
  ...[0,1,2,3,4].flatMap((id) => [`id${id}_visible`,`id${id}_x_mm`,`id${id}_y_mm`]),
  'mapping_mode','marker_positions_json','obstacle_status','obstacle_count','obstacles_json',
  'edge_status','edge_distance_px','generic_status','generic_obstacle_count',
  'proximity_status','nearest_distance_px','proximity_threshold_px'];
const statusText = {
  TRACKING: '正在定位 ID 4', TARGET_LOST: '未识别到 ID 4，当前位置不可用。',
  WAITING_REFERENCES: '需要同时看清 ID 0、1、2、3，才能计算坐标。',
  DUPLICATE_ID: '同一个 ID 出现多次，请移走重复的牌。',
  INVALID_GEOMETRY: '参照牌排列无法建立坐标，请检查摆放和标定值。',
  OUTSIDE_TABLE: 'ID 4 的码心超出了设定桌面范围。',
};
let layout, stream = null, sourceType = '', sourceLabel = '', sourceURL = '';
let epoch = 0, playing = false, busy = false, lastTime = -1;
let rows = [], trail = [], validCount = 0, recorder = null;
let currentObstacles = [];
const layoutStorageKey = 'arucoMeasuredLayoutV1';
const editorStorageKey = 'arucoCalibrationEditorV2';
let coordinateMode = 'image', currentMarkers = [], currentFrameSize = [1280,720];
let lastResult = null, deskPolygon = null, resolvedDeskPolygon = null, deskDraft = [], drawingDesk = false, backgroundImage = null;
const overlayBase = document.createElement('canvas');
try { if (localStorage.getItem('arucoCoordinateModeV1') === 'table') coordinateMode = 'table'; } catch {}

function updateModeUI() {
  const image = coordinateMode === 'image';
  const simple = isLShape();
  $('coordinateMode').value = coordinateMode;
  $('coordinateMode').options[1].textContent = simple ? '三牌定位 · 厘米位置' : '桌面定位 · 毫米坐标';
  $('xUnit').textContent = $('yUnit').textContent = image ? 'px' : simple ? 'cm' : 'mm';
  $('xLabel').textContent = simple ? '相对 ID 0：左右位置' : 'X 坐标';
  $('yLabel').textContent = simple ? '相对 ID 0：前后位置' : 'Y 坐标';
  $('mapTitle').textContent = image ? '画面轨迹' : simple ? 'L 形测试区域' : '桌面位置';
  $('axisNote').textContent = image ? '画面左上角为原点，X 向右、Y 向下；朝向 0° 指向画面上方。' : simple ? 'ID 0 中心为起点；向右、向远侧为正数，单位厘米。' : '左近角为原点，X 向右、Y 向远侧。';
  $('modeHint').textContent = image ? '固定摄像头，移动 ID 4 即可；不需要量纸牌位置。' : simple ? '同时看清 0、1、2，移动 ID 4；两段间距已记录，不用计算 X/Y。' : '需按实测位置填写桌面标定；三牌备用需统一朝向和黑框边长。';
  $('tableSize').textContent = image ? `${currentFrameSize[0]} × ${currentFrameSize[1]} px` : layout ? `${layout.table_width_mm/10} × ${layout.table_depth_mm/10} cm${simple ? ' · 测试区' : ''}` : '等待标定';
  $('coordinateNote').textContent = image ? '五张牌均显示画面像素坐标。ID 4 可见即可记录轨迹，无需四角牌齐全；结果不代表桌面厘米位置。请固定摄像头，切换模式或输入会重新统计。' : simple ? '0、1、2 的位置由两段实测间距生成，ID 4 为视觉计算值，ID 3 不参与。此区域不是整张桌面的边界；CSV 仍以明确标注的毫米列保存。' : 'ID 0–3 的桌面坐标为尺量输入的标定值；ID 4 为视觉计算值。码丢失或映射不可用时毫米坐标留空。';
  $('objectProjectionNote').textContent = image ? '橙色框是画面物品识别框，不代表实际桌面占地。' : '橙色区域为识别框的平面投影估计，尚不能直接作为车辆避障边界。';
  $('markerTableX').hidden = $('markerTableY').hidden = image;
  $('markerTableX').textContent = simple ? '左右位置 (cm)' : '桌面 X (mm)';
  $('markerTableY').textContent = simple ? '前后位置 (cm)' : '桌面 Y (mm)';
}
function isLShape() { return coordinateMode === 'table' && layout?.reference_layout_mode === 'l_shape'; }

function renderMarkerPositions(result = {}) {
  const positions = result.marker_positions || [0,1,2,3,4].map((id) => ({id}));
  $('markerPositions').replaceChildren(...positions.map((marker) => {
    const row = document.createElement('tr'); row.dataset.marker = marker.id;
    const divisor = isLShape() ? 10 : 1;
    const values = [`ID ${marker.id}`,isLShape() && marker.id === 3 ? '未参与标定' : marker.duplicate ? '重复 ID' : marker.visible ? (marker.id < 4 ? '参照可见' : '移动目标') : '未识别',
      marker.image_px ? marker.image_px.map((v) => v.toFixed(1)).join(', ') : '—',
      ...(coordinateMode === 'table' ? [marker.table_mm ? (Number(marker.table_mm[0])/divisor).toFixed(1) : '—',
      marker.table_mm ? (Number(marker.table_mm[1])/divisor).toFixed(1) : '—'] : [])];
    for (const value of values) { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); }
    return row;
  }));
  $('mappingMode').textContent = coordinateMode === 'image' ? '免测量 · 画面像素' : isLShape() && result.mapping_mode ? 'L 形三牌定位' : result.mapping_mode === 'four_centres' ? '四牌中心标定' :
    result.mapping_mode === 'three_marker_corners' ? '三牌角点备用标定' : '等待标定参照';
}

function message(text, type = '') {
  $('message').textContent = text;
  $('message').className = type;
}
function confidenceText(object) {
  return Number.isFinite(object.confidence) ? `${Math.round(object.confidence*100)}%` : '变化检测';
}
function resetMonitoring() {
  lastResult = null; deskPolygon = null; resolvedDeskPolygon = null; deskDraft = []; drawingDesk = false; backgroundImage = null;
  $('markDesk').textContent = '标出桌面范围'; cameraCanvas.style.cursor = '';
  updateMonitorControls();
}
function updateMonitorControls() {
  const region = deskPolygon || resolvedDeskPolygon;
  $('markDesk').disabled = !lastResult;
  $('clearDesk').disabled = !region;
  $('captureEmpty').disabled = !lastResult || !region || drawingDesk;
  $('clearEmpty').disabled = !backgroundImage;
  $('deskSetupStatus').textContent = drawingDesk ? `请按顺序点击桌面四角：已选 ${deskDraft.length} / 4。` :
    !region ? '先沿桌面可见范围依次点选四个角；毫米模式也可使用有效标定自动投影的桌面范围。' :
    backgroundImage ? '范围和空桌参考已就绪；移动手机、变焦或换输入后需重新设置。' : isLShape() && !deskPolygon ? '当前边界是三牌测试区，不是整桌；可用“标出桌面范围”另圈实际可见边界。' : '桌面范围已设置；清空待检测物品后点“记录空桌面”，定位牌可以保留。';
}
function paintDeskOverlay() {
  if (!overlayBase.width || !lastResult) return;
  cameraContext.drawImage(overlayBase,0,0);
  const polygon = drawingDesk ? deskDraft : deskPolygon || resolvedDeskPolygon;
  if (!polygon?.length) return;
  const scale = Math.min(cameraCanvas.clientWidth/cameraCanvas.width,cameraCanvas.clientHeight/cameraCanvas.height) || 1;
  cameraContext.strokeStyle = ['OUTSIDE','CROSSING_EDGE'].includes(lastResult.edge_status) ? '#ff6860' : '#46c8ed';
  cameraContext.fillStyle = '#46c8ed18'; cameraContext.lineWidth = Math.max(2,2/scale);
  cameraContext.beginPath();
  polygon.forEach(([x,y],i) => i ? cameraContext.lineTo(x*cameraCanvas.width,y*cameraCanvas.height) : cameraContext.moveTo(x*cameraCanvas.width,y*cameraCanvas.height));
  if (!drawingDesk) { cameraContext.closePath(); cameraContext.fill(); }
  cameraContext.stroke();
  if (drawingDesk) for (const [x,y] of polygon) { cameraContext.beginPath(); cameraContext.arc(x*cameraCanvas.width,y*cameraCanvas.height,Math.max(5,4/scale),0,Math.PI*2); cameraContext.fillStyle='#46c8ed'; cameraContext.fill(); }
}
function renderMonitoring(result) {
  const state = result.edge_status || 'NOT_SET';
  $('edgeAlert').textContent = result.edge_message || '未设置桌面范围，暂不能判断是否越界。';
  $('edgeAlert').className = ['OUTSIDE','CROSSING_EDGE'].includes(state) ? 'monitor-danger' : ['NEAR_EDGE','TARGET_LOST'].includes(state) ? 'monitor-warning' : state === 'INSIDE' ? 'monitor-safe' : 'monitor-neutral';
  $('proximityAlert').textContent = result.proximity_message || '等待 ID 4 和障碍候选。';
  $('proximityAlert').className = result.proximity_status === 'OVERLAPPING' ? 'monitor-danger' : ['NEAR_OBSTACLE','TARGET_LOST'].includes(result.proximity_status) ? 'monitor-warning' : 'monitor-neutral';
  const count = result.obstacles?.length || 0;
  const generic = result.generic_obstacle_count || 0;
  $('obstacleAlert').textContent = `${count ? `提示：检测到 ${count} 个物品／候选区域，其中 ${generic} 个为未知变化。` : '当前未检出物品／候选区域。'} ${result.generic_message || ''}`;
  $('obstacleAlert').className = count || result.generic_status === 'scene_changed' ? 'monitor-warning' : 'monitor-neutral';
  updateMonitorControls();
}
function convexQuad(points) {
  if (points.length!==4) return false;
  const turns = points.map((a,i) => {const b=points[(i+1)%4],c=points[(i+2)%4];return (b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]);});
  const area = Math.abs(points.reduce((sum,p,i) => sum+p[0]*points[(i+1)%4][1]-p[1]*points[(i+1)%4][0],0))/2;
  return area>.002 && (turns.every((v)=>v>0)||turns.every((v)=>v<0));
}
function refreshAnalysis() {
  epoch++; lastTime=-1;
  if (playing) processFrame(epoch);
  else if (lastResult) analyzeCanvas(epoch).catch((error)=>message(error.message,'error'));
}
function timeText(seconds) {
  return `${Math.floor(seconds / 60).toString().padStart(2,'0')}:${Math.floor(seconds % 60).toString().padStart(2,'0')}`;
}
function download(blob, name) {
  const anchor = document.createElement('a');
  const url = URL.createObjectURL(blob);
  anchor.href = url; anchor.download = name;
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
function clearPose() {
  for (const id of ['x', 'y', 'heading', 'latency']) $(id).textContent = '—';
  document.querySelectorAll('[data-id]').forEach((el) => el.classList.remove('visible'));
  currentObstacles = []; $('objectCount').textContent = '0 件';
  currentMarkers = [];
  $('trailInfo').textContent = `轨迹采样 ${trail.filter((value) => value !== null).length} 点；当前未采样，不追加轨迹。`;
  $('objectList').replaceChildren(); $('objectStatus').textContent = '等待下一次识别';
  $('edgeAlert').textContent = '当前未采样，无法确认实时越界状态。'; $('edgeAlert').className = 'monitor-neutral';
  $('proximityAlert').textContent = '当前未采样，不更新 ID 4 与障碍物的距离提示。'; $('proximityAlert').className = 'monitor-neutral';
  $('obstacleAlert').textContent = '当前未采样，暂停时不更新障碍提示。'; $('obstacleAlert').className = 'monitor-neutral';
  renderMarkerPositions();
  drawMap(null);
}
function updateRecordingFrame() {
  recordContext.fillStyle = '#f5f7f8'; recordContext.fillRect(0,0,1440,810);
  recordContext.fillStyle = '#203d45'; recordContext.font = '26px sans-serif';
  recordContext.fillText(coordinateMode === 'image' ? 'ArUco 像素轨迹演示' : 'ArUco 桌面定位测试',28,42);
  recordContext.font = '17px sans-serif'; recordContext.fillText(sourceLabel,28,75);
  if (cameraCanvas.width) recordContext.drawImage(cameraCanvas,24,100,920,540);
  recordContext.drawImage(mapCanvas,965,130,450,225);
  recordContext.fillStyle = '#203d45'; recordContext.font = '20px sans-serif';
  recordContext.fillText(`X  ${$('x').textContent} ${$('xUnit').textContent}`,985,420);
  recordContext.fillText(`Y  ${$('y').textContent} ${$('yUnit').textContent}`,985,458);
  recordContext.fillText(`朝向  ${$('heading').textContent}°`,985,496);
  recordContext.font = '17px sans-serif'; recordContext.fillStyle = '#99622b';
  recordContext.fillText(`桌面物品 ${currentObstacles.length} 件`,985,548);
  currentObstacles.slice(0,3).forEach((item,index) => recordContext.fillText(`${item.label} ${confidenceText(item)}`,985,580+index*27));
  recordContext.fillStyle = '#a54139'; recordContext.fillText(`边界状态 ${lastResult?.edge_status || 'NOT_SET'}`,985,680);
  recordContext.fillText(`障碍接近 ${lastResult?.proximity_status || 'NOT_READY'}`,985,710);
  recordContext.font = '17px sans-serif';
  recordContext.fillText($('message').textContent,28,690);
  recordContext.fillText(`有效定位 ${validCount} / ${rows.length} 帧`,28,730);
  if (sourceType === 'sample') {
    recordContext.fillStyle = '#a84d31'; recordContext.fillText('生成样本 · SYNTHETIC TEST INPUT',28,770);
  }
}
function stopRecording() {
  if (recorder?.state === 'recording') recorder.stop();
  $('record').textContent = '录制测试'; $('record').classList.remove('recording');
}
function stopSource() {
  playing = false; epoch++; lastTime = -1;
  video.pause();
  if (stream) { stream.getTracks().forEach((track) => track.stop()); stream = null; }
  video.srcObject = null;
  $('camera').textContent = '开启摄像头';
  $('pause').disabled = true; $('record').disabled = true; $('seek').disabled = true;
  if (sourceURL) { URL.revokeObjectURL(sourceURL); sourceURL = ''; }
  stopRecording(); resetMonitoring(); clearPose();
}
function resetData() {
  rows = []; trail = []; validCount = 0;
  $('trailInfo').textContent = '轨迹采样 0 点；需先获得有效坐标。';
  $('validCount').textContent = '0 / 0 帧'; $('export').disabled = true;
  clearPose();
}
function drawImageMap(pose) {
  const c = mapContext, [width,height] = currentFrameSize;
  const scale = Math.min(790/width,330/height), left = 55, top = 40;
  const point = (x,y) => [left+x*scale,top+y*scale];
  c.fillStyle = '#f7faf9'; c.fillRect(0,0,900,450);
  c.strokeStyle = '#d8e5df'; c.lineWidth = 1;
  for (let i=1;i<4;i++) {
    c.beginPath(); c.moveTo(...point(width*i/4,0)); c.lineTo(...point(width*i/4,height)); c.stroke();
  }
  c.strokeStyle = '#91aaa3'; c.strokeRect(left,top,width*scale,height*scale);
  const desk = deskPolygon || resolvedDeskPolygon;
  if (desk) {
    c.strokeStyle = '#2698b7'; c.lineWidth = 2; c.beginPath();
    desk.forEach(([x,y],i) => i ? c.lineTo(...point(x*width,y*height)) : c.moveTo(...point(x*width,y*height)));
    c.closePath(); c.stroke();
  }
  for (const object of currentObstacles) {
    const [x1,y1,x2,y2] = object.box_px;
    c.fillStyle = '#e5a24633'; c.fillRect(...point(x1,y1),(x2-x1)*scale,(y2-y1)*scale);
    c.strokeStyle = '#c38738'; c.strokeRect(...point(x1,y1),(x2-x1)*scale,(y2-y1)*scale);
  }
  c.fillStyle = '#55736c'; c.font = '20px sans-serif';
  for (const marker of currentMarkers) {
    if (!marker.image_px || marker.id === 4) continue;
    const [x,y] = point(...marker.image_px);
    c.beginPath(); c.arc(x,y,5,0,Math.PI*2); c.fill(); c.fillText(`ID ${marker.id}`,x+9,y-6);
  }
  c.strokeStyle = '#16756b'; c.lineWidth = 3; c.beginPath(); let connected = false;
  for (const value of trail) {
    if (value === null) { connected = false; continue; }
    if (connected) c.lineTo(...point(...value)); else c.moveTo(...point(...value));
    connected = true;
  }
  c.stroke(); c.fillStyle = '#5a9b8b';
  for (const value of trail) { if (!value) continue; c.beginPath(); c.arc(...point(...value),2.2,0,Math.PI*2); c.fill(); }
  if (pose) {
    const [x,y] = point(pose[0],pose[1]), angle = pose[2]*Math.PI/180;
    c.fillStyle = '#16756b'; c.beginPath(); c.arc(x,y,8,0,Math.PI*2); c.fill();
    c.strokeStyle = '#16756b'; c.lineWidth = 4; c.beginPath(); c.moveTo(x,y); c.lineTo(x+30*Math.sin(angle),y-30*Math.cos(angle)); c.stroke();
  }
  c.fillStyle = '#6a827a'; c.font = '18px sans-serif';
  c.fillText(`画面像素 · ${width} × ${height} px`,left,top+height*scale+34);
}
function drawMap(pose) {
  if (coordinateMode === 'image') { drawImageMap(pose); return; }
  if (!layout) return;
  const c = mapContext, width = layout.table_width_mm, depth = layout.table_depth_mm;
  const scale = Math.min(790 / width, 345 / depth);
  const left = 55, bottom = 400;
  const point = (x,y) => [left + x*scale, bottom - y*scale];
  c.fillStyle = '#f7faf9'; c.fillRect(0,0,900,450);
  c.strokeStyle = '#d8e5df'; c.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const x = left + width*scale*i/4;
    c.beginPath(); c.moveTo(x,bottom); c.lineTo(x,bottom-depth*scale); c.stroke();
  }
  c.strokeStyle = '#91aaa3'; c.lineWidth = 2;
  c.strokeRect(left,bottom-depth*scale,width*scale,depth*scale);
  c.fillStyle = '#55736c'; c.font = '22px sans-serif';
  for (const [id,xy] of Object.entries(layout.reference_centres_mm)) {
    if (isLShape() && id === '3') continue;
    const [x,y] = point(...xy);
    c.beginPath(); c.arc(x,y,6,0,Math.PI*2); c.fill(); c.fillText(id,x+12,y+8);
  }
  for (const object of currentObstacles) {
    const polygon = object.table_polygon_mm;
    if (!polygon?.length) continue;
    c.beginPath();
    polygon.forEach((xy,index) => index ? c.lineTo(...point(...xy)) : c.moveTo(...point(...xy)));
    c.closePath(); c.fillStyle = '#e5a24644'; c.fill();
    c.strokeStyle = '#c38738'; c.lineWidth = 2; c.stroke();
    c.fillStyle = '#956024'; c.font = '20px sans-serif';
    const centre = polygon.reduce((sum,xy) => [sum[0]+xy[0]/polygon.length,sum[1]+xy[1]/polygon.length],[0,0]);
    c.fillText(object.label,...point(...centre));
  }
  c.strokeStyle = '#b3c9c1'; c.lineWidth = 3; c.beginPath();
  let connected = false;
  for (const value of trail) {
    if (value === null) { connected = false; continue; }
    const [x,y] = point(...value);
    if (connected) c.lineTo(x,y); else c.moveTo(x,y);
    connected = true;
  }
  c.stroke();
  // Keep isolated valid observations visible without joining across lost frames.
  c.fillStyle = '#5a9b8b';
  for (const value of trail) {
    if (value === null) continue;
    c.beginPath(); c.arc(...point(...value),2.2,0,Math.PI*2); c.fill();
  }
  if (pose) {
    const [x,y] = point(pose[0],pose[1]);
    const angle = pose[2]*Math.PI/180;
    c.fillStyle = '#16756b'; c.beginPath(); c.arc(x,y,9,0,Math.PI*2); c.fill();
    c.strokeStyle = '#16756b'; c.lineWidth = 4; c.beginPath(); c.moveTo(x,y);
    c.lineTo(x+38*Math.sin(angle),y-38*Math.cos(angle)); c.stroke();
  }
  c.fillStyle = '#6a827a'; c.font = '18px sans-serif'; c.fillText('(0, 0)',left,bottom+31);
}
function renderFrame(result) {
  lastResult = result;
  cameraCanvas.width = captureCanvas.width; cameraCanvas.height = captureCanvas.height;
  cameraContext.drawImage(captureCanvas,0,0);
  currentMarkers = result.marker_positions || [];
  currentFrameSize = result.image_size_px || [captureCanvas.width,captureCanvas.height];
  resolvedDeskPolygon = result.desk_polygon_px?.map(([x,y]) => [x/currentFrameSize[0],y/currentFrameSize[1]]) || null;
  updateModeUI();
  const overlayScale = Math.min(cameraCanvas.clientWidth/cameraCanvas.width,cameraCanvas.clientHeight/cameraCanvas.height) || 1;
  const labelSize = Math.max(18,Math.min(64,15/overlayScale));
  cameraContext.lineWidth = Math.max(2,2/overlayScale); cameraContext.font = `${labelSize}px sans-serif`;
  for (const marker of result.corners) {
    const danger = marker.id===4 && (['OUTSIDE','CROSSING_EDGE'].includes(result.edge_status) || result.proximity_status==='OVERLAPPING');
    const near = marker.id===4 && (result.edge_status==='NEAR_EDGE' || result.proximity_status==='NEAR_OBSTACLE');
    cameraContext.strokeStyle = danger ? '#ff625a' : near ? '#ffbd59' : '#2ce393'; cameraContext.fillStyle = cameraContext.strokeStyle;
    cameraContext.beginPath();
    marker.points.forEach(([x,y],i) => i ? cameraContext.lineTo(x,y) : cameraContext.moveTo(x,y));
    cameraContext.closePath(); cameraContext.stroke();
    const entry = currentMarkers.find((value) => value.id === marker.id);
    const position = coordinateMode === 'image' ? entry?.image_px : entry?.table_mm;
    const text = `ID ${marker.id}${position ? ` (${position.map((v) => isLShape() ? (v/10).toFixed(1) : Math.round(v)).join(', ')}) ${coordinateMode === 'image' ? 'px' : isLShape() ? 'cm' : 'mm'}` : ''}`;
    const textX = Math.max(0,Math.min(marker.points[0][0],cameraCanvas.width-cameraContext.measureText(text).width));
    cameraContext.fillText(text,textX,Math.max(labelSize,marker.points[0][1]-6));
  }
  currentObstacles = result.obstacles || [];
  for (const object of currentObstacles) {
    const [x1,y1,x2,y2] = object.box_px;
    const label = `${object.source === 'background_difference' ? '未知变化' : object.label} · ${confidenceText(object)}`;
    cameraContext.strokeStyle = object.overlap_target ? '#ff625a' : object.near_target ? '#ff914f' : '#ffbd59'; cameraContext.lineWidth = Math.max(3,2/overlayScale);
    cameraContext.strokeRect(x1,y1,x2-x1,y2-y1);
    cameraContext.font = `${labelSize}px sans-serif`;
    const textWidth = cameraContext.measureText(label).width+16, textHeight = labelSize+12;
    const textY = Math.max(0,y1-textHeight), textX = Math.min(x1,Math.max(0,cameraCanvas.width-textWidth));
    cameraContext.fillStyle = '#ffbd59'; cameraContext.fillRect(textX,textY,textWidth,textHeight);
    cameraContext.fillStyle = '#382b19'; cameraContext.fillText(label,textX+8,textY+labelSize+2);
  }
  $('objectCount').textContent = `${currentObstacles.length} 件`;
  $('objectList').replaceChildren(...currentObstacles.map((object) => {
    const item = document.createElement('li'), name = document.createElement('b'), detail = document.createElement('span');
    name.textContent = object.label;
    detail.textContent = `${confidenceText(object)} · ${coordinateMode === 'image' ? '画面物品框' : object.table_polygon_mm ? '已作平面投影' : '未映射到桌面'}`;
    item.append(name,detail); return item;
  }));
  const mapped = currentObstacles.filter((item) => item.table_polygon_mm).length;
  $('objectStatus').textContent = result.obstacle_status === 'disabled' ? (result.generic_status !== 'disabled' ? '类别识别已关闭；未知物品检测需设置范围和空桌参考。' : '物品识别已关闭') :
    result.obstacle_status !== 'ready' ? `物品识别不可用：${result.obstacle_error || '模型未载入'}` :
    currentObstacles.length ? `识别到 ${currentObstacles.length} 件物品／候选区域${coordinateMode === 'image' ? '，显示画面像素位置。' : result.homography ? `，其中 ${mapped} 件已作投影估计。` : '；参照不足，仅显示画面位置。'}` : '当前未检出物品或明显变化，请保持光线稳定。';
  if (sourceType === 'sample') {
    cameraContext.fillStyle = '#ffffffdd'; cameraContext.fillRect(0,cameraCanvas.height-34,cameraCanvas.width,34);
    cameraContext.fillStyle = '#995233'; cameraContext.font = '16px sans-serif';
    cameraContext.fillText('生成样本 · SYNTHETIC TEST INPUT',12,cameraCanvas.height-12);
  }
  overlayBase.width = cameraCanvas.width; overlayBase.height = cameraCanvas.height;
  overlayBase.getContext('2d').drawImage(cameraCanvas,0,0);
  paintDeskOverlay(); renderMonitoring(result);
  const pose = result.pose;
  renderMarkerPositions(result);
  for (const [i,id] of ['x','y','heading'].entries()) $(id).textContent = pose ? (pose[i]/(isLShape() && i<2 ? 10 : 1)).toFixed(1) : '—';
  document.querySelectorAll('[data-id]').forEach((el) => el.classList.toggle('visible',result.ids.includes(Number(el.dataset.id))));
  trail.push(pose ? pose.slice(0,2) : null);
  if (trail.length > 4000) trail.shift();
  if (result.status === 'TRACKING') validCount++;
  const trailCount = trail.filter((value) => value !== null).length;
  $('trailInfo').textContent = `轨迹采样 ${trailCount} 点${pose ? '；移动 ID 4 可记录轨迹。' : '；当前无有效坐标，不追加轨迹。'}`;
  const markerColumns = (result.marker_positions || [0,1,2,3,4].map((id) => ({id}))).flatMap((marker) => [marker.visible ? 1 : 0,...(marker.table_mm || ['',''])]);
  const targetImage = currentMarkers.find((marker) => marker.id === 4)?.image_px || ['',''];
  const tablePose = coordinateMode === 'table' && pose ? pose.slice(0,2) : ['',''];
  rows.push([rows.length+1,sourceType === 'image' ? '0.000' : video.currentTime.toFixed(3),result.ids.join(' '),result.status,coordinateMode,...tablePose,...targetImage,pose ? pose[2] : '',
    ...markerColumns,result.mapping_mode || '',JSON.stringify(result.marker_positions || []),result.obstacle_status,currentObstacles.length,JSON.stringify(currentObstacles),
    result.edge_status || '',result.edge_distance_px ?? '',result.generic_status || '',result.generic_obstacle_count || 0,
    result.proximity_status || '',result.nearest_distance_px ?? '',result.proximity_threshold_px ?? '']);
  $('validCount').textContent = `${validCount} / ${rows.length} 帧`;
  $('latency').textContent = `${result.processing_ms.toFixed(1)} ms`;
  $('frameInfo').textContent = `${captureCanvas.width} × ${captureCanvas.height} · ${result.ids.length} 个标记 · ${currentObstacles.length} 件物品`;
  let positionStatus = result.status === 'WAITING_REFERENCES' && layout.allow_three_references ? '需要至少三张朝向正确的参照牌（ID 0–3）才能计算桌面坐标。' : statusText[result.status] || result.status;
  if (isLShape() && result.status === 'WAITING_REFERENCES') positionStatus = '请让摄像头同时看清 ID 0、1、2；ID 3 不能替代这三张牌。';
  if (isLShape() && result.status === 'OUTSIDE_TABLE') positionStatus = 'ID 4 的中心超出了三牌围出的测试区域。';
  if (coordinateMode === 'image' && result.status === 'TRACKING') positionStatus = '正在记录 ID 4 的画面像素轨迹；无需桌面尺寸标定。';
  if (result.status === 'INVALID_GEOMETRY' && result.geometry_hint) {
    positionStatus = result.geometry_hint;
    if (!isLShape() && Number.isFinite(result.mapping_error_mm)) positionStatus += ` 角点最大拟合差 ${result.mapping_error_mm.toFixed(1)} mm（允许 ${result.mapping_error_limit_mm.toFixed(1)} mm）。`;
  }
  const pausedFrame = !playing && ['file','sample'].includes(sourceType) ? '暂停帧 · ' : '';
  message(`${pausedFrame}${positionStatus}${result.mapping_mode === 'three_marker_corners' ? (isLShape() ? ' 当前使用 L 形三牌记录。' : ' 当前使用三牌角点备用定位。') : ''}${currentObstacles.length ? ` 已识别 ${currentObstacles.length} 件桌面物品。` : ''}`, result.status === 'TRACKING' ? 'success' : 'error');
  $('export').disabled = false;
  drawMap(pose); updateRecordingFrame();
}
async function analyzeCanvas(token) {
  const response = await fetch('/api/frame',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({layout,coordinate_mode:coordinateMode,image:captureCanvas.toDataURL('image/jpeg',.9),detect_objects:$('detectObjects').checked,object_confidence:Number($('confidence').value)/100,
      desk_polygon_normalized:deskPolygon,detect_unknown:$('detectUnknown').checked,background_image:$('detectUnknown').checked ? backgroundImage : null})});
  const result = await response.json();
  if (token !== epoch) return;
  if (!response.ok) throw new Error(result.error || '处理失败');
  renderFrame(result);
}
async function processFrame(token) {
  if (!playing || token !== epoch) return;
  if (busy || video.readyState < 2 || (sourceType !== 'camera' && video.currentTime === lastTime)) {
    setTimeout(() => processFrame(token),80); return;
  }
  busy = true; lastTime = video.currentTime;
  try {
    const ratio = Math.min(1,1600/video.videoWidth);
    captureCanvas.width = Math.round(video.videoWidth*ratio); captureCanvas.height = Math.round(video.videoHeight*ratio);
    captureContext.drawImage(video,0,0,captureCanvas.width,captureCanvas.height);
    await analyzeCanvas(token);
  } catch (error) {
    if (token === epoch) { playing = false; video.pause(); clearPose(); stopRecording(); message(error.message,'error'); $('pause').textContent = '继续'; }
  } finally { busy = false; }
  if (playing && token === epoch) setTimeout(() => processFrame(token),85);
}
async function startVideo(source,label,type) {
  stopSource(); resetData(); sourceType = type; sourceLabel = label;
  const token = epoch;
  if (source instanceof Blob) { sourceURL = URL.createObjectURL(source); video.src = sourceURL; }
  else video.src = source;
  $('sourceName').textContent = label;
  try {
    await video.play();
    if (token !== epoch) return;
    playing = true; $('empty').hidden = true;
    $('pause').disabled = false; $('pause').textContent = '暂停'; $('record').disabled = false;
    $('seek').disabled = false; processFrame(epoch);
  } catch (error) { message(`录像无法播放：${error.message}`,'error'); }
}
async function startImage(file) {
  stopSource(); resetData(); sourceType = 'image'; sourceLabel = file.name;
  const token = epoch;
  $('sourceName').textContent = file.name; message('正在识别图片中的定位牌和物品…');
  try {
    const image = await createImageBitmap(file);
    if (token !== epoch) { image.close(); return; }
    const ratio = Math.min(1,1600/image.width);
    captureCanvas.width = Math.round(image.width*ratio); captureCanvas.height = Math.round(image.height*ratio);
    captureContext.drawImage(image,0,0,captureCanvas.width,captureCanvas.height); image.close();
    $('empty').hidden = true; $('seek').value = 0; $('time').textContent = '静态图片';
    await analyzeCanvas(token);
  } catch (error) { if (token === epoch) message(`图片无法读取：${error.message}`,'error'); }
}
async function refreshCameras() {
  if (!navigator.mediaDevices?.enumerateDevices) { message('当前浏览器不支持摄像头枚举，请使用 Mac 上的 Chrome 或 Safari。','error'); return; }
  const selected = $('devices').value;
  const cameras = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'videoinput');
  $('devices').replaceChildren(new Option('系统默认',''),...cameras.map((d,i) => new Option(d.label || `摄像头 ${i+1}`,d.deviceId)));
  const active = stream?.getVideoTracks()[0]?.getSettings().deviceId || selected;
  if (cameras.some((d) => d.deviceId === active)) $('devices').value = active;
  return cameras;
}
async function startCamera(changeDevice = false) {
  if (!changeDevice && sourceType === 'camera' && stream) {
    stopSource(); sourceType = ''; $('pause').disabled = true; $('record').disabled = true;
    $('sourceName').textContent = '摄像头已关闭'; message('可以重新开启摄像头或导入录像。'); return;
  }
  stopSource(); resetData(); sourceType = 'camera'; sourceLabel = '实时摄像头';
  const token = epoch;
  try {
    const deviceId = $('devices').value;
    const requestedStream = await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1920},height:{ideal:1080},...(deviceId ? {deviceId:{exact:deviceId}} : {})},audio:false});
    if (token !== epoch) { requestedStream.getTracks().forEach((track) => track.stop()); return; }
    stream = requestedStream;
    video.removeAttribute('src'); video.srcObject = stream; await video.play();
    if (token !== epoch) return;
    sourceLabel = stream.getVideoTracks()[0].label || '实时摄像头';
    playing = true; $('empty').hidden = true; $('sourceName').textContent = sourceLabel;
    $('camera').textContent = '关闭摄像头';
    $('pause').disabled = false; $('pause').textContent = '暂停'; $('record').disabled = false; $('seek').disabled = true;
    stream.getVideoTracks()[0].onended = () => { if (stream === requestedStream) { stopSource(); message('摄像头连接已断开，请检查 iPhone 或 USB 后重新开启。','error'); } };
    stream.getVideoTracks()[0].onmute = () => {
      if (stream !== requestedStream) return;
      playing = false; epoch++; clearPose(); stopRecording();
      $('pause').textContent = '继续'; $('record').disabled = true;
      message('摄像头画面已中断，当前坐标已清空。恢复 iPhone 连接后点「继续」。','error');
    };
    await refreshCameras();
    processFrame(epoch);
  } catch (error) { if (token === epoch) { stopSource(); message(`摄像头无法开启：${error.message}。请检查浏览器和系统相机权限。`,'error'); } }
}
$('camera').onclick = () => startCamera();
$('devices').onchange = () => { if (sourceType === 'camera' && stream) startCamera(true); };
$('refreshCameras').onclick = () => refreshCameras().then((cameras) => { if (cameras) message(cameras.length ? '摄像头列表已刷新，请选择 iPhone；若名称为空，先开启摄像头并授权。' : '暂未发现摄像头，请连接 iPhone、锁屏并确认连续互通相机已开启。'); }).catch((error) => message(error.message,'error'));
if (navigator.mediaDevices?.addEventListener) navigator.mediaDevices.addEventListener('devicechange',() => refreshCameras().catch(() => {}));
$('sample').onclick = () => startVideo('/sample.mp4','生成样本（程序测试）','sample');
$('file').onchange = (event) => { const file = event.target.files[0]; if (file) file.type.startsWith('image/') ? startImage(file) : startVideo(file,file.name,'file'); event.target.value = ''; };
$('confidence').oninput = () => { $('confidenceValue').textContent = `${$('confidence').value}%`; };
function updateDetectionSettings() {
  epoch++; lastTime = -1; clearPose();
  if (playing) processFrame(epoch);
  else if (sourceType === 'image') analyzeCanvas(epoch).catch((error) => message(error.message,'error'));
}
$('confidence').onchange = updateDetectionSettings;
$('detectObjects').onchange = updateDetectionSettings;
$('markDesk').onclick = () => {
  drawingDesk = !drawingDesk; deskDraft = [];
  $('markDesk').textContent = drawingDesk ? '取消标记' : '标出桌面范围';
  cameraCanvas.style.cursor = drawingDesk ? 'crosshair' : '';
  updateMonitorControls(); paintDeskOverlay();
};
cameraCanvas.addEventListener('click',(event) => {
  if (!drawingDesk || !lastResult) return;
  const rect = cameraCanvas.getBoundingClientRect();
  const scale = Math.min(rect.width/cameraCanvas.width,rect.height/cameraCanvas.height);
  const x = (event.clientX-rect.left-(rect.width-cameraCanvas.width*scale)/2)/(cameraCanvas.width*scale);
  const y = (event.clientY-rect.top-(rect.height-cameraCanvas.height*scale)/2)/(cameraCanvas.height*scale);
  if (x<0 || y<0 || x>1 || y>1) return;
  deskDraft.push([x,y]);
  if (deskDraft.length===4) {
    if (!convexQuad(deskDraft)) {deskDraft=[];message('范围交叉或过小，请沿桌面边缘依次点选四个角。','error');}
    else {
      deskPolygon=deskDraft; deskDraft=[]; drawingDesk=false; backgroundImage=null;
      $('markDesk').textContent='标出桌面范围'; cameraCanvas.style.cursor='';
      message('桌面范围已设置。清空待检测物品后记录空桌面；ID 4 越界会单独提示。');
      refreshAnalysis();
    }
  }
  updateMonitorControls(); paintDeskOverlay();
});
$('clearDesk').onclick = () => {deskPolygon=null;resolvedDeskPolygon=null;deskDraft=[];drawingDesk=false;backgroundImage=null;$('markDesk').textContent='标出桌面范围';cameraCanvas.style.cursor='';updateMonitorControls();paintDeskOverlay();refreshAnalysis();};
$('captureEmpty').onclick = () => {backgroundImage=captureCanvas.toDataURL('image/jpeg',.9);updateMonitorControls();message('空桌参考已记录。参考中已有的物品会作为背景，请确保已移走待检测障碍。');refreshAnalysis();};
$('clearEmpty').onclick = () => {backgroundImage=null;updateMonitorControls();refreshAnalysis();};
$('detectUnknown').onchange = refreshAnalysis;
$('coordinateMode').onchange = () => {
  coordinateMode = $('coordinateMode').value;
  try { localStorage.setItem('arucoCoordinateModeV1',coordinateMode); } catch {}
  stopRecording(); epoch++; lastTime = -1; resetData(); updateModeUI();
  message(coordinateMode === 'image' ? '已切到免测量演示。固定摄像头，移动 ID 4 即可记录像素轨迹。' : '已切到桌面毫米定位，请先确认参照牌的实测标定。');
  if (playing) processFrame(epoch);
  else if (lastResult) analyzeCanvas(epoch).catch((error) => message(error.message,'error'));
};
$('pause').onclick = async () => {
  if (playing) {
    playing = false; epoch++; video.pause(); clearPose(); stopRecording();
    $('pause').textContent = '继续'; $('record').disabled = true; message('已暂停，当前坐标不再更新。');
  } else {
    if (video.ended) video.currentTime = 0;
    try { await video.play(); playing = true; epoch++; lastTime = -1; $('pause').textContent = '暂停'; $('record').disabled = false; processFrame(epoch); }
    catch (error) { message(error.message,'error'); }
  }
};
video.ontimeupdate = () => {
  if (sourceType === 'camera' || sourceType === 'image') return;
  const duration = Number.isFinite(video.duration) ? video.duration : 0;
  $('seek').value = duration ? video.currentTime/duration*100 : 0;
  $('time').textContent = `${timeText(video.currentTime)} / ${timeText(duration)}`;
};
video.onended = () => { playing = false; epoch++; stopRecording(); clearPose(); $('pause').textContent = '重新播放'; $('record').disabled = true; message('录像处理完成，可以导出 CSV。'); };
video.addEventListener('seeked',async () => {
  if (playing || !['file','sample'].includes(sourceType) || video.readyState<2) return;
  const token=epoch,ratio=Math.min(1,1600/video.videoWidth);
  captureCanvas.width=Math.round(video.videoWidth*ratio);captureCanvas.height=Math.round(video.videoHeight*ratio);
  captureContext.drawImage(video,0,0,captureCanvas.width,captureCanvas.height);
  try {await analyzeCanvas(token);} catch (error) {if(token===epoch)message(error.message,'error');}
});
$('seek').oninput = () => {
  epoch++; lastTime = -1; clearPose();
  if (Number.isFinite(video.duration)) video.currentTime = Number($('seek').value)*video.duration/100;
  trail.push(null);
  if (playing) processFrame(epoch);
};
$('clear').onclick = () => { resetData(); message('轨迹和统计已清空。'); };
$('export').onclick = () => {
  const csv = [columns,...rows].map((row) => row.map((value) => `"${String(value).replaceAll('"','""')}"`).join(',')).join('\r\n');
  download(new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8'}),`aruco_positions_${Date.now()}.csv`);
};
$('record').onclick = () => {
  if (recorder?.state === 'recording') { stopRecording(); return; }
  if (!playing) return;
  if (!window.MediaRecorder || !recordCanvas.captureStream) { message('当前浏览器不支持录制，请使用最新版 Chrome。','error'); return; }
  const mime = ['video/mp4','video/webm;codecs=vp8','video/webm'].find((type) => MediaRecorder.isTypeSupported(type));
  const recordedStream = recordCanvas.captureStream(15);
  recorder = new MediaRecorder(recordedStream,mime ? {mimeType:mime} : undefined);
  const activeRecorder = recorder;
  const chunks = [], extension = recorder.mimeType.includes('mp4') ? 'mp4' : 'webm';
  recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
  recorder.onstop = () => {
    recordedStream.getTracks().forEach((t) => t.stop());
    if (chunks.length) download(new Blob(chunks,{type:activeRecorder.mimeType}),`aruco_test_${Date.now()}.${extension}`);
  };
  updateRecordingFrame(); recorder.start(250);
  $('record').textContent = '结束并保存'; $('record').classList.add('recording');
};
function lShapeLayout(a,b,side) {
  if (![a,b,side].every(Number.isFinite) || Math.min(a,b,side)<=0) throw new Error('请先量好 A、B 两段距离，再填入厘米数。');
  if (a<=side || b<=side) throw new Error('两段中心间距应大于黑框边长，请把纸牌分开摆放后再量。');
  const width=a*10,depth=b*10;
  return {table_width_mm:width,table_depth_mm:depth,target_id:4,
    reference_centres_mm:{0:[0,0],1:[width,0],2:[width,depth],3:[0,depth]},
    reference_layout_mode:'l_shape',reference_inset_mm:0,allow_three_references:true,
    reference_marker_size_mm:side*10,l_shape_horizontal_cm:a,l_shape_depth_cm:b};
}
function readLShape() {
  const form=$('layoutForm').elements;
  return lShapeLayout(Number(form.lHorizontalCm.value),Number(form.lDepthCm.value),Number(form.lMarkerCm.value));
}
$('configure').onclick = () => {
  if (!layout) return;
  const form=$('layoutForm').elements;
  form.width.value = layout.table_width_mm;
  form.depth.value = layout.table_depth_mm;
  form.allowThree.checked = Boolean(layout.allow_three_references);
  form.markerSize.value = layout.reference_marker_size_mm || 60;
  form.lHorizontalCm.value = layout.reference_layout_mode === 'l_shape' ? layout.table_width_mm/10 : '';
  form.lDepthCm.value = layout.reference_layout_mode === 'l_shape' ? layout.table_depth_mm/10 : '';
  form.lMarkerCm.value = (layout.reference_marker_size_mm || 60)/10;
  $('referenceInputs').innerHTML = [0,1,2,3].map((i) => `<tr><td>ID ${i}</td><td><input aria-label="ID ${i} X" name="x${i}" type="number" step="any" required value="${layout.reference_centres_mm[i][0]}"></td><td><input aria-label="ID ${i} Y" name="y${i}" type="number" step="any" required value="${layout.reference_centres_mm[i][1]}"></td></tr>`).join('');
  let editor='l_shape';
  try { const stored=localStorage.getItem(editorStorageKey);if(['l_shape','corners','manual'].includes(stored)) editor=stored; } catch {}
  $('referenceLayout').value=editor;
  const inset=layout.reference_inset_mm ?? layout.reference_centres_mm['0'][0];
  form.referenceInset.value=Number.isFinite(inset) ? inset : 50;
  syncLayoutEditor();
  $('layoutError').textContent = ''; $('settings').showModal();
};
function cornerCoordinates(width,depth,inset) {
  if (![width,depth,inset].every(Number.isFinite) || inset<0 || width<=2*inset || depth<=2*inset) return null;
  return [[inset,inset],[width-inset,inset],[width-inset,depth-inset],[inset,depth-inset]];
}
function syncLayoutEditor() {
  const form=$('layoutForm').elements,simple=form.referenceLayout.value==='l_shape',automatic=form.referenceLayout.value==='corners';
  $('lGuide').hidden=!simple;
  $('advancedLayout').hidden=simple;
  for (const name of ['lHorizontalCm','lDepthCm','lMarkerCm']) {form[name].disabled=!simple;form[name].required=simple;}
  // Inactive fields must not prevent submission of the other measurement method.
  for (const control of $('advancedLayout').querySelectorAll('input')) control.disabled=simple;
  $('applyLayout').textContent=simple ? '保存并开始三牌定位' : '应用标定';
  $('layoutError').textContent='';
  if (simple) {
    try {
      const next=readLShape();
      $('lSummary').textContent=`已记录：左右 ${next.table_width_mm/10} cm，前后 ${next.table_depth_mm/10} cm。ID 0 为起点，程序替你计算位置。`;
    } catch { $('lSummary').textContent='量黑框中心到黑框中心，不量纸边，不需要计算 X/Y。'; }
    return;
  }
  $('insetLabel').hidden=!automatic;
  for(let i=0;i<4;i++) for(const axis of ['x','y']) form[`${axis}${i}`].readOnly=automatic;
  form.referenceInset.required=automatic;
  form.referenceInset.disabled=!automatic;
  if (!automatic) { $('cornerLayoutHint').textContent='从同一桌角量到各码黑框中心；X 向右，Y 向远侧。';return; }
  const coordinates=cornerCoordinates(Number(form.width.value),Number(form.depth.value),Number(form.referenceInset.value));
  $('layoutError').textContent=coordinates ? '' : '桌面长、深必须大于码中心距边距离的两倍；请检查长宽或减小距边距离。';
  $('cornerLayoutHint').textContent='四角坐标已按长、深及距边距离自动更新。请按这些中心位置摆放纸牌。';
  if(coordinates) coordinates.forEach(([x,y],i)=>{form[`x${i}`].value=x;form[`y${i}`].value=y;});
}
$('referenceLayout').onchange=()=>{
  syncLayoutEditor();
  try { localStorage.setItem(editorStorageKey,$('referenceLayout').value); } catch {}
};
for(const name of ['width','depth','referenceInset','lHorizontalCm','lDepthCm','lMarkerCm']) $('layoutForm').elements[name].addEventListener('input',syncLayoutEditor);
$('saveLRecord').onclick=()=>{
  try {
    const next=readLShape();
    const text=[ 'FYP · L 形三牌测量记录',`记录时间：${new Date().toLocaleString('zh-CN')}`,'',
      `A｜ID 0 到 ID 1，左右中心间距：${next.table_width_mm/10} cm`,
      `B｜ID 1 到 ID 2，前后中心间距：${next.table_depth_mm/10} cm`,
      `参照牌黑框边长：${next.reference_marker_size_mm/10} cm（不含白边）`,'',
      '摆放：ID 0 在近左，ID 1 在近右，ID 2 在远右，三张牌摆成直角 L。',
      '全部平放，图案上边统一朝远侧。量黑框中心到中心，保留白边。',
      'ID 0 中心是起点；ID 4 在区域内移动；ID 3 不参与此方法。',
      '这两段定义三牌测试区域，不是整张桌面的长宽。',
      '保存记录文件不会应用标定；返回页面点击“保存并开始三牌定位”。',
      '位置显示厘米；CSV 的毫米列仍保存毫米数据。',
      '手机位置、焦段或摆牌变化后需要复核记录。',''].join('\n');
    download(new Blob(['\ufeff',text],{type:'text/plain;charset=utf-8'}),`三牌测量记录_${Date.now()}.txt`);
    $('layoutError').textContent='';
  } catch(error) { $('layoutError').textContent=error.message; }
};
$('cancelSettings').onclick = () => $('settings').close();
async function validateLayout(next) {
  const scratch = document.createElement('canvas'); scratch.width = 8; scratch.height = 8;
  const response = await fetch('/api/frame',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({layout:next,image:scratch.toDataURL('image/jpeg'),detect_objects:false})});
  const value = await response.json(); if (!response.ok) throw new Error(value.error);
}
$('layoutForm').onsubmit = async (event) => {
  event.preventDefault(); const form = event.target.elements;
  try {
    const simple=form.referenceLayout.value==='l_shape';
    const next=simple ? readLShape() : {table_width_mm:Number(form.width.value),table_depth_mm:Number(form.depth.value),target_id:4,reference_centres_mm:{},
      allow_three_references:form.allowThree.checked,reference_marker_size_mm:Number(form.markerSize.value),
      reference_layout_mode:form.referenceLayout.value,reference_inset_mm:form.referenceLayout.value==='corners' ? Number(form.referenceInset.value) : null};
    if(!simple) {
      if(form.referenceLayout.value==='corners' && !cornerCoordinates(next.table_width_mm,next.table_depth_mm,next.reference_inset_mm)) {syncLayoutEditor();return;}
      for(let i=0;i<4;i++) next.reference_centres_mm[i]=[Number(form[`x${i}`].value),Number(form[`y${i}`].value)];
    }
    await validateLayout(next);
    const hasFrame=Boolean(lastResult);
    stopRecording(); layout=next;
    if(simple) coordinateMode='table';
    epoch++;lastTime=-1;resetData();
    let saved=false;
    try {
      localStorage.setItem(layoutStorageKey,JSON.stringify(next));
      localStorage.setItem('arucoCoordinateModeV1',coordinateMode);
      localStorage.setItem(editorStorageKey,form.referenceLayout.value);
      saved=true;
    } catch {}
    updateModeUI();
    $('settings').close();
    message(`${simple ? '两段距离已记录，已切换到三牌定位。' : '标定已应用。'}${saved ? '记录已保存在当前浏览器。' : '当前浏览器未允许保存，刷新后需重填。'}${simple ? '请同时看清 0、1、2，并移动 ID 4。' : '统计从此处重新开始。'}`);
    if(playing) processFrame(epoch);
    else if(hasFrame) await analyzeCanvas(epoch);
  } catch(error) { $('layoutError').textContent=error.message; }
};
window.addEventListener('pagehide',stopSource);
renderMarkerPositions();
updateModeUI();
fetch('/api/layout').then((r) => r.json()).then(async (value) => {
  layout = value;
  try {
    const stored = localStorage.getItem(layoutStorageKey);
    if (stored) { const saved = JSON.parse(stored); await validateLayout(saved); layout = saved;
      message(coordinateMode === 'image' ? '免测量演示已就绪，移动 ID 4 即可；已保留桌面标定供毫米模式使用。' : '已恢复当前浏览器保存的标定。请确认纸牌没有移位。'); }
  } catch { message(coordinateMode === 'image' ? '桌面标定已重置，免测量像素演示仍可直接使用。' : '已回到默认标定；请按当前纸牌的实测位置重新填写。','error'); }
  updateModeUI();
  renderMarkerPositions();
  drawMap(null);
}).catch((error) => message(error.message,'error'));
