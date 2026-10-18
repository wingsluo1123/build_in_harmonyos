# SKILL: meson 直驱交叉配方陷阱检测与两步法预防（meson-cross-pkgconfig）

> 版本 1.0.0 · 适用 OHOS PC（aarch64）三方库适配流程 · Conan 2.x + meson 上游
> 定位：把「lv2/drobilla 生态 meson 库交叉适配的 G2 修复循环」（sratom 实测
> 5 轮）压缩成**建配方前一次廉价检测 + 模板直抄**。一次入库、多次复用。

## 1. 一句话说明

上游用 meson 的 C 库在 conan 交叉配方里有一族高概率踩坑点（库形态选项
缺失、pkg-config 子 shell 不稳、传递依赖 .pc 不生成、源下载被钉死、库实体
名带版本后缀）。本 SKILL 做三件事：

1. **识别**：三通道检测——L1 构建日志特征归因 / L2 配方反模式预检 /
   L3 conan 环境陷阱（源下载钉死）；
2. **给策略**：`templates/conanfile-meson-two-step.tmpl` 两个可直接抄的
   模板块（配方 build() + test_package 两步法），注释内嵌实证记录；
3. **可复现**：`tests/repro_meson_cross_trap.sh` A/B 双向验证（关策略
   复现原始报错 / 开策略走通），`TRAP_REPRODUCED_*` →
   `FIX_CONFIRMED_*` → `REPRO_SCRIPT_EFFECTIVE=yes`。

## 2. 问题机理（五坑一陷阱，全部实测）

| # | 坑 | 实测报错形态 | 策略 |
|---|-----|------------|------|
| ① | 上游 meson_options.txt 无 `shared` 选项 | `ERROR: Unknown option: "shared"` | 库形态用 `--default-library=shared\|static` 全局开关 |
| ② | `--default-library` 只收 shared/static | `invalid choice: 'false'` | conan bool 映射 `true→shared / false→static` |
| ③ | self.run 内嵌套 `"$(pkg-config ...)"` 子 shell 在 conan 沙箱不稳（内层失败被吞，flags 空串静默进编译命令） | 头文件/库全找不到的连锁报错 | **两步法**：pkg-config 输出落盘文件 → Python 读回字面量 flags |
| ④ | 传递依赖不生成 .pc（仅显式 requires 的包才生成） | `Package lv2 was not found in the pkg-config search path` | test_package 显式 `requires` 每个直接消费头文件域的包 |
| ⑤ | lv2 生态库实体名带版本后缀 | `unable to find library -lzix`（实体是 libzix-0） | 兜底 `-l` 前先 ls 依赖 lib 目录核实命名 |
| ⊕ | HMDFS exec 陷阱（E046 族延伸） | `Error loading shared library liblilv-0.so.0`（destdir 重写版加载失败，ld 直出版正常） | 验证用构建目录 ld 直出版；探测工具勿信 `[ -x ]`（属主映射恒 False），用实际执行验证 |

环境侧独立坑：`~/.conan2/global.conf` 的 `core.sources:download_urls`
钉死本地 backup 源时，新包 source() 直接 `NotFoundException`（未回退原始
URL）——临时注释跑验证，完成后还原。

## 3. 适用范围

### 3.1 适用

| 场景 | 表现 |
|------|------|
| 新适配 meson 构建 C/C++ 库（尤其 lv2/drobilla 生态：sratom/lilv/serd/sord/suil/zix 族） | 配方首次 conan-verify G2 失败 |
| 建配方前预检（W0/conan-init 后） | `--recipe conanfile.py` 扫反模式 |
| CI 红后归因（R44 diagnose 二次分类） | `--log conan-create.log` 出处方 |
| 新机器/新工作区环境确认 | `--env` 查源下载钉死 |

### 3.2 实证样例（一类问题，≥2 例）

| 样例库 | 踩坑 | 结果 |
|--------|------|------|
| sratom 0.6.22（首例，全踩） | ①②③④⑤⊕ 全中，G2 修复循环 5 轮 | 策略逐条固化（见 samples/sample-g2-failure-sequence.log） |
| lilv 0.28.0（第 2 例，迁移验证） | 套用同套策略，仅⊕源下载坑重现 | G2 一次通过——策略可迁移性证明 |
| jalv 1.10.0（第 3 例在途） | 同生态同构建系统宿主程序 | 待依赖合并后适配 |

### 3.3 不适用

| 情形 | 原因 |
|------|------|
| 上游非 meson（autotools/cmake） | 各有专属模板；本 SKILL 特征串不会命中 |
| 上游 meson_options.txt 自带 shared 选项 | 坑①②不存在，但③④⑤仍适用（按检测结果取舍） |
| 非 lv2 生态的库实体命名 | 坑⑤的正则会命中但建议仅作提示；兜底前核实命名是通用要求 |

## 4. 使用方法

```sh
G=skills/meson-cross-pkgconfig/scripts/meson_cross_pkgconfig_guard.py
# L1：CI 红后日志归因（R44 二次分类）
python3 $G --log reports/conan-create.log --json -o /tmp/guard.json
# L2：建 PR 前配方预检
python3 $G --recipe archives/x/<pkg>/<ver>/conanfile.py --json
# L3：环境陷阱
python3 $G --env --json
```

复现验证（双向）：

```sh
sh skills/meson-cross-pkgconfig/tests/repro_meson_cross_trap.sh
# 期望末行：REPRO_SCRIPT_EFFECTIVE=yes（A 面复现 + B 面修复对照全过）
```

单元测试：`python3 skills/meson-cross-pkgconfig/tests/test_meson_cross_pkgconfig.py`（9 例）。

## 5. 产出物清单

| 文件 | 作用 |
|------|------|
| scripts/meson_cross_pkgconfig_guard.py | 三通道检测器（L1 六特征 / L2 三反模式 / L3 钉源），JSON 输出，日志走文件防 SIGPIPE，无本机路径写死 |
| templates/conanfile-meson-two-step.tmpl | 配方 build() + test_package 两步法模板（注释内嵌实证） |
| samples/sample-g2-failure-sequence.log | sratom G2 五轮失败序列样本（归因训练语料） |
| tests/repro_meson_cross_trap.sh | A/B 双向复现（含 HMDFS 探测陷阱的规避实证） |
| tests/test_meson_cross_pkgconfig.py | 9 例单测（六特征逐条 + 反模式逐条 + 钉源 + 文件输出） |

## 6. 与既有知识的关系

- E046（chmod 不生效/属主映射）：本 SKILL 的⊕坑与探测纪律（实际执行验证）
  是其在「工具探测逻辑」上的具体化延伸；
- fuse-tmp-write-guard SKILL：同属 FUSE/HMDFS 环境陷阱族，但针对临时目录
  写入（umask 形态）；本 SKILL 针对 meson×conan 交叉配方形态，互补不重叠；
- R33（禁裸 shell env）/R51（上游测试三步法）：模板已内置合规实现。
