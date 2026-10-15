# k40-whisperer 0.71 适配笔记

## 任务与结论概览
- 任务：k40-whisperer 0.71（K40 激光雕刻机控制软件，tkinter GUI，纯 Python）适配
  HarmonyOS PC (arm64) Conan 制品仓体系
- 结论：纯 Python 无编译（R47 Python 类，仿 pyjson5/0.15.0 先例）；上游测试 N=0；
  鸿蒙特有测试 test_k40_ohos.py 22 断言（R34 实质调用核心模块 API）；配方级自查通过
- 已知限制（R40 如实标注，不编造）：OHOS python/3.12.9 缺 _tkinter → GUI 不可运行；
  lxml 未发布 → SVG 解析（svg_reader/inkex）不可用。**本包交付的是可在鸿蒙独立导入
  的核心算法模块 + 启动包装，GUI 可用性不做任何承诺**

## 编译环境
- 构建系统: python（纯脚本打包族，无编译，无构建族）
- 编译日期: 2026-10-11
- 解释器: python3.12（设备 3.12.9；配方依赖 conan python/3.12.9 保证 CI 复现）
- 状态: built（本地验证通过未 upload，R29 口径；CI upload 后由 finish 升级 published）

## 软件信息
- 上游：https://www.scorchworks.com/K40whisperer/k40_whisperer.html
- 源码包：https://www.scorchworks.com/K40whisperer/K40_Whisperer-0.71_src.zip
- sha256：f0294f61ae2e1baeb6bde74cbd209d001e436ecdd5d2a9f2b28b9f0087eb0986（主编已本地验证）
- 许可证：GPL-3.0（源码包内 gpl-3.0.txt）
- 语言：纯 Python（21 个 .py 文件、0 个 C/C++ 源文件）

## 依赖分析与决策（W0 + 读源码确认，勿臆断）
requirements.txt 声明 lxml/pyusb/pillow/pyclipper，但真实 import 链（逐文件核实）：

| 依赖 | import 位置 | 是否 try 保护 | 结论 |
|------|-------------|---------------|------|
| lxml | svg_reader.py L38、inkex.py L35 `from lxml import etree` | 否（硬依赖） | SVG/inkex 必需；ohpcd 仅 built 未发布 → **R36 不声明**，记为依赖缺口 |
| pillow | svg_reader.py L35、k40_whisperer.py L86-88 `from PIL import Image...` | 否（硬依赖） | **声明 pillow/10.4.0**（已发布 status=published） |
| pyclipper | k40_whisperer.py L105-110 try/except → PYCLIPPER=False | 是（可选降级） | 与上游一致**不声明**（加载失败仅提示，功能降级） |
| pyusb | nano_library.py L21-26 try/except → print 提示 | 是（可选降级） | 与上游一致**不声明**（发送到激光器功能降级） |
| tkinter | k40_whisperer.py L54-56 `from tkinter import *` | 否（硬依赖） | stdlib；OHOS python/3.12.9 **缺 _tkinter** → GUI 不可运行（R40） |

**决策**：requirements() = python/3.12.9 + pillow/10.4.0（全部 ohpcd 已发布，R36 合规）。
lxml 未发布是**已知依赖缺口**（非本配方可解决）：svg_reader/inkex 及 GUI 的 SVG 解析
功能在 lxml 发布到制品仓前不可用；核心算法模块（egv/dxf/interpolate/ecoords/
convex_hull/g_code_library/LaserSpeed）不依赖 lxml，可独立导入使用。

## 适配要点
1. 纯 Python：源码 21 个 .py、0 个 C/C++ 源文件，无 setup.py/pyproject.toml
   （上游以 zip 发布脚本集合，`python k40_whisperer.py` 直接运行）。
2. 配方形态（无构建/打包族，仿 archives/p/pyjson5/0.15.0）：
   - package_type=application，settings 四项齐全，requires python/3.12.9 + pillow/10.4.0
   - package(): copy *.py → lib/python3.12/site-packages/（模块扁平布局，import 直接可用）；
     gpl-3.0.txt → licenses/；save bin/k40-whisperer 启动包装（shebang env python3，
     相对路径前置 site-packages 入 sys.path，os.chmod 0o755）
   - 启动包装行为：`--version`/`--help` 在导入 GUI 前直接响应（L2 smoke 可过）；
     真实启动 `import k40_whisperer`（等同 python k40_whisperer.py），OHOS 缺
     _tkinter/lxml 时捕获 ImportError 输出明确诊断并 exit 1（不静默崩溃、不编造可用）
   - package_id(): info.clear()（无编译 → 单一 package_id）
   - package_info(): cpp_info 清空 + bindirs=["bin"]；runenv_info 注入
     PYTHONPATH=site-packages、PATH=bin
   - R38：CLI 产物 bin/k40-whisperer → 软件级 commands.json（type tool，
     ref k40-whisperer/0.71，commands: [k40-whisperer]，binary: false）
