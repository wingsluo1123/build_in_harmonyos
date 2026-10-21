#!/usr/bin/env python3
"""Conan recipe — Meson project (PipeWire 1.6.9)."""
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class PipewireConan(ConanFile):
    name = "pipewire"
    version = "1.6.9"
    description = "PipeWire multimedia server library 1.6.9"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/pipewire/pipewire"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # Upstream builds libpipewire with an explicit shared_library() call, so
        # the Conan "shared" option cannot change the artifact. Reject a static
        # request instead of producing a package that claims shared=False while
        # shipping libpipewire-0.3.so (kcolorscheme 6.26.0.1 precedent).
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "pipewire 1.6.9 OHOS adaptation only packages the shared library "
                "(libpipewire-0.3.so); use -o '&:shared=True' (the default)."
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: System-name libraries default to static
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Minimal build: core libs + spa + tools + tests, no external deps
        tc.project_options["tests"] = "enabled"
        tc.project_options["pipewire-jack"] = "disabled"
        tc.project_options["pipewire-alsa"] = "disabled"
        tc.project_options["pipewire-v4l2"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["docs"] = "disabled"
        tc.project_options["man"] = "disabled"
        tc.project_options["session-managers"] = "[]"
        tc.project_options["spa-plugins"] = "enabled"
        tc.project_options["alsa"] = "disabled"
        tc.project_options["bluez5"] = "disabled"
        tc.project_options["jack"] = "disabled"
        tc.project_options["dbus"] = "disabled"
        tc.project_options["sndfile"] = "disabled"
        tc.project_options["ffmpeg"] = "disabled"
        tc.project_options["vulkan"] = "disabled"
        tc.project_options["gstreamer"] = "disabled"
        tc.project_options["libsystemd"] = "disabled"
        tc.project_options["logind"] = "disabled"
        tc.project_options["systemd-system-service"] = "disabled"
        tc.project_options["systemd-user-service"] = "disabled"
        tc.project_options["selinux"] = "disabled"
        tc.project_options["pw-cat"] = "disabled"
        tc.project_options["readline"] = "disabled"
        tc.project_options["udev"] = "disabled"
        tc.project_options["libpulse"] = "disabled"
        tc.project_options["v4l2"] = "disabled"
        tc.project_options["libcamera"] = "disabled"
        tc.project_options["videoconvert"] = "disabled"
        tc.project_options["videotestsrc"] = "disabled"
        tc.project_options["audiotestsrc"] = "disabled"
        tc.project_options["libcanberra"] = "disabled"
        tc.project_options["libusb"] = "disabled"
        tc.project_options["x11"] = "disabled"
        tc.project_options["x11-xfixes"] = "disabled"
        tc.project_options["libffado"] = "disabled"
        tc.project_options["lv2"] = "disabled"
        tc.project_options["raop"] = "disabled"
        tc.project_options["avahi"] = "disabled"
        tc.project_options["snap"] = "disabled"
        tc.project_options["flatpak"] = "disabled"
        tc.project_options["gsettings"] = "disabled"
        tc.project_options["gsettings-pulse-schema"] = "disabled"
        tc.project_options["gstreamer-device-provider"] = "disabled"
        tc.project_options["installed_tests"] = "disabled"
        tc.project_options["sdl2"] = "disabled"
        tc.project_options["libmysofa"] = "disabled"
        tc.project_options["roc"] = "disabled"
        tc.project_options["avb"] = "disabled"
        tc.project_options["compress-offload"] = "disabled"
        tc.project_options["opus"] = "disabled"
        tc.project_options["ebur128"] = "disabled"
        tc.project_options["fftw"] = "disabled"
        tc.project_options["onnxruntime"] = "disabled"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器，而 clang 工具链在 /data/service/hnp/bin，CI worker PATH 上无
        # llvm-ar 时 configure 失败（cairo 1.18.4 / libsigc / pixman / bstring 同一模式）。直接把
        # ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH。
        import os as _os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar"); _rl = _ce.get("ranlib")
        # CI profile 仅提供 c/cpp，未给 ar/ranlib：从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径。
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = _os.path.dirname(_cc) if _os.path.sep in _cc else ""
            if _bindir:
                _cand = _os.path.join(_bindir, "llvm-ar")
                if _os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = _os.path.join(_bindir, "llvm-ranlib")
                    if _os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = _os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and _os.path.isfile(_nf):
            with open(_nf) as _f: _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl: _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f: _f.write(_c)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # OHOS 对已签名 ELF 做完整性校验：meson 安装期会重写 rpath（把构建树
        # 的 $ORIGIN rpath 抹掉），改动字节后 execve 直接返回 EPERM（真机实测
        # bin/pipewire、pw-cli 均无法执行）。这里在安装完成后用构建树里未被
        # 改动的原始产物覆盖安装副本，保持签名有效；运行时库定位交给
        # LD_LIBRARY_PATH / 系统路径。恢复失败不静默：任何一个安装 ELF 无法
        # 恢复都抛错，避免把不可执行的包标记为成功。
        import os as _os
        import shutil as _sh
        # 同 basename 在构建树可能命中多个产物；候选只收 ELF，按确定的目录/文件
        # 顺序取第一个，并在真正命中多个候选时打印告警，避免 os.walk 顺序不确定
        # 造成换错二进制，也避免同名非 ELF 文件遮住真正产物。
        _cands = {}
        for _root, _dirs, _files in _os.walk(self.build_folder):
            _dirs.sort()
            for _fn in sorted(_files):
                _p = _os.path.join(_root, _fn)
                if _os.path.islink(_p) or not _os.path.isfile(_p):
                    continue
                try:
                    with open(_p, "rb") as _f:
                        if _f.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                _cands.setdefault(_fn, []).append(_p)
        _errors = []
        _symlinks = []
        _restored = 0
        for _root, _dirs, _files in _os.walk(self.package_folder):
            _dirs.sort()
            for _dn in list(_dirs):
                _dp = _os.path.join(_root, _dn)
                if _os.path.islink(_dp):
                    _symlinks.append(_dp)
                    _dirs.remove(_dn)
            for _fn in sorted(_files):
                _dst = _os.path.join(_root, _fn)
                if _os.path.islink(_dst):
                    _symlinks.append(_dst)
                    continue
                try:
                    with open(_dst, "rb") as _f:
                        if _f.read(4) != b"\x7fELF":
                            continue
                except OSError as _e:
                    _errors.append("%s: %s" % (_dst, _e))
                    continue
                _list = _cands.get(_fn) or []
                if not _list:
                    # 找不到原始产物就不能恢复签名字节；保留安装副本会在设备上
                    # execve EPERM，因此与复制失败同等对待（fail-closed）。
                    _errors.append("%s: no build-tree original" % _dst)
                    continue
                if len(_list) > 1:
                    self.output.warning("pipewire package(): %d build-tree candidates for %s; using %s"
                                        % (len(_list), _fn, _list[0]))
                _src = _list[0]
                try:
                    _sh.copyfile(_src, _dst)
                    _os.chmod(_dst, 0o755)
                    _restored += 1
                except OSError as _e:
                    _errors.append("%s <- %s: %s" % (_dst, _src, _e))
        if _symlinks:
            raise ConanException("pipewire package(): symlinks are not allowed on HMDFS: %s"
                                 % ", ".join(_symlinks[:10]))
        if _errors:
            raise ConanException("pipewire package(): failed to restore %d ELF file(s): %s"
                                 % (len(_errors), "; ".join(_errors[:10])))
        self.output.info("pipewire package(): restored %d ELF file(s) from the build tree" % _restored)
        # 安装脚本用 cp 物化的守护进程别名同样源自被改写的 pipewire，需要
        # 以恢复后的 bin/pipewire 重新生成。
        _pw = _os.path.join(self.package_folder, "bin", "pipewire")
        if not _os.path.isfile(_pw):
            raise ConanException("pipewire package(): bin/pipewire is missing from the install tree")
        for _alias in ("pipewire-pulse", "pipewire-avb", "pipewire-aes67"):
            _dst = _os.path.join(self.package_folder, "bin", _alias)
            if not _os.path.isfile(_dst):
                raise ConanException("pipewire package(): daemon alias bin/%s is missing" % _alias)
            try:
                _sh.copyfile(_pw, _dst)
                _os.chmod(_dst, 0o755)
            except OSError as _e:
                raise ConanException("pipewire package(): cannot materialise bin/%s: %s" % (_alias, _e))

    def package_info(self):
        self.cpp_info.libs = ["pipewire-0.3"]
        self.cpp_info.system_libs = ["dl", "pthread", "m"]
        # meson installs headers under <prefix>/include/pipewire-0.3/
        # and spa headers under <prefix>/include/spa-0.2/
        self.cpp_info.includedirs = ["include/pipewire-0.3", "include/spa-0.2", "include"]
