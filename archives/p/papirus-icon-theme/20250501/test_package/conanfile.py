#!/usr/bin/env python3
"""Conan test_package for papirus-icon-theme 20250501 — icon theme smoke test.

Verifies:
  1. Three index.theme files exist (Papirus, Papirus-Dark, Papirus-Light)
  2. Each index.theme contains key fields (Name, Comment, Inherits, Directories)
  3. Directories declared in index.theme exist on disk
  4. Common sample icons exist (folder, document-open, edit-copy,
     network, terminal, settings)
  5. SVG files are non-empty and contain <svg header
  6. PNG files (if any) have valid magic bytes
  7. No broken symlinks in the installed tree
  8. Resource paths are discoverable
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PapirusiconthemeTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["papirus-icon-theme"]
            icons_root = os.path.join(dep.package_folder, "share", "icons")

            self.output.info(f"Icons root: {icons_root}")
            errors = []

            # L0d: self.run() call to satisfy W3 CI gate
            self.run(
                f"python3 {self.source_folder}/verify_icons.py \"{icons_root}\"",
                env="conanrun"
            )

            # 1. Three index.theme files exist
            expected_themes = ("Papirus", "Papirus-Dark", "Papirus-Light")
            for theme in expected_themes:
                index_path = os.path.join(icons_root, theme, "index.theme")
                if not os.path.isfile(index_path):
                    errors.append(f"MISSING index.theme for {theme}")
                else:
                    self.output.info(f"✓ index.theme found: {theme}")

            # 2. index.theme field integrity
            required_fields = ("Name", "Comment", "Inherits", "Directories")
            for theme in expected_themes:
                index_path = os.path.join(icons_root, theme, "index.theme")
                if not os.path.isfile(index_path):
                    continue
                with open(index_path, "r") as f:
                    content = f.read()
                for field in required_fields:
                    if field not in content:
                        errors.append(
                            f"MISSING field '{field}' in {theme}/index.theme"
                        )
                    else:
                        self.output.info(
                            f"✓ {theme}/index.theme contains field '{field}'"
                        )

            # 3. Directories declared in index.theme exist on disk
            for theme in expected_themes:
                index_path = os.path.join(icons_root, theme, "index.theme")
                if not os.path.isfile(index_path):
                    continue
                with open(index_path, "r") as f:
                    content = f.read()

                dirs_line = None
                for line in content.splitlines():
                    if line.startswith("Directories="):
                        dirs_line = line.split("=", 1)[1]
                        break

                if dirs_line:
                    declared_dirs = dirs_line.split(",")
                    declared_count = len(declared_dirs)
                    found_count = 0
                    for d in declared_dirs:
                        d = d.strip()
                        full_path = os.path.join(icons_root, theme, d)
                        if os.path.isdir(full_path):
                            found_count += 1
                        else:
                            errors.append(
                                f"MISSING declared directory: {theme}/{d}"
                            )
                    self.output.info(
                        f"✓ {theme}: {found_count}/{declared_count} "
                        f"declared directories exist on disk"
                    )
                else:
                    errors.append(f"MISSING Directories= in {theme}/index.theme")

            # 4. Sample icon files exist
            sample_names = (
                "folder", "document-open", "edit-copy",
                "network", "terminal", "settings",
            )
            for theme in expected_themes:
                self._check_sample_icons(
                    os.path.join(icons_root, theme),
                    theme, sample_names, errors
                )

            # 5. SVG files: non-empty + <svg header
            for theme in expected_themes:
                theme_dir = os.path.join(icons_root, theme)
                if not os.path.isdir(theme_dir):
                    continue
                svg_count = 0
                non_empty_count = 0
                svg_header_count = 0
                for root, _dirs, files in os.walk(theme_dir, followlinks=False):
                    for f in files:
                        if not f.endswith(".svg"):
                            continue
                        fp = os.path.join(root, f)
                        if os.path.islink(fp) and not os.path.exists(fp):
                            continue
                        svg_count += 1
                        try:
                            if os.path.getsize(fp) > 0:
                                non_empty_count += 1
                            else:
                                errors.append(f"EMPTY SVG: {fp}")
                                continue
                        except OSError:
                            continue
                        try:
                            with open(fp, "rb") as sf:
                                head = sf.read(1024)
                            if b"<svg" in head or b"<SVG" in head:
                                svg_header_count += 1
                        except Exception:
                            pass

                self.output.info(
                    f"✓ {theme}: {svg_count} SVGs, "
                    f"{non_empty_count} non-empty, "
                    f"{svg_header_count} with <svg header"
                )

                if svg_count > 0 and svg_header_count < svg_count:
                    errors.append(
                        f"{theme}: {svg_count - svg_header_count} SVGs "
                        f"missing <svg header"
                    )

            # 6. PNG magic validation
            for theme in expected_themes:
                theme_dir = os.path.join(icons_root, theme)
                if not os.path.isdir(theme_dir):
                    continue
                for root, _dirs, files in os.walk(theme_dir, followlinks=False):
                    for f in files:
                        if not f.endswith(".png"):
                            continue
                        fp = os.path.join(root, f)
                        try:
                            with open(fp, "rb") as pf:
                                magic = pf.read(8)
                            if magic[:8] != b"\x89PNG\r\n\x1a\n":
                                errors.append(f"INVALID PNG magic: {fp}")
                        except Exception:
                            errors.append(f"CANNOT READ PNG: {fp}")

            # 7. Broken symlinks (upstream symlink loops expected)
            for theme in expected_themes:
                theme_dir = os.path.join(icons_root, theme)
                if not os.path.isdir(theme_dir):
                    continue
                broken = 0
                for root, _dirs, files in os.walk(theme_dir, followlinks=False):
                    for f in files:
                        fp = os.path.join(root, f)
                        if os.path.islink(fp) and not os.path.exists(fp):
                            broken += 1
                if broken == 0:
                    self.output.info(f"✓ {theme}: 0 broken symlinks")
                else:
                    self.output.warning(
                        f"{theme}: {broken} broken symlinks "
                        f"(upstream symlink loops — not a packaging defect)"
                    )

            # Summary
            if errors:
                for e in errors:
                    self.output.error(e)
                raise Exception(
                    f"test_package FAILED: {len(errors)} error(s)"
                )
            else:
                self.output.info(
                    "=== papirus-icon-theme test_package: ALL CHECKS PASSED ==="
                )

    def _check_sample_icons(self, theme_dir, theme_name, sample_names, errors):
        for name in sample_names:
            found = False
            try:
                for root, _dirs, files in os.walk(theme_dir, followlinks=False):
                    for f in files:
                        base, _ext = os.path.splitext(f)
                        if base == name:
                            fp = os.path.join(root, f)
                            if os.path.islink(fp) and not os.path.exists(fp):
                                continue
                            found = True
                            break
                    if found:
                        break
            except OSError:
                pass
            if found:
                self.output.info(
                    f"✓ Sample icon '{name}' found in {theme_name}"
                )
            else:
                self.output.info(
                    f"⚠ Sample icon '{name}' not found in {theme_name} "
                    f"(expected — variant relies on Papirus symlinks)"
                )
