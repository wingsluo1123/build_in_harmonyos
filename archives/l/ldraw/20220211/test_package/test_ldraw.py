#!/usr/bin/env python3
"""ldraw 消费侧校验脚本（由 test_package/conanfile.py 调用）。

用法: python3 test_ldraw.py <package_folder>

对纯数据包而言，"真实消费"就是像 LDraw 渲染/查看应用那样读取安装后的
零件库数据并校验可用性（等价于应用启动时定位 LDRAW 库路径并加载零件）。

用例：
  1. share/ldraw/parts 存在且零件数 > 30000（官方完整库规模）
  2. 随机抽检 5 个 .dat 零件：文件存在、首行以 '0 ' 开头（LDraw 元命令行）
  3. LDConfig.ldr 存在且含颜色码行（如 '4 4 255 0 0' 红色）
  4. share/ldraw/models 存在（官方样例模型）

退出码: 0 = 全部通过; 1 = 存在失败用例。
"""
import os
import random
import sys

LDRAW_RELPATH = os.path.join("share", "ldraw")

results = []


def check(name, func):
    try:
        func()
    except Exception as exc:  # noqa: BLE001 汇总报告
        results.append((name, False, str(exc)))
        print(f"  [FAIL] {name}: {exc}")
    else:
        results.append((name, True, ""))
        print(f"  [PASS] {name}")


def main():
    pkg = sys.argv[1]
    ldraw_dir = os.path.join(pkg, LDRAW_RELPATH)
    parts_dir = os.path.join(ldraw_dir, "parts")

    def c_parts_exist():
        n = 0
        for root, _, files in os.walk(parts_dir):
            n += len(files)
        if n <= 30000:
            raise AssertionError(f"parts 数量不足: {n}")
        print(f"        零件文件数: {n}")

    def c_part_readable():
        dat_files = []
        for root, _, files in os.walk(parts_dir):
            for f in files:
                if f.lower().endswith(".dat"):
                    dat_files.append(os.path.join(root, f))
        if len(dat_files) < 30000:
            raise AssertionError(f".dat 零件不足: {len(dat_files)}")
        for p in random.sample(dat_files, 5):
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                first = fh.readline().strip()
            if not first.startswith("0 "):
                raise AssertionError(f"首行非 LDraw 元命令: {p} -> {first[:40]!r}")
        print(f"        抽检 5 个 .dat 首行均合法 (共 {len(dat_files)})")

    def c_ldconfig():
        ld = os.path.join(ldraw_dir, "LDConfig.ldr")
        if not os.path.isfile(ld):
            raise AssertionError("LDConfig.ldr 缺失")
        with open(ld, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        # LDraw 官方颜色定义格式：!COLOUR Red CODE 4 VALUE #B40000 ...
        if "!COLOUR Red" not in content or "CODE 4" not in content:
            raise AssertionError("未找到官方红色颜色定义 '!COLOUR Red CODE 4'")

    def c_models():
        m = os.path.join(ldraw_dir, "models")
        if not os.path.isdir(m):
            raise AssertionError("models/ 目录缺失")

    check("parts 完整库规模 (>30000)", c_parts_exist)
    check(".dat 零件可读且格式合法 (抽检 5)", c_part_readable)
    check("LDConfig.ldr 颜色定义", c_ldconfig)
    check("models 样例目录", c_models)

    failed = [r for r in results if not r[1]]
    print(f"\nldraw 消费侧校验: {len(results)-len(failed)}/{len(results)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
