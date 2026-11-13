import re
from pathlib import Path

from scripts.prompt_format import SYSTEM_RULES

DOC_PATH = Path(__file__).parent.parent / "docs" / "prompt_format.md"


def test_system_rules_match_doc():
    """Les règles du code doivent être identiques à celles du document."""
    doc = DOC_PATH.read_text(encoding="utf-8")
    section = doc.split("## Règles système")[1].split("## Exemple complet")[0]
    doc_rules = re.search(r"```text\n(.*?)```", section, re.S).group(1).strip()
    assert SYSTEM_RULES == doc_rules