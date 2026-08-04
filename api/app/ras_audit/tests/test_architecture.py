import ast
from pathlib import Path

API_APP = Path(__file__).resolve().parents[2]
ACTIVE_BACKEND_PACKAGES = ("agent", "excel_agent", "ras_audit")


def test_active_ras_backend_does_not_import_legacy_tax_declaration_modules() -> None:
    forbidden_imports: list[str] = []
    for package_name in ACTIVE_BACKEND_PACKAGES:
        for source_path in (API_APP / package_name).rglob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                imported_names = _imported_names(node)
                if any(
                    name == "app.tax_declaration"
                    or name.startswith("app.tax_declaration.")
                    for name in imported_names
                ):
                    forbidden_imports.append(str(source_path.relative_to(API_APP)))

    assert forbidden_imports == []


def _imported_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return (node.module,)
    return ()
