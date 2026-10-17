#!/usr/bin/env python3
"""Conan test_package for wxsvg 1.5.25 — 消费者冒烟测试（L1）。

覆盖：SVG 解析（expat 路径）/ DOM 查询 / 离屏渲染（cairo 真实光栅化，无需
显示环境）/ 像素级断言。上游 wxsvg 无任何测试套件（R51 清点为 0），本测试
补位。

构建方式：直接从解析后的 cpp_info 编译（playerctl/2.4.1.1 同款），不走
CMakeDeps/PkgConfigDeps —— wxsvg 消费需要 wx 静态全链（libwxsvg.so 内烘焙
的 wx 符号不可见，消费者必须再链 wxwidgets-gtk3 的静态链）加上 glib 私有
传递依赖补链，后者无法用 CMake target 语义表达：
  * -lffi / -lpcre2-8：glib 的静态传递依赖（glib 组件 requires 有声明，
    但作为静态库必须晚于其引用者出现，故尾置）；
  * -lintl：glib 包私有代理 libintl.so（gettext -> g_libintl_* 桥），
    glib 系 .pc/cpp_info 均不传递，与 wxsvg 配方 generate() 同款处理。
"""
import os

from conan import ConanFile


class WxsvgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    # VirtualBuildEnv: CXX/CC 在 PATH；VirtualRunEnv: 运行期全部依赖包
    # lib 目录进 LD_LIBRARY_PATH（conanrun）。
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib 的静态传递依赖（libffi/pcre2）只进构建图、不进消费图聚合
        # （wxsvg 配方 docstring 有全文）；消费链接行的尾置 -lffi/-lpcre2-8
        # 需要它们的包目录，在测试图里自行声明。版本与 glib/2.84 系配方
        # 的 requires 一致（libffi/3.4.4、pcre2/10.45，单图单版本）。
        self.requires("libffi/3.4.4")
        self.requires("pcre2/10.45")

    @staticmethod
    def _abs(dep, d):
        return d if os.path.isabs(d) else os.path.join(dep.package_folder, d)

    def _collect_cpp_info(self):
        """聚合整图的 include/lib 目录与 defines；lib 需要定序，单独处理。"""
        inc_dirs, lib_dirs, defines = [], [], []
        for dep in self.dependencies.host.values():
            ci = dep.cpp_info
            for d in ci.includedirs:
                inc_dirs.append(self._abs(dep, d))
            for d in ci.libdirs:
                lib_dirs.append(self._abs(dep, d))
            defines.extend(ci.defines)
            for comp in ci.components.values():
                for d in comp.includedirs:
                    inc_dirs.append(self._abs(dep, d))
                for d in comp.libdirs:
                    lib_dirs.append(self._abs(dep, d))
                defines.extend(comp.defines)
        # 去重保序
        uniq = lambda seq: list(dict.fromkeys(seq))
        return uniq(inc_dirs), uniq(lib_dirs), uniq(defines)

    def _collect_libs(self):
        """确定性链接序：
        1) -lwxsvg（被测共享库优先）
        2) wxwidgets-gtk3 静态全链（cpp_info.libs 内部顺序已由上游配方按
           依赖拓扑排好：上层 GUI 库在前、base 在后、内置 3rdparty 紧随）
        3) 其余依赖（全部共享库，与顺序无关）
        4) 尾置 -lffi -lpcre2-8 -lintl（静态/代理补链，必须晚于引用者）
        """
        libs = ["wxsvg"]
        wx = self.dependencies["wxwidgets-gtk3"]
        libs.extend(wx.cpp_info.libs)

        tail_skip = {"wxwidgets-gtk3", "libffi", "pcre2"}
        for dep in self.dependencies.host.values():
            if dep.ref is None or dep.ref.name in tail_skip:
                continue
            ci = dep.cpp_info
            libs.extend(ci.libs)
            for comp in ci.components.values():
                libs.extend(comp.libs)
        # 去重保序（保留首次出现位置）
        libs = list(dict.fromkeys(libs))
        libs += ["ffi", "pcre2-8", "intl"]
        return libs

    def build(self):
        cxx = os.environ.get("CXX") or "clang++"
        inc_dirs, lib_dirs, defines = self._collect_cpp_info()
        libs = self._collect_libs()

        inc = " ".join("-I%s" % p for p in inc_dirs)
        dfn = " ".join("-D%s" % d for d in defines)
        lib = " ".join("-L%s" % p for p in lib_dirs)
        lnk = " ".join("-l%s" % l for l in libs)
        # E505：用 DT_RPATH 内嵌依赖 lib 目录，运行期不依赖全局
        # LD_LIBRARY_PATH（OHOS musl 下该变量会压过 DT_RPATH，且 HMDFS 上
        # 符号链接形式的版本化别名无法由加载器经别名解析）。
        rpf = " ".join("-Wl,-rpath,%s" % p for p in lib_dirs)
        cmd = ("{cxx} test_package.cpp -o test_wxsvg "
               "-Wl,--disable-new-dtags {rpf} {inc} {dfn} {lib} {lnk}").format(
            cxx=cxx, rpf=rpf, inc=inc, dfn=dfn, lib=lib, lnk=lnk)
        self.run(cmd, shell=True, env="conanbuild")

    def test(self):
        self.run("./test_wxsvg", env="conanrun")
