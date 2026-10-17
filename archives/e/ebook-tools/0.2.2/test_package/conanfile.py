#!/usr/bin/env python3
"""ebook-tools/0.2.2 的 test_package：现场造一个最小 EPUB，走 libepub 真实解析链路。

- test.c 用 libzip（EPUB 容器就是 zip）现场构造 mimetype + META-INF/container.xml +
  OEBPS/content.opf + 章节，再调 libepub 的 epub_open / epub_get_metadata /
  epub_get_ocf_file 读回并逐字节比对 —— 不是 print-only 空壳（R34/PF3）。
- test() 另外 exec 一次打包进 bin/ 的 einfo CLI（验签名 + 运行时链接）。
- 手工 cc 编译（与 archives/l/libzip/1.11.4 test_package 同法）：绕开 conan_toolchain
  在 os=OHOS 下的 CMAKE_SYSTEM_NAME 映射问题，也免去 test_package 再起一套 cmake。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 现场构造 EPUB 容器要用（libepub 自己的依赖，制品仓已发布）
        self.requires("libzip/1.11.4")

    def build(self):
        cc = os.environ.get("CC", "clang")
        incs, libdirs = [], []
        for _ref, d in self.dependencies.items():
            # 只收绝对路径：graph 里混着一条未聚合的相对项（includedirs=["include"]），
            # 拼进编译行会退化成 -Iinclude/-Llib 之类对 CWD 的隐式依赖。
            incs += ["-I" + p for p in d.cpp_info.includedirs if os.path.isabs(p)]
            libdirs += [p for p in d.cpp_info.libdirs if os.path.isabs(p)]
        inc = " ".join(incs)
        # 头闭包/运行时都要带全依赖的 lib 目录（libepub.so 运行时还要找 libxml2/libzip）
        # 注意：库名是 epub（产物 libepub.so）⇒ 链接旗标是 -lepub，写成 -leepub 会去找
        # libeepub.so 并报 ld.lld: unable to find library。
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-lepub", "-lzip"]
                        + ["-Wl,-rpath," + p for p in libdirs])
        # C 测试不能收 C++ 标准开关；musl 上用 gnu 方言才拿得到 POSIX 声明
        self.run(f"{cc} -std=gnu99 test.c -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        shell = os.environ.get("CONFIG_SHELL")
        if not shell:
            shell = "/data/service/hnp/bin/bash" if os.path.isfile("/data/service/hnp/bin/bash") else "/bin/sh"
        # ① 解析链路往返（构造→打开→读元数据→读容器条目→错误路径）
        self.run(f"{shell} -c './test_probe'", env="conanrun")
        # ② 执行打包的 CLI（XPM 签名 + 运行时链接）：einfo -h 打印 usage 并退出 0
        # 路径一律用 package_folder 绝对拼接——ConanFileInterface 上没有 bindirs/libdirs
        # 属性（要走 .cpp_info），且 cpp_info 里的相对 "bin"/"lib" 会被 musl 当 CWD 相对路径。
        # LD_LIBRARY_PATH 必须**聚合全部依赖**的 lib 目录：libepub.so 的 DT_NEEDED 里有
        # libxml2.so/libzip.so，只给本包 lib 会报 "Error relocating …: xmlStrdup: symbol not
        # found"（musl 忽略 DT_RUNPATH，本包 install 后 RPATH 为空）。
        dep = self.dependencies["ebook-tools"]
        bindir = os.path.join(dep.package_folder, "bin")
        ldirs = []
        for _ref, d in self.dependencies.items():
            for p in d.cpp_info.libdirs:
                if os.path.isabs(p) and p not in ldirs:
                    ldirs.append(p)
        pkg_lib = os.path.join(dep.package_folder, "lib")
        if os.path.isdir(pkg_lib) and pkg_lib not in ldirs:
            ldirs.insert(0, pkg_lib)
        ld_path = ":".join(ldirs)
        einfo = os.path.join(bindir, "einfo")
        if os.path.isfile(einfo):
            self.run("{sh} -c 'LD_LIBRARY_PATH={ld} {ei} -h'".format(
                sh=shell, ld=ld_path, ei=einfo), env="conanrun")
            self.output.info("einfo CLI 已执行（usage 退出码 0）")
        else:
            raise Exception("打包产物缺 bin/einfo——上游 install(TARGETS einfo) 未生效")
