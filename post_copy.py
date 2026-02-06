#!/usr/bin/env python3
"""Post-copy script for the KBase JupyterLab extension overlay.

Modifies pyproject.toml to switch from the jupyterlab extension template's
hatch-nodejs-version setup to hatch-vcs, and removes incompatible files.

Usage: python post_copy.py <python_name>
"""

import os
import re
import sys
from pathlib import Path


def modify_pyproject(path: Path, python_name: str) -> None:
    """Modify pyproject.toml for hatch-vcs workflow."""
    content = path.read_text()

    # Replace hatch-nodejs-version with hatch-vcs in build-system requires
    content = re.sub(
        r'"hatch-nodejs-version>=[\d.]+"',
        '"hatch-vcs>=0.4.0"',
        content,
    )

    # Change version source from nodejs to vcs
    content = re.sub(
        r'\[tool\.hatch\.version\]\nsource = "nodejs"',
        '[tool.hatch.version]\nsource = "vcs"',
        content,
    )

    # Add raw-options for local_scheme if not present
    if "local_scheme" not in content:
        content = re.sub(
            r'(\[tool\.hatch\.version\]\nsource = "vcs")',
            r'\1\n\n[tool.hatch.version.raw-options]\nlocal_scheme = "no-local-version"',
            content,
        )

    # Add version hook for _version.py if not present
    version_hook = f'[tool.hatch.build.hooks.version]\npath = "{python_name}/_version.py"'
    if "tool.hatch.build.hooks.version" not in content:
        # Insert before jupyter-builder hook
        content = content.replace(
            "[tool.hatch.build.hooks.jupyter-builder]",
            f"{version_hook}\n\n[tool.hatch.build.hooks.jupyter-builder]",
        )

    # Remove jupyter-releaser sections
    content = re.sub(
        r'\[tool\.jupyter-releaser\.options\].*?(?=\[|\Z)',
        '',
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r'\[tool\.jupyter-releaser\.hooks\].*?(?=\[|\Z)',
        '',
        content,
        flags=re.DOTALL,
    )

    # Bump requires-python to >=3.10
    content = re.sub(
        r'requires-python = ">=3\.\d+"',
        'requires-python = ">=3.10"',
        content,
    )

    # Remove Python 3.8 and 3.9 classifiers
    content = re.sub(
        r'\s*"Programming Language :: Python :: 3\.[89]",?\n',
        '\n',
        content,
    )

    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    path.write_text(content)


def modify_init(python_name: str) -> None:
    """Update __init__.py to import from _version.py with fallback."""
    init_path = Path(python_name) / "__init__.py"
    if not init_path.exists():
        return

    content = init_path.read_text()

    # Check if _version import already exists
    if "_version" in content:
        return

    # Add version import at the top (after any existing imports)
    version_block = '''try:
    from ._version import __version__
except ImportError:
    import warnings
    warnings.warn("Importing '{}' outside a proper installation.")
    __version__ = "dev"
'''.format(python_name)

    # Insert after the first docstring or at the top
    if '"""' in content:
        # Insert after closing docstring
        parts = content.split('"""', 2)
        if len(parts) >= 3:
            content = parts[0] + '"""' + parts[1] + '"""' + '\n\n' + version_block + parts[2]
        else:
            content = version_block + '\n' + content
    else:
        content = version_block + '\n' + content

    init_path.write_text(content)


def delete_files() -> None:
    """Remove files that are incompatible with hatch-vcs workflow."""
    files_to_delete = [
        ".nvmrc",
        "setup.py",
        ".github/workflows/check-release.yml",
        ".github/workflows/prep-release.yml",
        ".github/workflows/publish-release.yml",
        ".github/workflows/enforce-label.yml",
    ]
    for f in files_to_delete:
        path = Path(f)
        if path.exists():
            path.unlink()
            print(f"  Deleted {f}")


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <python_name>")
        sys.exit(1)

    python_name = sys.argv[1]
    print(f"KBase JupyterLab overlay post-copy for: {python_name}")

    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        print("  Modifying pyproject.toml...")
        modify_pyproject(pyproject, python_name)
    else:
        print("  WARNING: pyproject.toml not found!")

    print("  Updating __init__.py...")
    modify_init(python_name)

    print("  Cleaning up incompatible files...")
    delete_files()

    print("  Done! Next steps:")
    print("    uv sync")
    print("    uv run jupyter labextension develop . --overwrite")


if __name__ == "__main__":
    main()
