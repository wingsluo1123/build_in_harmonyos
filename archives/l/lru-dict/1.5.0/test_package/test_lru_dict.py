#!/usr/bin/env python3
"""消费者视角的公开 API 契约测试 — lru-dict 1.5.0（已安装产物）。

与上游 test/test_lru.py 的区别：上游用例跑在**源码树**里（验证实现），本
文件跑在 **site-packages 产物**上（验证「装出来的包能被消费者正确使用」，
即 R34 要求的实质依赖被测包）。用例覆盖面按消费者最常用的公开 API 选取，
不逐条复制上游 26 个用例。

同时充当 test_package 的 L0c 实体：由 conanfile.test() 通过 self.run 真实
执行，可单独运行：
    <python> -m unittest -v test_lru_dict
"""
import sys
import unittest

import lru


class TestLruDictConsumerAPI(unittest.TestCase):
    def test_exports_lru_class(self):
        self.assertTrue(hasattr(lru, "LRU"))
        self.assertEqual(lru.__all__, ["LRU"])

    def test_invalid_capacity_rejected(self):
        for bad in (-1, 0):
            with self.assertRaises(ValueError):
                lru.LRU(bad)

    def test_basic_set_get_and_len(self):
        d = lru.LRU(4)
        for i in range(4):
            d[i] = str(i)
        self.assertEqual(len(d), 4)
        for i in range(4):
            self.assertEqual(d[i], str(i))

    def test_eviction_is_least_recently_used(self):
        d = lru.LRU(2)
        d["a"] = 1
        d["b"] = 2
        _ = d["a"]              # 触碰 a → b 成为最久未用
        d["c"] = 3
        self.assertEqual(sorted(d.keys()), ["a", "c"])
        self.assertFalse(d.has_key("b"))

    def test_views_and_peek(self):
        d = lru.LRU(3)
        d[1] = "1"
        d[2] = "2"
        self.assertEqual(d.keys(), [2, 1])
        self.assertEqual(d.values(), ["2", "1"])
        self.assertEqual(d.items(), [(2, "2"), (1, "1")])
        self.assertEqual(d.peek_first_item(), (2, "2"))
        self.assertEqual(d.peek_last_item(), (1, "1"))
        # peek 不改变使用顺序
        self.assertEqual(d.keys(), [2, 1])

    def test_missing_key_semantics(self):
        d = lru.LRU(2)
        d[1] = "1"
        with self.assertRaises(KeyError):
            _ = d[99]
        self.assertIsNone(d.get(99))
        self.assertEqual(d.get(99, "dflt"), "dflt")
        with self.assertRaises(KeyError):
            del d[99]

    def test_setdefault(self):
        d = lru.LRU(2)
        d[1] = "1"
        self.assertEqual(d.setdefault(1), "1")
        self.assertEqual(d.setdefault(2, "2"), "2")
        self.assertEqual(d[2], "2")

    def test_update_from_mapping_and_kwargs(self):
        d = lru.LRU(4)
        d.update({"a": 1, "b": 2})
        self.assertEqual(d["a"], 1)
        d.update(a=3)
        self.assertEqual(d["a"], 3)
        d.update()
        self.assertEqual(d["a"], 3)

    def test_pop_and_popitem(self):
        d = lru.LRU(3)
        for i in (1, 2, 3):
            d[i] = str(i)
        self.assertEqual(d.pop(2), "2")
        self.assertEqual(d.pop(99, "fallback"), "fallback")
        k, v = d.popitem()                       # 默认淘汰最久未用
        self.assertEqual((k, v), (1, "1"))
        self.assertEqual(d.popitem(least_recent=False), (3, "3"))
        with self.assertRaises(KeyError):
            d.popitem()

    def test_size_get_set_and_clear(self):
        d = lru.LRU(3)
        self.assertEqual(d.get_size(), 3)
        for i in range(5):
            d[i] = str(i)
        d.set_size(5)
        self.assertEqual(d.get_size(), 5)
        d.set_size(2)
        self.assertEqual(len(d), 2)
        d.clear()
        self.assertEqual(len(d), 0)

    def test_stats_track_hits_and_misses(self):
        d = lru.LRU(2)
        d[1] = "1"
        _ = d[1]
        _ = d.get(1)
        _ = d.get(99)
        with self.assertRaises(KeyError):
            _ = d[99]
        self.assertEqual(d.get_stats(), (2, 2))

    def test_eviction_callback(self):
        evicted = []
        d = lru.LRU(2, callback=lambda k, v: evicted.append((k, v)))
        d["a"] = 1
        d["b"] = 2
        d["c"] = 3
        self.assertEqual(evicted, [("a", 1)])
        d.set_callback(None)
        d["d"] = 4                    # callback 已解绑 → 不再记录
        self.assertEqual(evicted, [("a", 1)])
        self.assertEqual(len(d), 2)

    def test_unhashable_key_rejected(self):
        d = lru.LRU(2)
        with self.assertRaises(TypeError):
            _ = d[{"a": "b"}]
        with self.assertRaises(TypeError):
            d[["x"]] = 1

    def test_subclassing(self):
        class Child(lru.LRU):
            pass

        c = Child(2)
        c["k"] = "v"
        self.assertEqual(c["k"], "v")
        self.assertIsInstance(c, lru.LRU)

    def test_loaded_from_packaged_site_packages(self):
        """消费者加载的必须是产物（而非源码树 / 系统安装）里的模块。"""
        ext = lru._lru.__file__
        self.assertIn("site-packages", ext.replace("\\", "/"),
                      f"extension not loaded from an installed package: {ext}")
        print(f"  consumer loaded: {ext} (python {sys.version.split()[0]})")


if __name__ == "__main__":
    unittest.main(verbosity=2)
