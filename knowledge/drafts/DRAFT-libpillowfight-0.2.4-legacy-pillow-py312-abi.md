# DRAFT — 旧版 Pillow（5.0/6.0 时代）sdist 在 python 3.12 上可编译但运行期不可用（ABI 崩溃/解码失效）

- **软件**：libpillowfight 0.2.4
- **任务**：`libpillowfight-0.2.4-r06-historical-2018-stack-replication-pc1-35-20261015T120000Z`
- **状态**：DRAFT（配对 `DRAFT-libpillowfight-0.2.4-legacy-pillow-py312-abi.kv`）
- **编号**：`DRAFT-libpillowfight-0.2.4-legacy-pillow-py312-abi`（待人工审核后分配正式 E 编号）

## 1. 现象

为复现上游参考图生成环境（issue #15 指向 2018 年 PyPI wheel Pillow 5.0 时代），在 python 3.12
设备上构建旧版 Pillow sdist：Pillow 5.0.0/6.0.0 均**编译成功**（`pip install` 通过、import 通过），
但**运行期不可用**：
- Pillow 5.0.0：解码 JPEG 时 `Signal 11 (core dumped)`（C 扩展 ABI 崩溃；此前还报
  `PY_SSIZE_T_CLEAN macro must be defined` 与 `collections.MutableMapping` 缺失）
- Pillow 6.0.0：`OSError: cannot identify image file ...jpg`（JPEG 解码器未生效）

## 2. 根因

2018 时代 Pillow C 扩展按 python 3.6 时代 C-API 编写：python 3.12 上 ①`'#'` 格式需
`-DPY_SSIZE_T_CLEAN`、`collections.MutableMapping` 已迁移到 `collections.abc`；②即便编译期
补丁+运行期 shim 通过，ABI 不兼容仍在解码路径崩溃（5.0 段错误 / 6.0 解码器失效）。
即**"构建成功 ≠ 运行期可用"**：参考环境（2018 Pillow + python 3.6 时代）在本平台结构性不可复现，
字节等值链条（同版本 Pillow + 同编码器）无法建立。

## 3. 设备可执行复现

```sh
python3 -m venv v; v/bin/pip install Pillow-5.0.0.tar.gz   # 编译成功
v/bin/python3 -c "import PIL; print(PIL.__version__)"      # 5.0.0 可导入
v/bin/python3 -c "from PIL import Image; Image.open('x.jpg')"  # Signal 11 / cannot identify
```

## 4. 处置（libpillowfight R06 实测）

- 历史栈复现前先做**运行期可用性验证**（实际解码一张 JPEG），失败原文（Signal 11 /
  cannot identify）即"已尝试"证据；按任务规则降级或转入证据链裁决，不得把构建成功当栈可用。
- 构建失败先核对旧版 Pillow setup.py 环境变量语义：5.0/6.0 仅从 **CFLAGS/LDFLAGS**（非
  CPPFLAGS）解析 `-I/-L`（本任务 Pillow 5.0 初两次用 CPPFLAGS 致 jpeg 探测失败，改 CFLAGS 即成功）。
- 结论支撑：R06 oracle（tests_blackfilter）在历史栈无命中且不可运行 → 最优可运行栈（统一基线）
  复跑 2/15，残余证据链 + issue #15 上游环境敏感性取证交最终裁决。

## 5. 边界与反例

- **与 E062/E065/E075/E113/E158 的区别**：均为头文件/CFLAGS/依赖类构建期问题；本条是运行期
  ABI 崩溃/解码失效。
- **反例**：python 3.10 以下运行旧版 Pillow 通常可用（ABI 兼容），无需本路径。
- **限制**：编译成功不得视为可用；必须运行期验证后再下命中/未命中结论。

## 6. 复用提示

凡"历史版本栈复现/上游参考环境还原"场景（字节等值图像测试返工）：先验证旧版 C 扩展 sdist 在
当前 python 的**运行期可用性**（实际解码），失败原文即已尝试证据；构建失败先核对 setup.py 的
CFLAGS/LDFLAGS（非 CPPFLAGS）语义。

## 7. 复现证据（本任务）

| 项 | 值 |
|---|---|
| Pillow 5.0.0 | 官方 sdist sha256 12f29d6c…（校验一致）；编译成功；运行期 Signal 11（pillow500-build1-4.log） |
| Pillow 6.0.0 | 官方 sdist sha256 809c0a2c…；编译成功；cannot identify image file（pillow600-build.log） |
| 环境变量语义 | CFLAGS（非 CPPFLAGS）携带 -I/-L 后 jpeg 探测通过（setup.py 5.0 源码第 262-268 行） |
| oracle 结论 | 历史栈无命中且不可运行（oracle-discrimination.md），统一基线 2/15 |
