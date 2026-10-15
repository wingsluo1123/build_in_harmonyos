# 构建树内相对路径假设在打包安装后断裂：argv[0] 目录相对运行时资源（other.dtb）与 CWD 相对测试数据（README）两类显形

- **草稿 ID**: DRAFT-11418-uboot-packaged-layout-relative-assets
- **来源**: u-boot 2026.07 HarmonyOS PC 适配（conan test_package 包布局回放暴露：other.dtb 按 argv[0] 目录相对解析缺失 → OF_LIVE 组 15 子测试全灭；membuf_readline 按 CWD 相对读 README 缺失 → smoke 失败 1；以包内镜像相对布局 + README 随包副本修复）
- **分类**: packaging / sandbox / relative-path / installed-layout / testing
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **关联**: 与 DRAFT-11418-uboot-fixture-staging-hex-carrier 同族（"产物必须在其运行环境内自足"）；实例一对应打包层修复（recipe package() 镜像相对布局），实例二对应 test_package 强化（README 随包 + CWD 切换）

## 问题 / 错误签名

- **实例一（argv[0] 目录相对，运行时资源）**：包内回放时 OF_LIVE 组 15 个子测试全败——`dm_test_livetree_ensure` + 14 个 `dm_test_ofnode_*_ot`，逐子测试日志首行：
  `Cannot open file '<pkg>/bin/arch/sandbox/dts/other.dtb'` →
  `state_load_other_fdt() Cannot read file ...` / `sandbox_load_other_fdt() Cannot read other FDT` →
  `test/dm/ofnode.c:1487 ... 0 == test_load_other_fdt(uts): Expected 0x0 (0), got 0xfffffffb (-5)`（live/flat 双遍各败一次）。
- **实例二（CWD 相对，测试数据）**：包内 smoke `ut lib` 失败 1 例——`membuf_readline` 以 CWD 相对路径打开 `README` 作样例数据，包回放 CWD 无该文件 → `failures: 1`（`Tests run: 131 ... failures: 1`）。
- **共同显形条件**：同一二进制、同一测试全量在**构建树内**多轮全绿（879/879）；只有**以包形态在独立 CWD/安装前缀下回放**时才出现，且无任何构建期告警。

## 根因

1. **argv[0] 目录相对解析（other.dtb）**：`state_load_other_fdt()` 经 `state_get_rel_filename("arch/sandbox/dts/other.dtb", ...)`（arch/sandbox/cpu/state.c:402）拼路径——取 `strrchr(state->argv[0], '/')` 得**可执行文件所在目录**，再拼相对子路径。上游构建树内二进制位于 `build/sandbox/u-boot`、资源位于 `build/sandbox/arch/sandbox/dts/other.dtb`，相对结构天然命中；包内二进制位于 `bin/u-boot-sandbox`，`bin/arch/sandbox/dts/other.dtb` 不存在 → 打开失败 -5。该解析既非 CWD 相对、也无环境变量/命令行覆盖，纯 argv[0] 目录相对。同类入口还有 `-T` 选项（start.c:213 同机制解析 `arch/sandbox/dts/test.dtb`）。
2. **CWD 相对解析（README）**：`test/lib/membuf.c` 的 `lib_test_membuf_readline` 以 `os_read_file("README", ...)`（相对 CWD）读取样例文本作断言输入。上游 pytest 的 CWD=源码树根，README 天然在场；打包框架的消费者测试在独立工作目录回放时缺席 → -EIO。
3. **显形的必要条件**：构建树布局假设在构建树内**永远命中**——in-tree 验证（哪怕是逐子测试全量）对"包布局缺口"零覆盖；打包框架的消费者测试（conan create/test_package 等）是唯一回放面，而它只有在全量测试被纳入时才触发这些用例（本项此前 smoke 先死在实例二，实例一被前序失败掩盖，修复 README 后才暴露——**前序失败会级联掩盖后续缺口，需修复后整链复跑**）。

## 最小修复方案

打包层镜像相对布局 + 数据随包 + 在位断言（不涉源码补丁）：

1. **other.dtb 随包镜像**（`conanfile.py` `package()`）：

   ```python
   other_dst = os.path.join(bin_dir, "arch", "sandbox", "dts")
   os.makedirs(other_dst, exist_ok=True)
   shutil.copy2(os.path.join(sb, "arch", "sandbox", "dts", "other.dtb"),
                os.path.join(other_dst, "other.dtb"))
   ```

   包内形成 `<bindir>/arch/sandbox/dts/other.dtb`，与二进制保持上游同相对结构；消费方以任意路径（绝对/相对）调用 `bin/u-boot-sandbox` 均可解析。
2. **README 随包**：上游源码树 `README` 逐字节副本放入 `test_package/fixtures/README`，test_package 主冒烟前复制到工作目录并切换 CWD（对齐上游 pytest 以源码根为 CWD 的契约）。
3. **在位断言防回归**：test_package 第 0 步产物在位断言把 `bin/arch/sandbox/dts/other.dtb` 纳入硬校验清单（9 → 10 项），打包层一旦静默丢文件立即失败、不进入后续步骤。

## 验证

1. **实例一对照闭环**（包内二进制定向单测）：修复前 `u-boot-sandbox -d test.dtb -c "ut dm dm_test_ofnode_get_path_ot; exit"` → `Cannot open file ...other.dtb` + `:1487 -5`；把 other.dtb 放至 `bin/arch/sandbox/dts/` 后同命令 → `failures: 0`（`dm_test_livetree_ensure` 同）。全量复跑：`PASS=879 FAIL=0 SKIP=0`（修复前 864/15，15 个失败恰好为该文件依赖的完整清单）。
2. **实例二对照闭环**：工作目录放入 README 后 `u-boot-sandbox -c "version; ut lib; exit"` → `failures: 0`（修复前 `failures: 1`）。
3. **包形态整链**：conan create 全链（含 test_package 四步）自全新解包执行，第 0 步 `10 package assets present`、逐子测试 `PASS=879 FAIL=0 SKIP=0`。

## 教训 / 泛化

- **"构建树内全绿"与"包可用"是两个命题**：凡上游测试/二进制按 CWD 或 argv[0] 目录相对解析资源者，构建树内跑了多少轮全绿都不覆盖安装布局；适配验证必须以包形态回放（打包框架消费者测试纳入全量测试面），否则缺口原样带到消费方。
- **显形条件要刻意构造**：in-tree 运行 = 相对路径天然命中 = 缺陷隐形；独立 CWD/安装前缀/最终制品回放才是显形面。这与"夹具必须在不依赖构建树的一次性状态下自足"（见 fixture-staging 草稿）同族。
- **前序失败级联掩盖**：多步流水线中前一步失败会掩盖后续步骤的全部缺口（本项 smoke 的 README 失败掩盖了全量测试里 other.dtb 的 15 失败）；修复必须整链复跑，不能以"修好了报错的那一步"收工。
- **资源解析路径第一现场取证**：`Cannot open file '<路径>'` 已给出实际解析路径，核对"该路径 vs 实测布局"是第一步——本项两条错误（-EIO -5）均为文件不在，而非 OF_LIVE 转换/设备树解析逻辑缺陷。
