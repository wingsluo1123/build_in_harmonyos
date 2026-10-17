#!/usr/bin/env python3
"""Conan recipe — pacredir 0.7.10 (raw GNU Makefile, 单 TU C11).

pacredir 是一个 HTTP 重定向守护进程：监听 127.0.0.1:7077，把 pacman 的 db/pkg
下载请求转发到局域网内通过 mDNS（``_pacserve._tcp.local``）发现的对等 pacserve
镜像上，并在 ``/`` 提供一个 HTML 状态页（内嵌 favicon.png 与 style.css）。上游
面向 Arch Linux + systemd 生态：peer 发现走 systemd-resolved 的
``org.freedesktop.resolve1.Manager.ResolveRecord`` D-Bus 方法，日志走
sd-journal，就绪通知走 sd_notify。

适配到 HarmonyOS PC (aarch64)。三处平台差异 + 两处依赖图处置：

平台差异（源码 / 构建层）
  1. musl 不传递暴露 ``ioctl()`` / ``SIOCGIFFLAGS``（glibc 由 <net/if.h> 间接
     提供），也不提供 glibc 内部 typedef ``__time_t`` —— 见
     patches/0001-pacredir.h.patch（无平台宏，glibc 下同样成立）。
  2. 上游 Makefile 在**解析期**用 ``$(shell ...)`` 探测 Arch 专有文件
     （``/etc/makepkg.conf`` 取 CARCH、``/etc/os-release`` 取 ID）。OHOS 上两者
     都不存在，``$(shell)`` 静默返回空串且 rc 被丢弃，空值经 version.h 编进
     二进制，进而污染运行期的 DNS-SRV TXT 对等体匹配（``arch=`` / ``id=``）与
     curl User-Agent。本配方改为从 Conan settings 推导并显式传 ``ARCH=`` / ``ID=``。
  3. ``favicon.h`` 由 ``resvg | oxipng``（均为 Rust CLI）从 logo.svg 渲染生成。
     制品仓里 resvg/0.47.0 与 oxipng/v10.1.1 的 manifest 状态都是 ``built``
     而非 ``published``（``conan download`` 实测取不到配方），且 CI 能力矩阵无
     Rust 工具链、无法 tool_requires 补齐。本配方用纯标准库 Python 复刻这条
     资产链：解码上游随包的 logo.png（96x96 调色板 PNG）→ 最近邻缩到 32x32 →
     重编码 PNG → 按 contrib/static_file.sh 的同构格式生成 C 头。产物维度、
     MIME、投递路径（``/favicon.png``）与上游一致；style.h 同理生成。

依赖图处置
  4. ``systemd/261.1``（提供 libsystemd：sd-bus / sd-daemon / sd-journal）钉
     ``zlib/1.3.1``，而 ``libcurl/8.5.0`` 钉 ``zlib/1.3.1.1`` —— 同图冲突，
     必须 override 到其中一方，代价是另一方的已发布二进制失效、需从源码重建。
     **本配方 override 到 zlib/1.3.1.1，让 systemd 从源码重建**，而不是反过来
     重建 libcurl。这个方向是被远程 CI 实测逼出来的，不是审美选择：
       - 反向方案（override 到 zlib/1.3.1 + 把 libcurl 切成静态库）在
         **CI #93768 实测失败**：libcurl 从源码构建时 CMake 走 ``make -j20``，
         撞上 OHOS 的 SELinux 禁止用户进程创建 FIFO ——
         ``make: jobserver mkfifo: .../GMfifo48803: Operation not permitted``
         → ``make[2]: /bin/sh: Resource temporarily unavailable``
         → ``/bin/sh: can't fork - try again`` → ``Error 127``。
         即知识条目 **E525**：GNU make 的 jobserver 靠 FIFO 传并行令牌，OHOS 上
         ``make -j>1`` 必炸、应统一 ``-j1``。但那个 ``-j20`` 出自 libcurl
         **自己的配方**（``cmake.build()``），下游无从干预——``tools.build:jobs``
         属 profile/conf，改它等于改框架文件（违反 W2 单 PR 原子性）。
       - systemd 的配方是纯 meson + ``ninja libsystemd.so.0.44.0``，全程不经过
         GNU make 的 jobserver（ninja 用 pipe），因此不受 E525 影响；且
         systemd/261.1 本身就是经 PR CI 从源码 ``conan create`` 成功后才发布的
         （commit 17debd6e99），worker 侧构建期工具已被那条 PR 实证可用。仓内
         另有 libseat/0.9.1、vte/0.74.2、libsoup/2.74.3 等多个 published 的
         meson 包，且都不 ``tool_requires`` meson，即依赖 worker 自带的系统 meson。
     zlib/1.3.1.1 正是仓内为「zlib/1.3.1 的 libz.a 非 PIC、链进共享库会炸
     ``R_AARCH64_ADR_PREL_PG_HI21``」而建的修订版（``--static`` + ``CFLAGS=-fPIC``），
     所以这个方向同时也避开了非 PIC 问题：libcurl 直接用回它已发布的**动态**二进制。
     ``-Wl,--exclude-libs,ALL`` 予以保留，但职责收窄为「把静态吸收进来的依赖符号
     留在本地作用域」，不再承担消解非 PIC 重定位的任务。
  5. 已发布的 ``libsystemd.so.0.44.0`` 带一个未定义符号 ``mallinfo2``：systemd
     配方在 OHOS 下注入 ``-DHAVE_MALLINFO2=1``，而该宏在
     0005-musl-mallinfo2-guard.patch 里同时罩住了 ``struct mallinfo2`` **和**
     systemd 自带的 ``static inline mallinfo2()`` 兜底实现；OHOS sysroot 的
     malloc.h 只声明了 struct、没有函数，于是符号悬空。链接**可执行文件**时
     lld 的 ``--no-allow-shlib-undefined``（可执行文件的默认值）把它升级成硬
     错误。SDK 的 libc.so 是链接桩（.text 仅 336 字节），其 .dynsym 收了
     malloc/mallopt 却漏了 mallinfo/mallinfo2 家族，而同一 sysroot 的 libc.a 里
     两者都是 ``T`` —— 即设备上真实 libc 有这个符号，只是桩的动态符号表不全。
     故用 ``-Wl,--allow-shlib-undefined`` 放行**共享库自身**的未定义符号；
     pacredir 自己目标文件的未定义符号仍照常报错，不会被这个开关掩盖。

上游测试清点见 notes.md：上游 0 个测试（无 tests/，Makefile 无 check/test
目标），适配后测试全部由 test_package/ 新增，计数口径为「独立检查项数量」。
"""
import hashlib
import os
import struct
import time
import zlib

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches
from conan.tools.gnu import AutotoolsDeps
from conan.tools.layout import basic_layout

