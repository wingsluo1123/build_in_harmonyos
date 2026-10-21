#!/usr/bin/env python3
"""Conan recipe for PerM 0.4.0 — 基于种子模式的短读比对工具（C++ / 上游自带 makefile）。

**上游**：`code.google.com/p/perm/`（Google Code 已关站）→ 源取 **Debian 源包 orig**（版本一致）。
**它是什么**（按源码实测）：基因组短读比对工具（种子模式），43 个 .cpp，`Source/PerM.cpp` 是主程序，
`Source/PerMTest.cpp` 是上游自带的测试程序。
**依赖**：上游 `Source/makefile` 里 `LIBS = -lm -lstdc++` → **零外部依赖** ✓（Debian 的
`Build-Depends: libbsd-dev` 是 Debian 侧补丁引入的，用 orig 源不需要）。
**构建**：上游 `makefile` 是**小写文件名**（make 能识别 ✓），且：
  ① `CC = g++ -O2 $(CFLAGS)` **硬编码 g++** ✗ → 命令行传 `CC="<clang++> -O2 -Wall"` 整体覆盖；
  ② `CFLAGS` 里带 **`-static`** ✗（musl 下与共享库冲突）→ 随 CC 覆盖一并去掉；
  ③ `perm` 目标会先 `make clean` 再编译，属上游正常流程。
**上游测试**：**有**（`Source/PerMTest.cpp`，自带 `main`）—— 但它 `main()` 里只调用
`testLongBases2Colors()` 并**固定 `return 0`**（不断言返回值），所以本配方把"能用除 PerM.cpp 外的
全部源编出该测试程序并真跑通、拿到 rc=0 与输出"作为门禁，**并如实记录它的断言语义**，不夸大成
"有 N 个断言全过"。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class PermConan(ConanFile):
    name = "perm"
    version = "0.4.0"
    description = ("PerM — a short read mapping tool based on seed patterns "
                   "(C++ / makefile / OpenMP)")
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/med-team/perm"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        spec = dict(self.conan_data["sources"])
        spec.pop("note", None)
        get(self, **spec, strip_root=True)

    def _cxx(self):
        import shutil
        for cand in ("clang++", "g++", "c++"):
            p = shutil.which(cand)
            if p:
                return p
        return "/data/service/hnp/bin/clang++"

    def _srcdir(self):
        """Debian orig 的压缩包是 `perm_0.4.0/Source/…` **两层** → conan 的 strip_root 只剥掉第一层，
        真正带 makefile 的源码在 `<source>/Source` 下（实测在源码根跑 make 会
        "No targets specified and no makefile found"）。"""
        sub = os.path.join(self.source_folder, "Source")
        return sub if os.path.isfile(os.path.join(sub, "makefile")) else self.source_folder

    def _patch_ptr_char_compare(self):
        """上游有把 `char*` 与字符字面量直接比较的写法（`m1.QScores == '\\0'`），现代 clang 会报
        `comparison between pointer and integer ('char *' and 'char')` → 做**等价最小修正**：
        `(!p || p[0] == '\\0')`，既覆盖"指针为空"也覆盖"首字符为 0"两种情况，语义不变、不动其它逻辑。
        （同文件里 `m1.caRef[0] == '\\0'` 是上游自己的写法，改法与之一致。）
        """
        h = os.path.join(self._srcdir(), "MappingResult.h")
        if not os.path.isfile(h):
            return
        t = open(h, encoding="utf-8", errors="ignore").read()
        new = t
        for fld in ("m1.QScores", "m2.QScores"):
            new = new.replace("%s == '\\0'" % fld, "(!%s || %s[0] == '\\0')" % (fld, fld))
        if new != t:
            with open(h, "w", encoding="utf-8") as fh:
                fh.write(new)
            self.output.info("[patch] MappingResult.h：char* 与 '\\0' 的比较改为 (!p || p[0]=='\\0')"
                             "（等价最小修正，语义不变）")

    def _patch_upstream_test(self):
        """上游 `PerMTest.cpp` 是**过时的**：它调用零参 `testLongBases2Colors()`，而该函数现在的签名是
        `(const char* longRead, const char* expLongColorSignals)`（`ColorSpaceRead.h:283`）。
        上游同文件里另有一个零参入口 `testLongBases2ColorsCases()`（`ColorSpaceRead.cpp:402`，
        内部用固定用例调两参版本）→ 把调用换成它，让上游自带测试**真能编、真能跑**
        （既不是跳过，也不是我另写测试）。
        """
        p = os.path.join(self._srcdir(), "PerMTest.cpp")
        if not os.path.isfile(p):
            return
        t = open(p, encoding="utf-8", errors="ignore").read()
        new = t.replace("testLongBases2Colors();", "testLongBases2ColorsCases();")
        if new != t:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(new)
            self.output.info("[patch] PerMTest.cpp：过时的零参调用 testLongBases2Colors() → "
                             "testLongBases2ColorsCases()（上游自己的零参入口），使该测试真能跑")

    def build(self):
        cxx = self._cxx()
        self._patch_ptr_char_compare()
        self._patch_upstream_test()
        # 上游 CC 里硬编码 g++，且 CFLAGS 带 -static（musl 下要不得）→ 覆盖 CC，顺带摘掉 -static/-fopenmp
        cc = "%s -O2 -Wall" % cxx
        self.run('make -j1 CC="%s"' % cc, cwd=self._srcdir())
        self._run_added_tests(cxx)

    # ── 上游自带测试程序：编出并真跑 ────────────────────────────────
    def _run_added_tests(self, cxx):
        src = self._srcdir()
        # PerMTest.cpp 自己也有 main → 用"除 PerM.cpp 外的全部源"编它（否则两个 main 冲突）
        cpps = sorted(f for f in os.listdir(src)
                      if f.endswith(".cpp") and f != "PerM.cpp")
        if "PerMTest.cpp" not in cpps:
            raise ConanInvalidConfiguration("[added tests] 上游 PerMTest.cpp 不存在，与预期不符")
        exe = os.path.join(src, "PerMTest")
        cmd = '"%s" -O2 -Wall -o "%s" %s -lm' % (cxx, exe, " ".join('"%s"' % c for c in cpps))
        self.output.info("[added tests] 编译上游测试程序：%d 个源文件" % len(cpps))
        r = self.run(cmd, cwd=src)
        p = subprocess.run([exe], cwd=src, capture_output=True, text=True, timeout=600)
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        if p.returncode != 0:
            raise ConanInvalidConfiguration(
                "[added tests] 上游 PerMTest 运行失败（rc=%d）：\n%s" % (p.returncode, out[-500:]))
        self.output.info("[added tests] ① 上游自带测试程序 PerMTest 编出并真跑通 ✓（rc=0，输出 %d 字节）"
                         % len(out))
        self.output.info("[added tests]    输出摘要：%s" % (out[-200:].replace("\n", " | ") or "（无输出）"))
        self.output.warning(
            "[added tests] ② 如实记录语义：上游 PerMTest.cpp 的 main() 只调用 testLongBases2Colors()"
            "并**固定 return 0**（不断言返回值）→ 本项只证明它可编、可跑通，不代表有 N 条断言全过")

    def package(self):
        binp = os.path.join(self.package_folder, "bin")
        os.makedirs(binp, exist_ok=True)
        exe = os.path.join(self._srcdir(), "perm")
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration("[package] 没找到构建产物 perm")
        copy(self, "perm", src=self._srcdir(), dst=binp, keep_path=False)
        # 上游 orig 里没有许可证文件（如实记录，不伪造）：有则带上，没有就在 README 里写清
        for lic in ("LICENSE", "COPYING", "README"):
            if os.path.isfile(os.path.join(self.source_folder, lic)):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
                break

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
