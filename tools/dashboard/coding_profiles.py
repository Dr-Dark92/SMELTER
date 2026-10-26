"""Small task-specific ECC profiles; instruction selection never grants tools."""
import json
from pathlib import Path
import re


def automatic_coding_enabled(root):
    from python_tools import _plain_path
    path = _plain_path(Path(root) / '.smelter/ecc-bridge.json')
    if not path.is_file():
        return False
    if path.stat().st_size > 32768:
        raise ValueError('Invalid ECC bridge activation record')
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1 or type(data.get('automatic_coding')) is not bool:
        raise ValueError('Invalid ECC bridge activation record')
    return data.get('enabled') is True and data['automatic_coding']


def coding_candidates(prompt):
    text = prompt.lower()
    if re.search(r'\b(review|audit)\b', text):
        return ['ecc-code-review', 'ecc-test-review']
    if re.search(r'\b(debug|syntax|traceback|import|module loading|path error|stuck|looping)\b', text):
        return ['smelter-debugging', 'ecc-verification-loop']
    if re.search(r'\bcpp\b|c\+\+|\.cpp\b|\b(native code|asi plugin|linker)\b', text):
        return ['ecc-cpp-standards', 'ecc-cpp-testing']
    if re.search(r'^\s*(plan|design)\b|\b(implementation plan|coding architecture)\b', text):
        return ['ecc-planner', 'ecc-retrieval']
    if re.search(r'\b(raptor|aggro|gameplay|npc|dinosaur|taming|cooldown)\b', text):
        return ['gameplay-testing', 'ecc-tdd-workflow']
    if re.search(r'\b(test quality|test coverage|verify code|validate code|run tests)\b', text):
        return ['ecc-verification-loop', 'ecc-test-review']
    if re.search(r'\b(implement|refactor|coding|code|script|fix|repair)\b', text):
        return ['ecc-tdd-workflow', 'ecc-verification-loop']
    return []
