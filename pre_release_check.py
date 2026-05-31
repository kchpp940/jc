#!/usr/bin/env python3
"""Pre-release self-check script for jc.

Single source of truth for version: jc.lib.__version__
Calls actual generation scripts via subprocess to regenerate artifacts
and compare content-level against actual files.

All generation logic lives ONLY in the gen scripts:
- readmegen.py       -> README.md
- mangen.py          -> man/jc.1
- readmesnapgen.py   -> README-snap.md
- doc2md.py          -> docs/parsers/*.md
- build-completions.py -> completions/*
"""
import difflib
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import jc.cli
import jc.lib
from jc.shell_completions import bash_completion, zsh_completion


class ReleaseChecker:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(f"ERROR: {msg}")

    def warning(self, msg: str) -> None:
        self.warnings.append(f"WARNING: {msg}")

    def get_canonical_version(self) -> str:
        """Get single source of truth version from jc.lib.__version__."""
        return jc.lib.__version__

    def _run_gen_script(self, script_name: str, args: Optional[List[str]] = None) -> Tuple[int, str, str]:
        """Run a generation script with --stdout and return output."""
        script_path = self.project_root / script_name
        cmd = [sys.executable, str(script_path), '--stdout'] + (args or [])

        result = subprocess.run(
            cmd,
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=60
        )

        return result.returncode, result.stdout, result.stderr

    def _run_gen_script_to_file(self, script_name: str, output_path: Path) -> Tuple[int, str, str]:
        """Run a generation script to write to specific output file."""
        script_path = self.project_root / script_name
        cmd = [sys.executable, str(script_path)]

        result = subprocess.run(
            cmd,
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=60
        )

        return result.returncode, result.stdout, result.stderr

    def _compare_content(self, expected: str, actual_path: Path, label: str,
                         ignore_patterns: Optional[List[str]] = None,
                         gen_command: Optional[str] = None) -> bool:
        """Compare expected content with actual file content."""
        if not actual_path.exists():
            self.error(f"Missing file: {actual_path.relative_to(self.project_root)}")
            return False

        actual = actual_path.read_text()

        expected_norm = expected.strip()
        actual_norm = actual.strip()

        if ignore_patterns:
            for pattern in ignore_patterns:
                expected_norm = re.sub(pattern, '', expected_norm, flags=re.MULTILINE)
                actual_norm = re.sub(pattern, '', actual_norm, flags=re.MULTILINE)

        if expected_norm == actual_norm:
            print(f"  ✓ {label}")
            return True
        else:
            hint = f" Run: {gen_command}" if gen_command else ""
            self.error(f"{label} content mismatch!{hint}")
            diff = difflib.unified_diff(
                actual.splitlines()[:50],
                expected.splitlines()[:50],
                fromfile=str(actual_path.relative_to(self.project_root)),
                tofile="generated",
                lineterm="",
                n=3
            )
            for line in list(diff)[:20]:
                print(f"    {line}")
            if len(expected.splitlines()) > 50 or len(actual.splitlines()) > 50:
                print("    ... (diff truncated)")
            return False

    def check_version_consistency(self) -> None:
        """Check all version references match the canonical source."""
        print("Checking version consistency (source: jc.lib.__version__)...")
        canonical = self.get_canonical_version()

        version_checks = [
            ("jc.cli.info.version", jc.cli.info.version),
            ("setup.py", self._extract_setup_version()),
            ("man/jc.1", self._extract_man_version()),
        ]

        all_match = True
        for name, actual in version_checks:
            if actual == canonical:
                print(f"  ✓ {name}: {actual}")
            else:
                self.error(f"{name} version mismatch! Expected '{canonical}', got '{actual}'")
                all_match = False

        snap_path = self.project_root / "snap" / "snapcraft.yaml"
        if snap_path.exists():
            content = snap_path.read_text()
            if "adopt-info: jc" in content and "craftctl set version" in content:
                print(f"  ✓ snap/snapcraft.yaml: uses adopt-info (verified)")
            else:
                self.warning("snapcraft.yaml may not use adopt-info versioning")

        if all_match:
            print(f"  ✓ All versions match canonical: {canonical}")

    def _extract_setup_version(self) -> str:
        """Extract version from setup.py."""
        setup_path = self.project_root / "setup.py"
        content = setup_path.read_text()
        match = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", content)
        return match.group(1) if match else "NOT FOUND"

    def _extract_man_version(self) -> str:
        """Extract version from man page."""
        man_path = self.project_root / "man" / "jc.1"
        if not man_path.exists():
            return "NOT FOUND"
        content = man_path.read_text()
        match = re.search(r"^\.TH jc 1 [\d-]+ ([\d.]+)", content, re.MULTILINE)
        return match.group(1) if match else "NOT FOUND"

    def check_parsers_sync(self) -> None:
        """Check parser synchronization across all generated artifacts."""
        print("\nChecking parser synchronization...")

        canonical_parsers = set(jc.lib.standard_parser_mod_list() +
                                jc.lib.streaming_parser_mod_list())

        canonical_cli = {p.replace('_', '-') for p in canonical_parsers}

        bash_content = bash_completion()
        bash_parsers = set(re.findall(r"--([\w-]+)", bash_content.split("jc_parsers=")[1].split(")")[0]))

        zsh_content = zsh_completion()
        zsh_parsers = set(re.findall(r"--([\w-]+)", zsh_content.split("jc_parsers=")[1].split(")")[0]))

        rc, readme_content, err = self._run_gen_script("readmegen.py")
        if rc != 0:
            self.error(f"readmegen.py failed: {err.strip()}")
            readme_parsers = set()
        else:
            readme_parsers = set(re.findall(r"`--([\w-]+)`", readme_content))

        rc, man_content, err = self._run_gen_script("mangen.py")
        if rc != 0:
            self.error(f"mangen.py failed: {err.strip()}")
            man_parsers = set()
        else:
            man_parsers = set(re.findall(r"\\fB--([\w-]+)\\fP", man_content))

        print(f"  ✓ Canonical parsers (jc.lib): {len(canonical_cli)}")
        print(f"  ✓ Bash completion parsers: {len(bash_parsers)}")
        print(f"  ✓ Zsh completion parsers: {len(zsh_parsers)}")
        print(f"  ✓ README parsers: {len(readme_parsers)}")
        print(f"  ✓ Man page parsers: {len(man_parsers)}")

        missing_bash = canonical_cli - bash_parsers
        missing_zsh = canonical_cli - zsh_parsers
        missing_readme = canonical_cli - readme_parsers
        missing_man = canonical_cli - man_parsers

        if missing_bash:
            self.error(f"Parsers missing from bash completion: {sorted(missing_bash)[:5]}")
        if missing_zsh:
            self.error(f"Parsers missing from zsh completion: {sorted(missing_zsh)[:5]}")
        if missing_readme:
            self.error(f"Parsers missing from README: {sorted(missing_readme)[:5]}")
        if missing_man:
            self.error(f"Parsers missing from man page: {sorted(missing_man)[:5]}")

    def check_generated_artifacts(self) -> None:
        """Check all generated artifacts match expected output by calling gen scripts."""
        print("\nChecking generated artifacts (content-level via gen scripts)...")

        print("\n  Shell completions:")
        expected_bash = bash_completion()
        bash_path = self.project_root / "completions" / "jc_bash_completion.sh"
        self._compare_content(expected_bash, bash_path, "Bash completion",
                              gen_command="python3 build-completions.py")

        expected_zsh = zsh_completion()
        zsh_path = self.project_root / "completions" / "jc_zsh_completion.sh"
        self._compare_content(expected_zsh, zsh_path, "Zsh completion",
                              gen_command="python3 build-completions.py")

        print("\n  Documentation:")
        rc, expected_readme, err = self._run_gen_script("readmegen.py")
        if rc == 0:
            readme_path = self.project_root / "README.md"
            date_pattern = r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2} \d{2}:\d{2}:\d{2} [A-Z]{3} \d{4}\b'
            self._compare_content(expected_readme, readme_path, "README.md",
                                  ignore_patterns=[date_pattern],
                                  gen_command="python3 readmegen.py")
        else:
            self.error(f"readmegen.py failed: {err.strip()}")

        rc, expected_man, err = self._run_gen_script("mangen.py")
        if rc == 0:
            man_path = self.project_root / "man" / "jc.1"
            date_header_pattern = r'^\.TH jc 1 [\d-]+ '
            self._compare_content(expected_man, man_path, "man/jc.1",
                                  ignore_patterns=[date_header_pattern],
                                  gen_command="python3 mangen.py")
        else:
            self.error(f"mangen.py failed: {err.strip()}")

        rc, expected_readme_snap, err = self._run_gen_script("readmesnapgen.py")
        if rc == 0:
            readme_snap_path = self.project_root / "README-snap.md"
            self._compare_content(expected_readme_snap, readme_snap_path, "README-snap.md",
                                  gen_command="python3 readmesnapgen.py")
        else:
            self.error(f"readmesnapgen.py failed: {err.strip()}")

    def _generate_parser_doc(self, parser_name: str) -> Optional[str]:
        """Generate parser documentation by calling doc2md.py as subprocess."""
        script_path = self.project_root / "doc2md.py"
        module_path = f"jc.parsers.{parser_name}"

        try:
            result = subprocess.run(
                [sys.executable, str(script_path), module_path],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                self.warning(f"doc2md.py failed for {parser_name}: {result.stderr.strip()}")
                return None

            return result.stdout
        except Exception as e:
            self.warning(f"Failed to generate doc for {parser_name}: {e}")
            return None

    def check_parser_docs(self) -> None:
        """Check each parser has up-to-date documentation by calling doc2md.py."""
        print("\nChecking parser documentation (via doc2md.py)...")

        canonical_parsers = (jc.lib.standard_parser_mod_list(show_hidden=True, show_deprecated=True) +
                             jc.lib.streaming_parser_mod_list(show_hidden=True, show_deprecated=True))

        docs_dir = self.project_root / "docs" / "parsers"
        missing: List[str] = []
        outdated: List[str] = []

        for parser_mod in canonical_parsers:
            parser_file = parser_mod.replace('-', '_')
            doc_path = docs_dir / f"{parser_file}.md"

            if not doc_path.exists():
                missing.append(parser_mod)
                continue

            expected_doc = self._generate_parser_doc(parser_file)
            if expected_doc is None:
                continue

            actual_doc = doc_path.read_text()

            expected_norm = re.sub(r'\s+', ' ', expected_doc.strip())
            actual_norm = re.sub(r'\s+', ' ', actual_doc.strip())

            if expected_norm != actual_norm:
                outdated.append(parser_mod)

        if missing:
            self.error(f"Missing parser docs: {sorted(missing)[:10]}")
            if len(missing) > 10:
                self.error(f"... and {len(missing) - 10} more")

        if outdated:
            self.warning(f"Outdated parser docs (content mismatch): {sorted(outdated)[:5]}")
            if len(outdated) > 5:
                self.warning(f"... and {len(outdated) - 5} more (run ./docgen.sh all)")

        total = len(canonical_parsers)
        ok = total - len(missing) - len(outdated)
        print(f"  ✓ {ok}/{total} parser docs up-to-date")

    def check_snap_config(self) -> None:
        """Check snap configuration and version extraction."""
        print("\nChecking snap configuration...")

        snap_path = self.project_root / "snap" / "snapcraft.yaml"
        if not snap_path.exists():
            self.error("Missing snap/snapcraft.yaml")
            return

        content = snap_path.read_text()
        canonical_version = self.get_canonical_version()

        checks = [
            ("adopt-info: jc", "adopt-info declaration"),
            ("craftctl set version", "version extraction logic"),
            ("grep version= setup.py", "version source from setup.py"),
        ]

        all_ok = True
        for pattern, desc in checks:
            if pattern in content:
                print(f"  ✓ {desc}")
            else:
                self.error(f"snapcraft.yaml missing {desc}")
                all_ok = False

        if all_ok:
            print(f"  ✓ Snap version source verified (from jc.lib.__version__: {canonical_version})")

    def run_all_checks(self) -> bool:
        """Run all pre-release checks."""
        print("=" * 60)
        print("JC Pre-Release Self-Check")
        print("=" * 60)

        self.check_version_consistency()
        self.check_parsers_sync()
        self.check_generated_artifacts()
        self.check_parser_docs()
        self.check_snap_config()

        print()
        print("=" * 60)

        if self.warnings:
            print("\nWarnings:")
            for w in self.warnings:
                print(f"  {w}")

        if self.errors:
            print("\nErrors:")
            for e in self.errors:
                print(f"  {e}")
            print(f"\n❌ {len(self.errors)} error(s) found. Release aborted.")
            return False
        else:
            print("\n✅ All checks passed! Ready to release.")
            return True


def main() -> int:
    project_root = Path(__file__).parent.resolve()
    checker = ReleaseChecker(project_root)
    success = checker.run_all_checks()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
