import ast
import re
from pathlib import Path

MIGRATION_PATH = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_initial.py"


def _source() -> str:
    return MIGRATION_PATH.read_text()


def test_migration_is_valid_python():
    ast.parse(_source())


def test_foreign_keys_reference_earlier_tables():
    src = _source()
    blocks = re.findall(r'op\.execute\("""(CREATE TABLE.*?)"""\)', src, re.S)
    created: list[str] = []
    for block in blocks:
        name = re.match(r"CREATE TABLE (\w+)", block).group(1)
        for ref in re.findall(r"REFERENCES (\w+)", block):
            assert ref in created, f"{name} references {ref} before it's created"
        created.append(name)
    assert len(created) == 18
