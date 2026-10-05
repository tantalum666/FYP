from pathlib import Path
import subprocess
import sys

renderer = Path('/Users/tantalum/.codex/plugins/cache/openai-primary-runtime/documents/26.909.12148/skills/documents/render_docx.py')
subprocess.run([sys.executable, str(renderer), *sys.argv[1:], '--emit_pdf'], check=True)
