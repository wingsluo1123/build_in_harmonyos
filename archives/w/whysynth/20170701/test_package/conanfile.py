import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    # PkgConfigDeps 让 pkg-config 能找到 dssi.pc/alsa.pc；
    # VirtualRunEnv / VirtualBuildEnv 必须一并写上：显式给 generators 会
    # **替换**（而非追加）conan 的默认集，漏了 VirtualRunEnv 就没有 conanrun
    # 环境，test() 里 env="conanrun" 拿不到 LD_LIBRARY_PATH。
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 测试程序自己要看 dssi.h / ladspa.h / alsa/seq_event.h，被测包不导出
        # 这些头（它是插件模块），所以显式声明。
        self.requires("dssi/1.1.1")
        self.requires("alsa-lib/1.2.16.1")

    def _pkgconfig(self, what, packages):
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = (self.generators_folder + os.pathsep
                                  + env.get("PKG_CONFIG_PATH", ""))
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for candidate in ("/data/service/hnp/bin/pkg-config",
                              "/usr/bin/pkg-config"):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    exe = candidate
                    break
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what] + packages, capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0:
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _dependency_include_dirs(self):
        """从依赖（含传递依赖）的 cpp_info 收集 include 目录。"""
        dirs = []
        seen = set()
        for view in (self.dependencies.host, self.dependencies):
            try:
                items = view.items()
            except AttributeError:
                continue
            for ref, dep in items:
                key = str(ref.ref) if hasattr(ref, "ref") else str(ref)
                if key in seen:
                    continue
                seen.add(key)
                base = getattr(dep, "package_folder", None) or ""
                for path in dep.cpp_info.includedirs:
                    if not os.path.isabs(path) and base:
                        path = os.path.join(base, path)
                    if os.path.isdir(path):
                        dirs.append("-I" + path)
        return dirs

    def _plugin_path(self):
        """被测包里装好的 DSSI 插件模块。"""
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        plugin_dir = os.path.join(package_folder, "lib", "dssi")
        candidates = []
        if os.path.isdir(plugin_dir):
            for name in sorted(os.listdir(plugin_dir)):
                if name.startswith("whysynth") and ".so" in name:
                    candidates.append(os.path.join(plugin_dir, name))
        if not candidates:
            raise ConanException(
                f"no whysynth plugin module found in {plugin_dir}"
            )
        return candidates[0]

    def build(self):
        plugin = self._plugin_path()
        self.output.info(f"whysynth plugin: {plugin}")

        includes = self._pkgconfig("--cflags", ["dssi", "alsa"])
        if includes:
            self.output.info("test_package uses pkg-config --cflags")
        else:
            self.output.warning("pkg-config --cflags unavailable, falling back to cpp_info")
            includes = " ".join(self._dependency_include_dirs())

        libdirs = []
        for _ref, dep in self.dependencies.items():
            for libdir in dep.cpp_info.libdirs:
                if libdir not in libdirs:
                    libdirs.append(libdir)

        cc = os.environ.get("CC", "clang")
        # C 程序不能带 C++ 标准开关；musl 上要用 gnu 方言（严格 ISO 方言不声明
        # POSIX 函数）。
        cmd = (f'{cc} -std=gnu99 -Wall -o test_whysynth test_whysynth.c '
               f'-DTARGET_SO=\'"{plugin}"\' {includes} '
               f'{" ".join("-L" + d for d in libdirs)} -lm -ldl')
        self.run(cmd)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building：只验证编译与链接")
            return
        # 插件在运行时要加载 libfftw3f/libasound，打包目录不在加载器默认路径上，
        # 必须显式给 LD_LIBRARY_PATH（链接期的 rpath 对被 dlopen 的 .so 不生效）。
        libdirs = []
        for _ref, dep in self.dependencies.items():
            for libdir in dep.cpp_info.libdirs:
                if libdir not in libdirs:
                    libdirs.append(libdir)
        ldpath = os.pathsep.join(libdirs)
        prefix = (f'LD_LIBRARY_PATH="{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}" '
                  if ldpath else "")
        self.run(f"{prefix}./test_whysynth", env="conanrun")
