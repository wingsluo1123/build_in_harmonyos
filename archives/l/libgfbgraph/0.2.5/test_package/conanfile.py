#!/usr/bin/env python3
"""消费者测试：链接已安装的 libgfbgraph-0.2，调用不访问网络的公开 API。"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class LibgfbgraphTestConan(ConanFile):
    _PC_SPACE_SEPARATED_FIELDS = frozenset(
        ("Cflags", "Cflags.private", "Libs", "Libs.private")
    )
    _PC_COMMA_SEPARATED_FIELDS = frozenset(
        ("Requires", "Requires.private", "Conflicts")
    )

    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _host_deps(self):
        host = getattr(self.dependencies, "host", None)
        if host is not None:
            return list(host.values())
        return list(self.dependencies.values())

    def _dedupe_pkgconfig_fields(self, lines, filename):
        """Collapse duplicate .pc fields while preserving list-valued entries."""
        out = []
        positions = {}
        for line in lines:
            field, separator, value = line.partition(":")
            if (
                not separator
                or not field
                or not field[0].isalpha()
                or any(not (character.isalnum() or character in "_.-") for character in field)
            ):
                out.append(line)
                continue

            value = value.strip()
            if field not in positions:
                positions[field] = len(out)
                out.append(line)
                continue

            index = positions[field]
            previous = out[index].partition(":")[2].strip()
            if not value or value == previous:
                continue
            if field in self._PC_SPACE_SEPARATED_FIELDS:
                joiner = " "
            elif field in self._PC_COMMA_SEPARATED_FIELDS:
                joiner = ", "
            else:
                raise ConanInvalidConfiguration(
                    "%s has conflicting duplicate %s fields" % (filename, field)
                )
            if value not in previous:
                out[index] = "%s: %s%s%s" % (field, previous, joiner, value)
        return out

    def _append_pkgconfig_field(self, lines, field, value):
        prefix = field + ":"
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                current = line[len(prefix):].split()
                if value not in current:
                    lines[index] = line.rstrip() + " " + value
                return
        lines.append("%s: %s" % (field, value))

    def _rewrite_pkgconfig(self, dest):
        os.makedirs(dest, exist_ok=True)
        for dep in self._host_deps():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            pc_dir = os.path.join(folder, "lib", "pkgconfig")
            if not os.path.isdir(pc_dir):
                continue
            for name in os.listdir(pc_dir):
                if not name.endswith(".pc"):
                    continue
                src = os.path.join(pc_dir, name)
                with open(src, "r", encoding="utf-8", errors="replace") as handle:
                    lines = handle.read().splitlines()
                out = []
                for line in lines:
                    if line.startswith("prefix="):
                        out.append("prefix=%s" % folder)
                    else:
                        out.append(line)
                if name == "goa-1.0.pc":
                    extra = "-I%s/lib/goa-1.0/include" % folder
                    self._append_pkgconfig_field(out, "Cflags", extra)
                out = self._dedupe_pkgconfig_fields(out, name)
                with open(os.path.join(dest, name), "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("\n".join(out) + "\n")
        self._ensure_sqlite3_pc(dest)

    def _sqlite3_dep(self):
        for dep in self._host_deps():
            ref = getattr(dep, "ref", None)
            if ref is not None and getattr(ref, "name", None) == "sqlite3":
                return dep
        return None

    def _ensure_sqlite3_pc(self, dest):
        """消费者 pkg-config 解析 libsoup-3.0 时同样需要 sqlite3.pc。"""
        dest_pc = os.path.join(dest, "sqlite3.pc")
        if os.path.isfile(dest_pc):
            return
        dep = self._sqlite3_dep()
        folder = getattr(dep, "package_folder", None) if dep is not None else None
        if not folder:
            raise ConanInvalidConfiguration(
                "sqlite3/3.49.1 没有包目录，消费者测试无法提供 sqlite3.pc"
            )
        version = str(dep.ref.version)
        body = (
            "prefix=%s\n"
            "exec_prefix=${prefix}\n"
            "libdir=${exec_prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: sqlite3\n"
            "Description: SQLite\n"
            "Version: %s\n"
            "Libs: -L${libdir} -lsqlite3 -ldl -lpthread -lm\n"
            "Cflags: -I${includedir}\n"
        ) % (folder, version)
        with open(dest_pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        self.output.info("wrote sqlite3.pc for %s into %s" % (version, dest))

    def _library_rank(self, path):
        """链接器产物优先。安装到包目录的副本在本机加载器上会被拒绝。"""
        norm = path.replace("\\", "/")
        rank = 0
        if "/.libs/" in norm:
            rank += 8
        if "/build/" in norm or "/build-release/" in norm:
            rank += 4
        return rank

    def _build_tree_libraries(self):
        home = os.environ.get("CONAN_HOME", "")
        root = os.path.join(home, "p", "b") if home else ""
        found = {}
        if not os.path.isdir(root):
            return found
        for dirpath, _dirnames, filenames in os.walk(root):
            norm = dirpath.replace("\\", "/")
            if "/p/lib" in norm or "/runtime-" in norm:
                continue
            for filename in filenames:
                if ".so" not in filename or filename.endswith(".symbols"):
                    continue
                path = os.path.join(dirpath, filename)
                if not os.path.isfile(path):
                    continue
                current = found.get(filename)
                if current is None:
                    found[filename] = path
                    continue
                rank = self._library_rank(path)
                current_rank = self._library_rank(current)
                if rank > current_rank or (
                    rank == current_rank and os.path.getmtime(path) > os.path.getmtime(current)
                ):
                    found[filename] = path
        return found

    def _libdirs(self):
        stage = os.path.join(self.build_folder, "runtime-libs")
        if os.path.isdir(stage):
            shutil.rmtree(stage)
        os.makedirs(stage)
        fresh = self._build_tree_libraries()
        for dep in self._host_deps():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            libdir = os.path.join(folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if ".so" not in name:
                    continue
                src = os.path.join(libdir, name)
                real = os.path.realpath(src)
                if not os.path.isfile(real):
                    continue
                target = fresh.get(os.path.basename(real), real)
                dest = os.path.join(stage, name)
                if os.path.lexists(dest):
                    continue
                self.output.info("runtime symlink %s -> %s" % (name, target))
                os.symlink(target, dest)
        return [stage]

    def test(self):
        if not can_run(self):
            self.output.warning("目标二进制不能在当前机器运行，跳过消费者测试")
            return
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or os.environ.get("CC") or "clang"
        pc_dir = os.path.join(self.build_folder, "pc-fix")
        self._rewrite_pkgconfig(pc_dir)
        src = os.path.join(self.source_folder, "test_package.c")
        out = os.path.join(self.build_folder, "test_libgfbgraph")
        self.run(
            'set -e; export PKG_CONFIG_PATH="%s"; '
            'flags=$(pkg-config --cflags --libs libgfbgraph-0.2); '
            'echo "pkg-config resolved flags: $flags"; '
            '%s -o "%s" "%s" $flags' % (pc_dir, cc, out, src),
            env="conanbuild",
        )
        libs = ":".join(self._libdirs())
        self.run(
            'LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH" "%s"' % (libs, out),
            env="conanrun",
        )
