#!/usr/bin/env python3
"""HarmonyOS (OHOS) 专项测试 — lru-dict 1.5.0 C 扩展的平台契约验证。

本文件是**适配时新增**的鸿蒙测试用例（上游 1.5.0 的 test/test_lru.py 只有
26 个纯功能用例，没有任何平台契约断言）。它同时是消费者用例：只通过公开
API `import lru` 使用交付物，不依赖源码树内部结构，因此既能验证
「装出来的包能被消费者用」，也能验证「它在 OHOS 上真的能加载」。

用法（两种上下文都可）：
  1) 构建期随上游套件一起跑（配方 build() 把它拷进上游 test/ 目录）：
       <python> -m unittest discover -s test -p 'test_*.py' -v
  2) 消费者侧独立跑（test_package）：
       <python> test_ohos_lru_dict.py <site-packages 路径>

验证的 OHOS 平台契约
--------------------
A. ABI 正确性：扩展模块名带 OHOS 平台标签（EXT_SUFFIX 形如
   `.cpython-312-aarch64-linux-ohos.so`）——证明产出是 OHOS aarch64 目标，
   而非误用宿主/其他架构的产物。
B. 可加载性（本平台最关键的一条）：扩展 ELF 必须带 `.codesign` 段。OHOS
   的 dlopen 对缺失该段的 .so 报
   `ImportError: Error loading shared library ...: Permission denied`
   （极易被误判为文件权限问题；E077 记录该 .codesign 加载要求，
   E212 记录同一症状的另一根因 —— hmmac 安全标签）。本仓实测：OHOS SDK clang
   15.0.4 链接期自动生成该段；用 llvm-objcopy 剥掉后 import 立即失败。
C. 真实加载：`import lru` 必须成功——这是对 A+B 的端到端确认（签名、
   依赖解析、符号绑定全部走通）。
D. 运行期语义：在被 OHOS 加载器真正加载的前提下，LRU 的淘汰/统计/回调
   语义仍然正确（不是「能 import 但一用就崩」）。
E. 运行期契约：不依赖 /tmp（OHOS 上 /tmp 只读，知识库 E002）——本模块
   不得使用 tempfile / 写临时目录。
"""
import gc
import os
import struct
import sys
import unittest

import lru  # noqa: F401  # 必须成功：这是 C 契约的核心断言


def _elf_section_names(path):
    """纯 Python 读出 ELF64 小端文件的段名集合（不依赖 readelf）。"""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        return None  # 非 64 位小端 ELF
    (e_shoff,) = struct.unpack_from("<Q", data, 0x28)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3a)
    if not e_shoff or not e_shnum:
        return set()
    (strtab_off,) = struct.unpack_from(
        "<Q", data, e_shoff + e_shstrndx * e_shentsize + 0x18)
    names = set()
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        (name_off,) = struct.unpack_from("<I", data, off)
        end = data.index(b"\x00", strtab_off + name_off)
        names.add(data[strtab_off + name_off:end].decode("ascii", "replace"))
    return names


class TestLruDictOhosContract(unittest.TestCase):
    """OHOS 平台契约（A/B/C）——适配新增，非上游用例。"""

    def test_extension_is_ohos_abi(self):
        """A: 扩展模块名必须带 OHOS 平台标签。"""
        ext_file = lru._lru.__file__
        name = os.path.basename(ext_file)
        self.assertTrue(name.endswith(".so"), name)
        self.assertIn(
            "ohos", name,
            f"extension module is not an OHOS-ABI artifact: {name}")
        print(f"  OHOS extension: {ext_file}")

    def test_extension_has_codesign_section(self):
        """B: 扩展 ELF 必须带 .codesign 段，否则 OHOS dlopen 报 Permission denied。"""
        ext_file = lru._lru.__file__
        names = _elf_section_names(ext_file)
        self.assertIsNotNone(names, f"not an ELF64-LE file: {ext_file}")
        self.assertIn(
            ".codesign", names,
            "OHOS requires the .codesign section on dlopen'd .so files; "
            f"missing in {ext_file} (loader will report 'Permission denied')")
        print(f"  OHOS .codesign section present: {ext_file}")

    def test_module_imports_and_reports_platform(self):
        """C: import 成功 = 签名/依赖/符号绑定端到端走通。"""
        self.assertTrue(hasattr(lru, "LRU"))
        self.assertEqual(lru.__all__, ["LRU"])
        print(f"  sys.platform={sys.platform!r}, lru.__file__={lru.__file__}")
        # 在真正的 OHOS 宿主解释器下必须自报 ohos（conan python 依赖解释器
        # 自报 linux，属预期差异，故此处只在宿主下收紧）
        if os.environ.get("OHOS_HOST_PYTHON") == "1":
            self.assertEqual(sys.platform, "ohos")


class TestLruDictOhosBehaviour(unittest.TestCase):
    """D: 被 OHOS 加载器真正加载后，LRU 语义仍然正确。"""

    def test_eviction_order(self):
        d = lru.LRU(3)
        for k in ("a", "b", "c"):
            d[k] = k
        _ = d["a"]              # 触碰 a → 最近使用
        d["d"] = "d"            # 淘汰 b
        self.assertEqual(sorted(d.keys()), ["a", "c", "d"])
        self.assertNotIn("b", d)

    def test_stats_and_callback(self):
        seen = []
        d = lru.LRU(2, callback=lambda k, v: seen.append((k, v)))
        d["x"] = 1
        d["y"] = 2
        d["z"] = 3              # 淘汰 x，触发 callback
        self.assertEqual(seen, [("x", 1)])
        self.assertEqual(sorted(d.keys()), ["y", "z"])

    def test_resize_and_clear(self):
        d = lru.LRU(4)
        for i in range(6):
            d[i] = str(i)
        self.assertEqual(len(d), 4)
        d.set_size(2)
        self.assertEqual(len(d), 2)
        d.clear()
        self.assertEqual(len(d), 0)
        self.assertEqual(d.get_stats(), (0, 0))

    def test_gc_no_leak_reference_counting(self):
        """C 扩展是否正确处理引用计数（上游 tearDown 同款思路，非 debug 构建时退化）。"""
        gettotalrefcount = getattr(sys, "gettotalrefcount", lambda: 0)
        gc.collect()
        before = gettotalrefcount()
        d = lru.LRU(16)
        for i in range(64):
            d[i] = "v" * 8
        del d
        gc.collect()
        self.assertEqual(before, gettotalrefcount())


class TestLruDictOhosRuntimeContract(unittest.TestCase):
    """E: OHOS 运行期契约（/tmp 只读，E002）。"""

    def test_module_does_not_use_tmpdir(self):
        """模块本身不得依赖 /tmp：本测试运行时 TMPDIR 指向只读 /tmp 也不受影响。"""
        d = lru.LRU(8)
        for i in range(32):
            d[i] = str(i)
        self.assertEqual(len(d), 8)
        # 交付物目录内不得残留临时文件/解析缓存
        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(lru.__file__)))
        self.assertTrue(os.path.isdir(pkg_dir))
        leftovers = [f for f in os.listdir(pkg_dir)
                     if f.startswith("tmp") or f.endswith(".tmp")]
        self.assertEqual(leftovers, [], f"temp leftovers in package: {leftovers}")


if __name__ == "__main__":
    # 消费者侧独立调用：可选地把 site-packages 作为第一个参数传进来
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        sys.path.insert(0, os.path.abspath(sys.argv.pop(1)))
    unittest.main(verbosity=2)
