#!/usr/bin/env python3
"""Conan recipe — sox_ng (SoX next generation, autotools).

sox_ng is a rewrite of SoX (Sound eXchange): audio conversion library
(libsox_ng) plus CLI tools (sox_ng, soxi_ng, play_ng, rec_ng).

OHOS adaptation (patches, see conandata.yml):
- 0001: Makefile.in - empty DOCPDF so make install does not depend on
  pdfroff (vendored tree is text-only; rationale in conandata.yml)
- 0002/0003: config.guess/config.sub do not recognize the linux-ohos
  triplet (knowledge E007/E072); config.guess temp dir umask 077->007
  (HMDFS uid mapping: 0700 dirs unwritable by creating process)
- 0004: configure - temp dir umask 077->007 in config.status template
  (HMDFS uid mapping: umask-077 temp dir fails EACCES writing subs1.awk)
- 0005: musl libc tmpfile() truncates the TMPDIR value to a 7-char
  static buffer, so a long TMPDIR (e.g. /storage/Users/currentUser/tmp)
  yields a bogus path under the read-only root directory and fails with
  EACCES; lsx_tmpfile() now uses the full TMPDIR via mkstemp
- 0006: /tmp is read-only on OHOS; test/check.sh hardcoded /tmp (E002)
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
import os
import time
import hashlib
import random


class SoxngConan(ConanFile):
    name = "sox_ng"
    version = "14.8.0.1"
    description = "SoX next generation: audio conversion library and CLI tools"
    license = "LGPL-2.1-or-later"
    homepage = "https://codeberg.org/sox_ng/sox_ng"
    url = "https://codeberg.org/sox_ng/sox_ng"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # 官方 release tarball 的解包随配方导出（vendor/sox_ng-14.8.0.1/，609 文本文件，
    # CHECKSUMS.sha256 逐文件钉死 sha256）。官方解包共 675 文件，剔除 66 个二进制
    # （58 个测试音频素材 + 7 个预建文档 PDF + src/monkey.wav）：平台 PR .diff 端点
    # 不携带二进制载荷，二进制文件导致 CI checkout-pr 秒败（CI #90955/#90964
    # "missing binary patch data"）；构建/安装链不消费这些文件，0001 补丁解除
    # install-pdf 对预建 PDF 的依赖。codeberg release 端点对 CI 共享出口 IP 持续
    # 429 限流（CI #89737/#90123：2 台 worker、跨 2.5h、22.5min 退避窗口仍全落空）
    # ——source() 下载失败时安装此 hash-verified 副本（fail closed）。同构 fcft 3.3.3
    # 的 tllist vendor 先例（CI #43331 后确立）。
    exports_sources = "vendor/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 可消费全集：制品仓 ohpcd 已发布（binary 实测可消费）
        self.requires("zlib/1.3.1")
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        self.requires("libsndfile/1.2.2")
        self.requires("libflac/1.5.0")
        self.requires("libmp3lame/3.100")
        self.requires("libmad/0.15.1b")
        self.requires("libid3tag/0.16.3")
        self.requires("libopus/1.6.1")
        self.requires("libpng/1.6.39")
        self.requires("libspeexdsp/1.2.1")

    def layout(self):
        basic_layout(self)

    def _get_with_retry(self, source_data, **kwargs):
        # codeberg release 端点对 CI 共享出口 IP 持续 429 限流（CI #89737/#90123）。
        # 重试策略同构 fcft 3.3.3（CI #43331 后确立）：3 次指数退避 + jitter，
        # 防共享出口 IP 的并行 worker 同步重试；sha 不匹配/404 立即换源。
        # 上限保持低——source() 在重试耗尽后安装 hash-verified vendor 副本，
        # 无必要烧 CI 时间硬扛长限流窗口。
        urls = source_data.get("url")
        if isinstance(urls, str):
            urls = [urls]
        sha256 = source_data.get("sha256")
        last_exc = None
        max_attempts = 3
        for url in urls:
            for attempt in range(1, max_attempts + 1):
                try:
                    get(self, url=url, sha256=sha256, **kwargs)
                    return
                except ConanException as exc:
                    last_exc = exc
                    msg = str(exc).lower()
                    if "sha256" in msg or "hash" in msg:
                        self.output.warning(
                            "sha256 mismatch for %s, trying next mirror" % url)
                        break
                    if "404" in msg or "not found" in msg or "does not exist" in msg:
                        self.output.warning(
                            "%s not found at %s, trying next mirror"
                            % (self.name, url))
                        break
                    self.output.warning(
                        "download attempt %d/%d failed for %s: %s"
                        % (attempt, max_attempts, url, exc))
                    if attempt < max_attempts:
                        wait = min(15 * (2 ** (attempt - 1)), 120)
                        time.sleep(wait + random.uniform(0, 10))
        raise last_exc

    def _install_vendored_source(self):
        # vendor/sox_ng-14.8.0.1 = 官方 release tarball 解包（strip root，
        # tarball sha256 7698a1b2699499b0b38fa95a15bb56c68928d97b144bce03b7ecb76fe9c46698，
        # 本地 2026-10-13 复核；文本化：官方解包 675 文件剔除 66 个二进制后为 609，
        # 原因见类注释）；CHECKSUMS.sha256 钉死 609 文件逐条 sha256（条目相对解包根
        # 目录，与 strip_root 后布局一致），fail closed。
        # EXECUTABLES.txt 钉死 tarball 可执行文件清单：Python 逐文件写盘不保留
        # tarball mode 位（落 660），写后按清单恢复 0o755，缺失即 fail closed
        # （否则 ./configure Permission denied, exit 126——CI 必走回退路径，必现）。
        # mtime 归一：顺序写盘产生 mtime 先后差 → automake maintainer 再生链
        # （aclocal 缺失, Error 127），写后 os.utime 统一还原发布 mtime。
        # 注意：不整体清空 source_folder——conan source 本地上下文里 source_folder
        # 即配方目录本身。失败的 get() 残树是清单项的子集（同一 tarball 解包），
        # 逐项覆盖写（先删后写）足以保证结果干净。
        vendor_dir = os.path.join(self.export_sources_folder,
                                  "vendor", "sox_ng-14.8.0.1")
        checksums_file = os.path.join(self.export_sources_folder,
                                      "vendor", "CHECKSUMS.sha256")
        if not os.path.isfile(checksums_file):
            raise ConanException(
                "vendored fallback missing CHECKSUMS.sha256 in recipe export")
        executables_file = os.path.join(self.export_sources_folder,
                                        "vendor", "EXECUTABLES.txt")
        if not os.path.isfile(executables_file):
            raise ConanException(
                "vendored fallback missing EXECUTABLES.txt in recipe export")
        with open(executables_file, "r", encoding="utf-8") as f:
            executables = {l.strip() for l in f if l.strip()}
        # mtime 归一：tar 解包把全部文件 mtime 统一置为发布时间；此处顺序写盘
        # 产生 mtime 先后差（aclocal.m4 先于 configure.ac/m4/* 落盘）→ make 判
        # aclocal.m4 过期 → automake maintainer 再生链（aclocal-1.17 未安装 →
        # Error 127，第 3 轮强制 vendor 复验实证）。写后统一还原发布 mtime，
        # 与 tar 解包语义对齐。
        import calendar
        import time as _time
        _vendor_mtime = calendar.timegm(
            _time.strptime("2026-05-12 06:47:00", "%Y-%m-%d %H:%M:%S"))
        installed = 0
        with open(checksums_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                expected_sha, relpath = line.split("  ", 1)
                src = os.path.join(vendor_dir, relpath)
                if not os.path.isfile(src):
                    raise ConanException(
                        "vendored fallback missing %s in recipe export" % relpath)
                with open(src, "rb") as fh:
                    content = fh.read()
                actual_sha = hashlib.sha256(content).hexdigest()
                if actual_sha != expected_sha:
                    raise ConanException(
                        "vendored source %s sha256 mismatch: %s != %s"
                        % (relpath, actual_sha, expected_sha))
                dest = os.path.join(self.source_folder, relpath)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if os.path.exists(dest):
                    os.remove(dest)
                with open(dest, "wb") as fh:
                    fh.write(content)
                if relpath in executables:
                    os.chmod(dest, 0o755)
                os.utime(dest, (_vendor_mtime, _vendor_mtime))
                installed += 1
        self.output.info(
            "installed vendored sox_ng 14.8.0.1 (%d files, sha256 verified)"
            % installed)

    def source(self):
        # 官方 URL 为首选源（R39 不变）；codeberg 对 CI 共享出口 IP 持续限流
        # （429，CI #89737/#90123）时回退 hash-verified vendor 副本（同构
        # fcft 3.3.3 tllist 先例）。本地/无限制环境首次尝试即成功，无额外开销。
        try:
            self._get_with_retry(dict(self.conan_data["sources"]),
                                 strip_root=True)
        except ConanException as exc:
            self.output.warning(
                "source download failed (%s); using vendored fallback" % exc)
            self._install_vendored_source()

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # configure 探测可选格式库需要 CPPFLAGS/LDFLAGS 指向 conan 依赖
        deps = AutotoolsDeps(self)
        deps.generate()
        # 原生编译 OHOS（build profile == host profile）：configure 会实际执行
        # 测试程序，build 环境必须能在运行时找到 host 依赖的共享库
        # （conan 默认不把 host 依赖 runenv 合入 build env）。
        env = Environment()
        for require, dep in self.dependencies.host.items():
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                env.append_path("LD_LIBRARY_PATH", path)
        env.vars(self, scope="build").save_script("host_deps_ld_path")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # release tarball 含预生成 configure，无需 autoreconf
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["sox_ng"]
