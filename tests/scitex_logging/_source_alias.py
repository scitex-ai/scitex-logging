"""Owned source aliases shared by hook and linter controls."""


def _alias(root, kind):
    source = root / "src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n")
    if kind == "directory":
        (root / "apps").symlink_to(source.parent, target_is_directory=True)
        return root / "apps/module.py", source
    alias = root / "legacy.py"
    alias.symlink_to(source)
    return alias, source