# Conan settings.arch → 编进二进制的 ARCH 字面量。上游从 /etc/makepkg.conf 的
# CARCH 取，OHOS 无该文件（见模块 docstring 平台差异 2）。
_ARCH_LITERAL = {
    "armv8": "aarch64",
    "armv7": "armv7",
    "armv6": "armv6",
    "x86_64": "x86_64",
    "x86": "i686",
}

# static_file.h 里上游定义好的 MIME 常量。
_MIME_BY_EXT = {"css": "MIME_CSS", "png": "MIME_PNG"}


class PacredirConan(ConanFile):
    name = "pacredir"
    version = "0.7.10"
    description = ("Redirect pacman requests to a local mDNS-discovered pacserve "
                   "peer, with an embedded HTML status page")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/eworm-de/pacredir"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 产物只有 bin/pacredir 一个守护进程可执行文件，无库。
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS 与 Linux 都要放行，不能写成 == "Linux"。
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pacredir 需要 POSIX socket + D-Bus 客户端环境，不支持 {self.settings.os}")

    def requirements(self):
        # libsystemd：sd-bus（向 systemd-resolved 查 mDNS PTR/SRV/TXT）、
        # sd-daemon（sd_notify 就绪通知）、sd-journal（sd_journal_send）。OHOS
        # 不运行 systemd 本体，但客户端库可用；无系统总线时上游自己走
        # `goto fast_finish` 优雅降级（test_package 的鸿蒙特有测试实测此路径）。
        self.requires("systemd/261.1")
        # libmicrohttpd：7077 端口上的 HTTP 服务与状态页。
        self.requires("libmicrohttpd/1.0.1")
        # libcurl：探测候选 peer 的 db/pkg 可用性并挑最快的那个。
        self.requires("libcurl/8.5.0")
        # iniparser：解析 /etc/pacredir.conf（静态 peer、忽略网卡、verbose）。
        self.requires("iniparser/4.2.6")
        # 见模块 docstring「依赖图处置 4」：override 到 PIC 修订版 zlib/1.3.1.1，
        # 让 libcurl 用回它**已发布的动态二进制**，把「必须从源码重建」的那一个
        # 换成不经过 GNU make jobserver 的 systemd（meson + ninja）。反向方案
        # （override 到 zlib/1.3.1 + libcurl 切静态）已被远程 CI #93768 证伪：
        # libcurl 从源码构建时 CMake 走 make -j20，撞 OHOS SELinux 禁 FIFO（E525）。
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps 按拓扑序给出 CPPFLAGS/LDFLAGS/LIBS（静态依赖顺序敏感），
        # 经 conanbuild.sh 暴露给 build()。上游 Makefile 自己那套
        # `pkg-config --libs --cflags libsystemd libcurl libmicrohttpd iniparser`
        # 被命令行 CFLAGS_EXTRA 覆盖，因此不依赖 worker 上是否装了 pkg-config。
        AutotoolsDeps(self).generate()

    # ─────── 资产头生成（替代 resvg | oxipng + contrib/static_file.sh）───────
    @staticmethod
    def _png_chunks(data):
        """解析 PNG chunk 流并逐块校验 CRC（防生成出坏图还静默通过）。"""
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ConanInvalidConfiguration("logo.png 不是合法 PNG")
        pos, out = 8, []
        while pos < len(data):
            (length,) = struct.unpack(">I", data[pos:pos + 4])
            ctype = data[pos + 4:pos + 8]
            payload = data[pos + 8:pos + 8 + length]
            (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
            if zlib.crc32(ctype + payload) & 0xFFFFFFFF != crc:
                raise ConanInvalidConfiguration(f"logo.png chunk {ctype!r} CRC 校验失败")
            out.append((ctype, payload))
            pos += 12 + length
        return out

    @staticmethod
    def _png_unfilter(ihdr, idat):
        """按 PNG 规范还原 5 种行滤波，返回逐行原始像素。"""
        width, height, depth, ctype = ihdr[0], ihdr[1], ihdr[2], ihdr[3]
        if depth != 8:
            raise ConanInvalidConfiguration(f"只支持 8-bit PNG（logo.png 实际 {depth}）")
        bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
        stride = width * bpp
        raw = zlib.decompress(idat)
        prev, rows, pos = bytearray(stride), [], 0
        for _ in range(height):
            ft = raw[pos]
            line = bytearray(raw[pos + 1:pos + 1 + stride])
            pos += 1 + stride
            if ft == 1:
                for i in range(bpp, stride):
                    line[i] = (line[i] + line[i - bpp]) & 0xFF
            elif ft == 2:
                for i in range(stride):
                    line[i] = (line[i] + prev[i]) & 0xFF
            elif ft == 3:
                for i in range(stride):
                    a = line[i - bpp] if i >= bpp else 0
                    line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
            elif ft == 4:
                for i in range(stride):
                    a = line[i - bpp] if i >= bpp else 0
                    b, c = prev[i], (prev[i - bpp] if i >= bpp else 0)
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                    line[i] = (line[i] + pred) & 0xFF
            elif ft != 0:
                raise ConanInvalidConfiguration(f"未知 PNG 行滤波类型 {ft}")
            rows.append(bytes(line))
            prev = line
        return rows, bpp

    def _make_favicon_png(self, src_png, dst_png, size):
        """最近邻把 logo.png 缩到 size×size 并重编码 —— 复刻上游
        `resvg --width=32 --height=32 logo.svg -c | oxipng -` 的产物形态。"""
        chunks = self._png_chunks(open(src_png, "rb").read())
        first = dict(chunks)
        ihdr = struct.unpack(">IIBBBBB", first[b"IHDR"])
        width, height = ihdr[0], ihdr[1]
        idat = b"".join(p for c, p in chunks if c == b"IDAT")
        rows, bpp = self._png_unfilter(ihdr, idat)
        scaled = bytearray()
        for y in range(size):
            src = rows[min(height - 1, y * height // size)]
            row = bytearray()
            for x in range(size):
                off = min(width - 1, x * width // size) * bpp
                row += src[off:off + bpp]
            scaled += b"\x00" + row  # 每行前置 filter type 0（None）

        def chunk(ctype, payload):
            return (struct.pack(">I", len(payload)) + ctype + payload
                    + struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF))

        out = b"\x89PNG\r\n\x1a\n"
        out += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size,
                                          ihdr[2], ihdr[3], ihdr[4], ihdr[5], ihdr[6]))
        # 调色板与透明度必须随像素一起搬（colortype 3 的像素值是索引）。
        for keep in (b"PLTE", b"tRNS", b"gAMA", b"sRGB", b"bKGD", b"pHYs"):
            for ctype, payload in chunks:
                if ctype == keep:
                    out += chunk(ctype, payload)
        out += chunk(b"IDAT", zlib.compress(bytes(scaled), 9))
        out += chunk(b"IEND", b"")
        with open(dst_png, "wb") as fh:
            fh.write(out)
        # 自校验：把刚生成的 PNG 再解析一遍，确认 CRC 与维度都对得上。
        got = struct.unpack(">IIBBBBB", dict(self._png_chunks(out))[b"IHDR"])
        if (got[0], got[1]) != (size, size):
            raise ConanInvalidConfiguration(
                f"favicon.png 维度自校验失败：期望 {size}x{size}，实得 {got[0]}x{got[1]}")
        return len(out)

    def _emit_static_header(self, asset, header, date):
        """生成与上游 contrib/static_file.sh 同构的 C 头。

        不复用上游脚本本身：它 shebang 写 #!/bin/sh 却用了 bash 4 的 ${NAME^^}
        大写展开，还依赖 GNU 的 `stat --format=%s` 与 coreutils `sha1sum`，在
        OHOS 的 /bin/sh 上不可移植。这里按同一份 static_file.h 的结构体布局直接
        产出，字段语义完全一致（date / mime / sha1 / size / content）。
        """
        blob = open(asset, "rb").read()
        base = os.path.basename(asset)
        stem, ext = base.split(".")[0], base.rsplit(".", 1)[-1]
        if ext not in _MIME_BY_EXT:
            raise ConanInvalidConfiguration(f"static_file.h 未定义 MIME_{ext.upper()}")
        lines = [
            f"#ifndef {stem.upper()}_H",
            f"#define {stem.upper()}_H",
            '#include "static_file.h"',
            "",
            f"static_file {stem} = {{",
            f'  .date = "{date}",',
            f"  .mime = {_MIME_BY_EXT[ext]},",
            f'  .sha1 = "{hashlib.sha1(blob).hexdigest()}",',
            f"  .size = {len(blob)},",
            "  .content = {",
        ]
        for off in range(0, len(blob), 16):
            lines.append("    " + " ".join(f"0x{b:02x}," for b in blob[off:off + 16]))
        lines += ["  }", "};", "#endif", ""]
        with open(header, "w") as fh:
            fh.write("\n".join(lines))
        return len(blob)

    def _prepare_generated_headers(self):
        """补齐上游 Makefile 在 `pacredir` 目标上的全部生成式前置文件。

        生成后 mtime 新于各自前置（logo.png / style.css / config.def.h /
        Makefile），于是 `make pacredir` 会跳过 resvg / oxipng / markdown /
        static_file.sh 这些 OHOS 上不可用的规则，只留下上游那条真正的编译命令。
        """
        src = self.source_folder
        # 资产日期沿用上游 SOURCE_DATE_EPOCH 语义（RFC1123 GMT），但取值来自
        # tarball 内文件的 mtime 而非当前时间 —— 同一 tarball 可复现构建。
        epoch = int(os.path.getmtime(os.path.join(src, "Makefile")))
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(epoch))

        # 上游规则 `config.h: config.def.h` 就是一次 cp。
        with open(os.path.join(src, "config.def.h")) as fh:
            cfg = fh.read()
        with open(os.path.join(src, "config.h"), "w") as fh:
            fh.write(cfg)

        arch = _ARCH_LITERAL.get(str(self.settings.arch), str(self.settings.arch))
        os_id = str(self.settings.os).lower()
        with open(os.path.join(src, "version.h"), "w") as fh:
            fh.write("#ifndef VERSION_H\n#define VERSION_H\n"
                     '#define VERSION\t"%s"\n' % self.version
                     + '#define ARCH\t"%s"\n' % arch
                     + '#define ID\t"%s"\n' % os_id
                     + "#endif\n")
        self.output.info("version.h: VERSION=%s ARCH=%s ID=%s"
                         % (self.version, arch, os_id))

        n = self._make_favicon_png(os.path.join(src, "logo.png"),
                                   os.path.join(src, "favicon.png"), 32)
        self.output.info("favicon.png: 32x32, %d bytes（上游 resvg|oxipng 链的等价产物）" % n)
        for asset, header in (("favicon.png", "favicon.h"), ("style.css", "style.h")):
            size = self._emit_static_header(os.path.join(src, asset),
                                            os.path.join(src, header), date)
            self.output.info("%s: 内嵌 %d bytes, date=%s" % (header, size, date))

    def _compiler(self):
        """解析 C 编译器：Conan conf 注入的绝对路径优先（CI 与本地同源），其次
        环境 CC，最后 PATH 上的 clang。与 archives/s/systemd/261.1 的
        test_package、archives/d/darkhttpd/1.17 同一套解析顺序。"""
        try:
            ce = self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict) or {}
        except Exception:
            ce = {}
        return ce.get("c") or os.environ.get("CC") or "clang"

    def build(self):
        self._prepare_generated_headers()
        cc = self._compiler()
        arch = _ARCH_LITERAL.get(str(self.settings.arch), str(self.settings.arch))
        os_id = str(self.settings.os).lower()
        # conanbuild.sh 里 AutotoolsDeps 给出的 CPPFLAGS/CFLAGS/LDFLAGS/LIBS 全部
        # 塞进上游 Makefile 预留的 CFLAGS_EXTRA（它在编译命令里排在 CFLAGS 之后、
        # LDFLAGS 之前），另附三段链接控制：
        #   --as-needed              丢掉 systemd 的 cpp_info 广告、但
        #                            libsystemd.so 实际并不需要的 libzstd/
        #                            liblzma DT_NEEDED（实测 libsystemd.so 的
        #                            未定义符号里没有任何 ZSTD_*/lzma_*）。
        #                            注意它是**位置敏感**开关，必须排在 $LIBS
        #                            之前，放在其后对其余 -l 完全不生效。
        #   --exclude-libs,ALL       让非 PIC 的 zlib/1.3.1 静态对象在可执行文件
        #                            内部被消解（docstring 依赖图处置 4）
        #   --allow-shlib-undefined  放行 libsystemd.so 自带的悬空 mallinfo2
        #                            （docstring 依赖图处置 5）
        # env="conanbuild" 让 Conan 自己激活 generators 目录下的 conanbuild.sh
        # （basic_layout 下它在 <build>/conan/，不能按相对路径 source）。
        # 先 unset 环境变量再调 make：上游 Makefile 对 CFLAGS/LDFLAGS 用的是
        # `+=`，会静默吸收环境值，显式清空才能保证注入点唯一、可复现。
        script = (
            'set -e; '
            'EXTRA="$CPPFLAGS $CFLAGS -Wl,--as-needed $LDFLAGS $LIBS '
            '-Wl,--exclude-libs,ALL -Wl,--allow-shlib-undefined"; '
            'unset CFLAGS CPPFLAGS CXXFLAGS LDFLAGS LIBS; '
            'make -C "%s" pacredir CC="%s" CFLAGS_EXTRA="$EXTRA" '
            'VERSION="%s" ARCH="%s" ID="%s"'
            % (self.source_folder, cc, self.version, arch, os_id)
        )
        self.run(script, env="conanbuild")

    def package(self):
        copy(self, "COPYING.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "pacredir", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        # 上游 install-doc 装 .md 与由 Perl `markdown` 生成的 .html；OHOS 无该
        # 工具，只装 Markdown 原文与矢量 logo（.html 缺失已在 notes.md 声明）。
        for doc in ("README.md", "FLOW.md", "logo.svg"):
            copy(self, doc, self.source_folder,
                 os.path.join(self.package_folder, "share", "doc", "pacredir"))

    def package_info(self):
        # 纯可执行文件包：只导出 bindirs，不导出头/库搜索路径。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
