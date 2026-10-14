#!/usr/bin/env python3
"""4ti2 test_package — qsolve C API、任意精度后端产物与 gensymm CLI 验证"""
import os
import tempfile
from conan import ConanFile


class FourTi2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：既 #include 公共头（4ti2 include/，含 gmp
        # 传递头），又链接静态库（4ti2 lib/ + 传递 glpk/gmp lib）——CI 的 L1e
        # 会把 include/ 与 lib/ 移走再跑一次，两处都要真实依赖。
        incs, linkdirs, rpaths = [], [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            for p in _d.cpp_info.libdirs:
                if os.path.isdir(p):
                    linkdirs.append("-L" + p)
                    rpaths.append("-Wl,-rpath-link," + p)
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        # conf first, then standard tool names (portable: the OHOS profile
        # always provides the conf; other hosts just use their compiler).
        cc = comp.get("c") or "cc"
        cxx = comp.get("cpp") or "c++"
        # 源码走 C 编译以验证 extern "C" 公共 API；链接用 clang++，
        # 因为 lib4ti2*.a 内含 C++ 代码，需要 libc++ 运行时。
        # 链接行按链接器实际报错确定：公共头 4ti2/4ti2.h 在 C++ 编译单元中
        # 声明 operator<<(std::ostream&, const __mpz_struct*)（test.c 经
        # clang++ 链接、libc++ ABI），该符号定义在 lib4ti2gmp.a，而后者依赖
        # libgmpxx（mpz_class）——故必须显式 -l4ti2gmp -lgmpxx。
        # 顺序：精度后端(int64/gmp) → 基础(common/util) → gmpxx/gmp → glpk → m。
        self.run(f'{cc} -c test.c -o test.o {" ".join(incs)}')
        self.run(f'{cxx} test.o -o test_probe {" ".join(linkdirs)} {" ".join(rpaths)} '
                 f'-l4ti2int64 -l4ti2gmp -l4ti2common -l4ti2util -lgmpxx -lgmp -lglpk -lm')

    def test(self):
        _pkg = self.dependencies["4ti2"].package_folder
        # 1) 任意精度后端打包检查（缺失即失败）：bin/4ti2gmp 可执行文件与
        #    lib/lib4ti2gmp.a 静态库必须真实存在，证明 gmp C++ 后端已构建。
        _gmp_exe = os.path.join(_pkg, "bin", "4ti2gmp")
        # Artifact name follows the tested package's shared option: static
        # packages ship .a, shared-only packages ship .so. The build() link
        # line uses -l flags, which resolve to whichever flavor is present.
        _is_shared = bool(self.dependencies["4ti2"].options.shared)
        _gmp_lib_name = "lib4ti2gmp.so" if _is_shared else "lib4ti2gmp.a"
        _gmp_lib = os.path.join(_pkg, "lib", _gmp_lib_name)
        if not os.path.isfile(_gmp_exe):
            raise AssertionError(f"missing packaged arbitrary-precision executable: {_gmp_exe}")
        if not os.path.isfile(_gmp_lib):
            raise AssertionError(f"missing packaged arbitrary-precision library: {_gmp_lib}")
        self.output.info(f"backend artifacts verified: {_gmp_exe}, {_gmp_lib}")
        # 进一步真实执行 4ti2gmp（--version），确认它能在本机加载
        # libgmpxx.so/libgmp.so 依赖并运行，而不仅是文件存在。
        self.run(f'"{_gmp_exe}" --version', env="conanrun")
        # 2) C API 测试：qsolve 参考算例（对齐上游 test/qsolve/api/qsolve_main.cpp），
        #    校验计算出的 4x3 qhom 矩阵，非零退出码即失败。
        self.run("./test_probe", env="conanrun")
        # 3) CLI 二进制验证：执行包内 gensymm 工具（在 $TMPDIR 草稿目录中运行，
        #    避免其输出文件 333.sym 污染 test_package 源码树）。
        _gensymm = os.path.join(_pkg, "bin", "gensymm")
        # TemporaryDirectory: scratch (and gensymm's 333.sym) is removed on
        # exit, including when self.run raises (no orphan dirs in TMPDIR).
        with tempfile.TemporaryDirectory(prefix="4ti2-gensymm-") as _scratch:
            self.run(f'cd "{_scratch}" && "{_gensymm}" 3 3 3 1 333', env="conanrun")
