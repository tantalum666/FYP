"""Verify native art bytes and preserve provenance; does not edit pixels."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import struct
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
ART = ROOT / 'design/desk-companion/characters/2026-10-12-a1-turnaround-details'


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def local(path):
    return str(Path(path).relative_to(ROOT))


def png_info(path):
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    return (*struct.unpack('>II', data[16:24]), len(data), sha256(data).hexdigest())


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


titles = {
    'A1-T01': '正面全身', 'A1-T02': '人物左侧面', 'A1-T03': '背面全身',
    'A1-T04': '人物右侧面', 'A1-T05': '前斜视（角度较浅）',
    'A1-T06': '后斜视（角度较浅）', 'A1-D01': '脸部与发扣',
    'A1-D02': '后发与发扣侧后', 'A1-D03': '上衣、腰带与叠裙',
    'A1-D04': '短靴与裤袜材质',
}
root_notes = {
    'A1-T01': ['正面平衡站姿；发扣在人物左侧／画面右；完整头手鞋。', '手臂仅小幅分离，低于目标15度；衣物折面稍简化。'],
    'A1-T02': ['鼻子朝画面左，近侧发扣位置正确；头到鞋完整，远侧手自然遮挡。', '后发比正面稍饱满，侧脸轮廓是本轮补充推演。'],
    'A1-T03': ['完整正背面无回头；发扣在画面左；后发至腰上，短外套与裹裙连续。', '后发分组、外套中缝和裙装后片为新增设计提案。'],
    'A1-T04': ['鼻子朝画面右；左发扣在远侧被遮住，没有搬到右侧；头到鞋完整。', '远侧手和部分远侧鞋被自然侧视遮挡，不能分别检查。'],
    'A1-T05': ['前左斜视；完整头手鞋，发扣在近侧，衣物延续原稿。', '实际角度较浅，脸接近正面，不标为精确45度。'],
    'A1-T06': ['最终稿头身同向朝远处；无眼口，左发扣近侧，完整头手鞋；延续T03。', '实际比目标45度更接近正背面。首稿头身方向不一致，由工作代理拒绝并保留。'],
    'A1-D01': ['完整头顶、灰蓝眉眼、概括鼻口及左侧开环发扣／耳钉清楚。', '1254×1254原生近景，头肩取景符合用途。'],
    'A1-D02': ['完整头顶与后发尾、近侧左发扣清楚；后发长度和分束沿用T03。', '侧脸只露窄边；取景稍延伸至上裙和袖部，后背缝更明确。'],
    'A1-D03': ['肩领、外套袖口、腰带小五金和斜向叠裙完整可读；头部按细节用途排除。', '接近正面，取景下缘比目标略低至更多大腿。'],
    'A1-D04': ['两条小腿和两只短靴完整；带扣、鞋底与方跟清楚，裤袜与靴子材质区分。', '1254×1254；鞋头分片和光泽比原V4更明确。'],
}
jobs = json.loads((ART / 'generation-jobs.json').read_text())
assert len(jobs) == 10
items, review = [], []
for index, job in enumerate(jobs, 1):
    receipt_path = Path(job['receipt_path'])
    receipt = json.loads(receipt_path.read_text())
    output = Path(job['output_path'])
    assert receipt['job_id'] == job['id']
    assert receipt['workspace_output_path'] == str(output)
    w, h, size, sh = png_info(output)
    assert (w, h, size, sh) == tuple(receipt[k] for k in ('width', 'height', 'bytes', 'sha256'))
    native = Path(receipt['native_original_path'])
    assert native.read_bytes() == output.read_bytes()
    assert digest(job['prompt_path']) == job['prompt_sha256']
    assert digest(receipt['prompt_path']) == receipt['prompt_sha256']
    assert receipt['reference_paths'] == job['reference_paths']
    assert [digest(p) for p in receipt['reference_paths']] == receipt['reference_sha256s']
    assert receipt['visual_check_passed'] is True
    assert 1 <= receipt['attempt_count'] <= 2
    item = {
        'id': job['id'], 'title_zh': titles[job['id']], 'kind': job['kind'],
        'image': output.name, 'width': w, 'height': h, 'bytes': size, 'sha256': sh,
        'native_original_path': str(native), 'receipt': receipt_path.name,
        'specification_prompt': str(Path(job['prompt_path']).relative_to(ART)),
        'specification_prompt_sha256': job['prompt_sha256'],
        'actual_prompt': str(Path(receipt['prompt_path']).relative_to(ART)),
        'actual_prompt_sha256': receipt['prompt_sha256'],
        'references': [{'path': local(p), 'sha256': digest(p)} for p in receipt['reference_paths']],
        'depends_on': job['depends_on'], 'attempt_count': receipt['attempt_count'],
        'worker_observations': receipt['visual_observations'],
        'deviations': receipt['deviations'], 'root_view_image_review': root_notes[job['id']],
        'status': 'retained_2d_reference', 'pixel_postprocessing': False,
        'copy_verified_byte_identical': True,
    }
    items.append(item)
    review.append({
        'id': job['id'], 'index': index, 'title': job['id'] + ' · ' + titles[job['id']],
        'src': output.name, 'href': output.name, 'imagePath': str(output),
        'prompt': Path(receipt['prompt_path']).read_text(),
        'routeName': '内置ImageGen · A1原服装参考',
    })

rejected_path = ART / 'a1-t06-back-three-quarter.attempt1-rejected.receipt.json'
rejected = json.loads(rejected_path.read_text())
assert rejected['visual_check_passed'] is False
assert Path(rejected['workspace_output_path']).read_bytes() == Path(rejected['native_original_path']).read_bytes()
assert png_info(rejected['workspace_output_path']) == tuple(rejected[k] for k in ('width', 'height', 'bytes', 'sha256'))
assert digest(rejected['prompt_path']) == rejected['prompt_sha256']
assert [digest(p) for p in rejected['reference_paths']] == rejected['reference_sha256s']
now = datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat()
manifest = {
    'group': 'Group 2', 'date': '2026-10-12', 'scope': 'A1 2D turnaround and details',
    'character_identity_user_selected': True, 'default_outfit_user_selected': False,
    'working_outfit': 'Original A1 V4; engineering continuity choice only',
    'route': 'built-in ImageGen', 'source_pixel_postprocessing': False,
    'accepted_image_count': 10, 'full_body_count': 6, 'detail_count': 4,
    'native_call_count': sum(i['attempt_count'] for i in items),
    'all_ten_accepted_images_actually_viewed_by_root': True,
    'dependency_review': 'T01 reviewed before side/back; T03 reviewed before T06/D02',
    'unseen_back_geometry': 'New inferred design proposal, not recovered 3D geometry or user approval',
    'angle_limit': 'T05 and T06 are shallow oblique views, not measured 45-degree projections',
    'items': items,
    'rejected_attempts': [{'job_id': 'A1-T06', 'image': Path(rejected['workspace_output_path']).name,
                           'receipt': rejected_path.name, 'sha256': rejected['sha256'],
                           'reason': rejected['deviations'], 'root_viewed': False}],
    'completed_at': now,
}
assert manifest['native_call_count'] == 11
write(ART / 'manifest.json', manifest)
write(ART / 'review-manifest.json', review)
write(QA / 'image-validation.json', manifest)
route = json.loads((QA / 'tool-route.json').read_text())
route.update({
    'rear_reference_reviewed_before_T06_D02': True, 'accepted_images': 10,
    'native_calls': 11, 'worker_terminal_results_consumed': True,
    'interrupt_confirmed_terminal_workers': 3, 'worker_handles_destroyed': False,
    'handle_destruction_api_available': False, 'static_review_renderer_used': True,
    'updated_at': now,
})
write(QA / 'tool-route.json', route)
print(json.dumps({'accepted': 10, 'full_body': 6, 'details': 4, 'calls': 11,
                  'source_bytes_unchanged': True, 'metadata_verified': True}, ensure_ascii=False))