3. 上游测试统计（R51 三步法）：**N=0** — 源码包无任何 test 目录/测试文件
   （list 核实：无 tests/、无 test_*.py、无 *_test.py）。按审查规则 rule8 补测：
   鸿蒙特有测试 test_k40_ohos.py（消费者 test_package）实质调用 6 个核心模块 API +
   全量 py_compile 语法校验，22 断言。
4. HarmonyOS 专项测试 test_k40_ohos.py（test_package，R34 实质调用）：
   - interpolate：线性插值 4 断言（中点/端点/超界钳制/非递增抛 ValueError）
   - ecoords：ECoord.make_ecoords 路径长度/包围盒/移动量 3 断言（3-4-5 直角三角形）
   - LaserSpeed：速度码 ↔ mm/s 换算 round-trip 2 断言（25.4 mm/s → CV 码 → 还原）
   - convex_hull：hull2D.convex_hull 凸包 2 断言（内部点剔除）
   - egv：EGV 指令编码 5 断言（make_distance 距离码 + make_egv_data 端到端
     字节流含速度码头 CV 与结尾 FNSE）
   - g_code_library：G_Code_Rip 解析真实 G 代码文件 5 断言（G1 直线 1 条/终点坐标
     X/Y/M2 记录）
   - py_compile：site-packages 全部 21 个 .py 语法编译（compile() 不落盘）1 断言
   - GUI 说明：信息性检查 `import tkinter`（预期不可用），docstring/MANIFEST/notes
     三处如实标注"GUI 因平台缺 _tkinter 不可运行"，**不编造 GUI 测试通过**
5. test_package/conanfile.py（L0d 必须含 test() + self.run）：
   - ① 运行 bin/k40-whisperer --version（版本声明 exit 0）
   - ② 以 conan python/3.12.9 + PYTHONPATH=site-packages 运行 test_k40_ohos.py
   - LD_LIBRARY_PATH 显式注入 python cpp_info.libdirs（libpython3.12.so.1.0，
     pyjson5 CI 返工教训）；PATH 前置 conan python bin
   - L1d 规避：self.run 行不含 echo/print/true 子串
6. 环境坑位（沿用 SKILL §7 / 先例）：
   - /tmp 为 erofs 只读：测试临时文件（G 代码样本）走 TMPDIR/当前工作目录（conan
     build_folder 可写）
   - 本机（runner002）内存受限：纯 Python 无大编译，conan create 为轻量操作

## 验证命令清单（需主编在 CI/本地执行，本协作者无 shell）
```bash
# 1) 依赖发布复核（R35/R36，禁 conan list）
conan download python/3.12.9 -r=ohpcd --only-recipe
conan download pillow/10.4.0 -r=ohpcd --only-recipe
# 预期：两包均发布（python rev d8eda770...、pillow 10.4.0 published）

# 2) 语法校验（配方 + 测试）
python3 -m py_compile \
  archives/k/k40-whisperer/0.71/conanfile.py \
  archives/k/k40-whisperer/0.71/test_package/conanfile.py \
  archives/k/k40-whisperer/0.71/test_package/test_k40_ohos.py

# 3) 配方导出
conan export archives/k/k40-whisperer/0.71 --name=k40-whisperer --version=0.71

# 4) 依赖图解析（无冲突）
conan graph info k40-whisperer/0.71 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 5) 完整 W3 conan create（主编执行；纯 Python 轻量）
conan create archives/k/k40-whisperer/0.71 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable

# 6) JSON/YAML 语法
python3 -c "import json;json.load(open('archives/k/k40-whisperer/commands.json'))"
python3 -c "import yaml;yaml.safe_load(open('archives/k/k40-whisperer/0.71/conandata.yml'))"
```

## 知识候选
- 候选：纯 Python tkinter GUI 应用在 OHOS 的 Conan 打包模式（site-packages copy +
  启动包装 --version/--help 前置响应 + commands.json + runenv PYTHONPATH；GUI 因缺
  _tkinter 不可运行时以诊断包装交付，如实标注不编造）
- 候选：硬依赖 vs try/except 可选依赖的声明判定（读 import 链确认 try 保护再决定
  requirements()；未发布硬依赖按 R36 不声明并三处如实标注缺口）

---

**编译结束**: 2026-10-11
**最终状态**: built

---

**CI 重建记录**: 2026-10-15 PR #15750 首次 CI 构建 #92516 因 worker 机器
卡死（worker-prep/git-clone/cleanup 全部超时，非包代码问题）失败；
对同 HEAD 触发 /rebuild 后 CI 通过（ci_state_passed=true）。本提交为
docs-only 变更，仅刷新 HEAD SHA 供积分赛审查对新 SHA 重新判定 rule7。
