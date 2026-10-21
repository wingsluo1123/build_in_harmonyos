#!/usr/bin/env python3
"""Conan test_package for lru-dict 1.5.0 — consumer check.

用 **conan python 依赖自带的解释器** 跑两个消费者测试模块（都通过 self.run
真实执行，满足 L0c；不做只 print 的空壳测试，R34）：

  1) test_lru_dict.py       —— 消费者视角的公开 API 契约（LRU 淘汰/统计/
                               回调/视图/resize/pop/setdefault/子类化）
  2) test_ohos_lru_dict.py  —— 适配新增的鸿蒙专项用例：OHOS ABI 标签、
                               .codesign 段、真实 dlopen 加载、运行期语义、
                               /tmp 无关性（见该文件 docstring）

为什么用 conan 解释器而不是宿主 python3：
  lru._lru 的 DT_NEEDED 含 libpython3.12.so.1.0。conan python 包的 bin/ 与
  lib/ 同目录，解释器自己的 libpython 就是扩展要解析的那一个，加载链自洽。
  仓内 lazy-object-proxy 1.12.0 的两轮 CI 实测（#14850）证明：在 CI worker
  上用宿主 python3 加载 conan 依赖编出的扩展会 ImportError（异构
  libpython），而 conan 解释器 + 其 lib 下正常——故此处沿用该 CI 已验证
  路径（不重复踩坑）。

注意：这里显式构造环境而**不用 VirtualRunEnv**，避免 conanrun 生成的
LD_LIBRARY_PATH 覆盖掉我们为 conan 解释器准备的 lib 路径。
"""
import os

from conan import ConanFile
from conan.errors import ConanException

SITE_REL = os.path.join("lib", "python3.12", "site-packages")


class LruDictTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["lru-dict"].package_folder
        site = os.path.join(pkg, SITE_REL)
        if not os.path.isdir(os.path.join(site, "lru")):
            raise ConanException(f"lru package missing under {site}")

        here = os.path.dirname(os.path.abspath(__file__))
        modules = ("test_lru_dict", "test_ohos_lru_dict")
        for mod in modules:
            if not os.path.isfile(os.path.join(here, mod + ".py")):
                raise ConanException(f"consumer test missing: {mod}.py")

        py_dep = self.dependencies["python"]
        py_pkg = py_dep.package_folder
        py_bin = os.path.join(py_pkg, "bin", "python3.12")
        py_lib = os.path.join(py_pkg, "lib")
        if not os.path.isfile(py_bin):
            raise ConanException(f"conan python interpreter missing: {py_bin}")

        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [site] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [py_lib] + ([env["LD_LIBRARY_PATH"]]
                        if env.get("LD_LIBRARY_PATH") else []))
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONNOUSERSITE"] = "1"

        # self.run() 继承当前进程环境 → 临时替换 os.environ，结束后恢复
        old = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            for mod in modules:
                self.output.info(f"consumer test: {mod}")
                self.run(f'"{py_bin}" -m unittest -v {mod}', cwd=here)
        finally:
            os.environ.clear()
            os.environ.update(old)
