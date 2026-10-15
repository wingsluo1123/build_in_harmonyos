#!/usr/bin/env python3
"""HarmonyOS 专项测试 — k40-whisperer 0.71。

在 OHOS 设备 python3.12 上运行，使用**已安装**的 k40-whisperer 模块
（PYTHONPATH 指向 site-packages）。核心算法模块（egv/dxf/interpolate/
ecoords/convex_hull/g_code_library/LaserSpeed）为纯 stdlib 依赖，无
tkinter/lxml/PIL 要求，可独立导入验证。

GUI 主程序 k40_whisperer.py 在 OHOS 不可运行（如实说明，不编造 GUI 可用）：
- OHOS python/3.12.9 缺 _tkinter（模块级 `from tkinter import *` 即失败）
- svg_reader.py/inkex.py 硬依赖 lxml（ohpcd 仅 built 未发布）
因此本测试不覆盖 GUI，仅验证可在鸿蒙运行的算法核心 + 全量模块语法。

用法：test_k40_ohos.py <site-packages-dir>
任一断言失败即非零退出；全部通过打印 PASS 标记。
"""
import os
import sys


def _check_interpolate():
    from interpolate import interpolate
    f = interpolate([0, 10, 20], [0.0, 100.0, 200.0])
    assert f[5] == 50.0, f[5]          # 中点线性插值
    assert f[0] == 0.0, f[0]           # 左端点
    assert f[25] == 200.0, f[25]       # 超右端钳制
    try:
        interpolate([0, 0, 1], [0.0, 1.0, 2.0])
        raise AssertionError("interpolate should reject non-ascending x")
    except ValueError:
        pass


def _check_ecoords():
    from ecoords import ECoord
    ec = ECoord()
    ec.make_ecoords([[0.0, 0.0, 30.0, 40.0],    # 3-4-5 直角三角形（斜边 50 mil）
                     [30.0, 40.0, 30.0, 40.0]], # 零长段应被跳过
                    scale=1)
    assert abs(ec.len - 50.0) < 1e-6, ec.len    # 总切割长度 50
    assert ec.bounds == (0.0, 30.0, 0.0, 40.0), ec.bounds
    assert ec.move == 0.0, ec.move              # 连续路径无快速移动


def _check_laserspeed():
    from LaserSpeed import LaserSpeed
    code = LaserSpeed.get_code_from_speed(25.4, board="M2")  # 25.4 mm/s = 1 in/s
    assert code.startswith("CV") and "G" not in code, code
    spd = LaserSpeed.get_speed_from_code(code, board="M2")
    assert abs(spd - 25.4) < 0.5, spd           # 码→速度还原


def _check_convex_hull():
    from convex_hull import hull2D
    hull = hull2D().convex_hull([(0, 0), (1, 0), (0, 1), (1, 1), (0.5, 0.5)])
    assert len(hull) == 4, hull                 # 内部点被剔除
    assert set(hull) == {(0, 0), (1, 0), (0, 1), (1, 1)}, hull


def _check_egv():
    from egv import egv
    out = []
    e = egv(target=out.append)
    assert e.make_distance(10) == [106], e.make_distance(10)    # 10 mil -> 'j'
    assert e.make_distance(255) == [122], e.make_distance(255)  # 255 mil -> 'z'
    # 端到端：两条线段生成 EGV 字节流，含速度码头与结尾标记
    ecoords = [
        [0.0, 0.0, 1, 12.0, 1],
        [100.0, 0.0, 1, 12.0, 1],
        [100.0, 100.0, 2, 12.0, 1],
    ]
    e2 = egv(target=out.append)
    e2.make_egv_data(ecoords, startX=0, startY=0, units="in",
                     Feed=12.0, board_name="LASER-M2", Raster_step=0)
    data = bytes(out)
    assert data.startswith(b"CV"), data[:16]    # 速度码头
    assert data.endswith(b"FNSE"), data[-8:]    # 结尾标记
    assert b"FNSE" in data, data[:40]


def _check_gcode():
    from g_code_library import G_Code_Rip
    base = os.environ.get("TMPDIR") or os.getcwd()
    gcode = os.path.join(base, "k40_gcode_test.nc")
    with open(gcode, "w", encoding="ascii") as fh:
        fh.write("G0 X0 Y0\nG1 X10 Y10 F100 S1000\nM2\n")
    rip = G_Code_Rip()
    msgs = rip.Read_G_Code(gcode)
    os.unlink(gcode)
    assert not msgs, msgs                       # 无错误/警告
    moves = [l for l in rip.g_code_data
             if isinstance(l, list) and l and l[0] == 1]
    assert len(moves) == 1, moves               # 恰一条 G1 直线
    assert abs(moves[0][2][0] - 10.0) < 1e-9, moves[0]
    assert abs(moves[0][2][1] - 10.0) < 1e-9, moves[0]
    assert any(isinstance(l, list) and l and l[0] == "M2"
               for l in rip.g_code_data), rip.g_code_data


def _check_syntax_all(site):
    mods = 0
    for name in sorted(os.listdir(site)):
        if name.endswith(".py"):
            with open(os.path.join(site, name), "rb") as fh:
                compile(fh.read(), name, "exec")  # 不落盘字节码
            mods += 1
    assert mods >= 21, mods   # 21 个上游 .py 全部语法可编译


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_k40_ohos.py <site-packages-dir>")
    site = sys.argv[1]
    _check_interpolate()
    _check_ecoords()
    _check_laserspeed()
    _check_convex_hull()
    _check_egv()
    _check_gcode()
    _check_syntax_all(site)

    # GUI 平台现实（信息性，不因缺 _tkinter 断言失败——核心功能已验证）：
    try:
        import tkinter  # noqa: F401
        gui_note = "tkinter available"
    except ImportError:
        gui_note = ("tkinter NOT available (OHOS python3.12 lacks _tkinter) "
                    "-> GUI 不可运行（如实标注，不编造 GUI 可用）")

    sys.stdout.write("HARMONYOS-SPECIFIC-TEST PASS: interpolate/ecoords/"
                     "LaserSpeed/convex_hull/egv/g_code_library/py_compile ok\n")
    sys.stdout.write("k40-whisperer version: 0.71\n")
    sys.stdout.write("python: %s\n" % sys.version.split()[0])
    sys.stdout.write("gui: %s\n" % gui_note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
