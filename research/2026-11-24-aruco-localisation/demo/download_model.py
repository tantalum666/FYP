"""Fetch the documented YOLOX model once and verify it before use."""
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def ensure_model(root=ROOT):
    folder = root / 'models'
    source = json.loads((folder / 'model-source.json').read_text())
    target = folder / 'yolox_s.onnx'
    expected = source['sha256']
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        return target
    if not source['url'].startswith('https://huggingface.co/opencv/opencv_zoo/resolve/'):
        raise ValueError('Unexpected model source; inspect model-source.json.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, suffix='.part', delete=False) as file:
            temporary = Path(file.name)
            digest, size = hashlib.sha256(), 0
            with urlopen(source['url'], timeout=120) as response:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > source['bytes']:
                        raise ValueError('Downloaded model exceeds expected size.')
                    digest.update(chunk)
                    file.write(chunk)
        if size != source['bytes'] or digest.hexdigest() != expected:
            raise ValueError('Model size or SHA256 differs; original file preserved.')
        temporary.replace(target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    print(f'Model verified: {ensure_model()}')
