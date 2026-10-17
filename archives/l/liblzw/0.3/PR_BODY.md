- **三方库名称**：liblzw
- **上游版本**：0.3（tag v0.3，commit b6b7241e6e49c4e07ea06367eff93f8b9b70e5bb）
- **上游仓库地址**：https://github.com/vapier/liblzw
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E011（edit-umask-in-configure）、E007/E072（autotools build-type/triplet）、E112/E052（config.status 临时目录）、E058/E209（autogen/configure 缺失）、E528（OHOS autotools 环境）、E046（hmdfs 权限）、E460（Autotools bootstrap 工具自足化，reuse_existing）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 3 | 来源：Autotest testsuite（lot/simple/simple2），`make check` 3/3 |
| 集成测试 | 0 | 无独立集成测试 |
| 其他测试 | 0 | — |
| **合计** | **3** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 3 | 不变 | 上游 testsuite 3 用例本地全部通过 |
| 集成测试 | 1 | +1 | test_package 消费者测试：写入上游 simple.Z 样本并经 liblzw API（lzw_open/lzw_read/lzw_close）解压，断言 73 字节明文与上游 uncompress 输出一致 |
| 鸿蒙特有测试 | 1 | 新增 | harmonyos_test.sh：验证 HarmonyOS PC aarch64 平台 + liblzw LZW 解压字节级一致（含静态库链接与 ar archive 完整性） |
| **合计** | **5** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 若选择「是」，须说明：
> - **补全的测试范围**：为 liblzw 核心 LZW 解压功能新增 1 个 test_package 消费者测试 + 1 个鸿蒙特有平台测试
> - **补全原因**：上游仅有 Autotest testsuite（覆盖 CLI 工具与简单解压路径）；test_package 消费者测试验证安装态静态库的 API 可用性；鸿蒙特有测试验证 HarmonyOS PC aarch64 平台行为
> - **新增测试文件清单**：
>   1. `test_package/test.c` — 消费者测试：写入 simple.Z 样本、lzw_open/lzw_read 解压、断言明文字节级一致
>   2. `harmonyos_test.sh` — 鸿蒙特有测试：平台断言（HongMeng Kernel/aarch64）+ 编译链接 liblzw.a + 解压字节级断言

## 验证结果

- 编译状态：通过（autotools configure/make/make install 通过；conan-verify G0/G1/G2/G3 全 PASS；finish W2/W3 通过）
- 上游测试用例通过率：3/3（100%）
- 新增测试用例通过率：2/2（100%）（test_package 消费者测试 + harmonyos_test.sh 均实跑 exit 0）
- **R02 CI L1 干净环境闭环**：conan create 官方源下载成功、autogen.sh 在 conanbuild 环境由 tool_requires（automake/1.18 + libtool/2.5.4）驱动 aclocal/automake/libtoolize，configure 生成，exit 0；CI 等价 build_and_test.sh G0/KC/JC/L0/L1/L4/L5 全 PASS（L2 因纯库无 bin/ 合理 skip）

## 补充说明

- 上游 v0.3 tarball 未包含生成的 configure 脚本，配方 build() 先执行 `sh autogen.sh`（autoreconf -i -f）。
- OHOS/HMDFS 适配：config.status 临时目录 umask 077→022（E011）；configure 显式 `--build/--host=aarch64-linux-ohos`（E007/E072）；生成 libtool 修补 `echo`/`tool_oldlib`（E528 同族）；test_package 在可写 cwd 创建临时文件（hmdfs /tmp 只读）。
- **R02 修复（CI L1 clean-env 闭环）**：R01 交付后远端 CI L1 conan create 在干净环境失败——CI 仅有 autoconf 2.72、无 automake/aclocal，`sh autogen.sh` 报 `Can't exec "aclocal"`（autoreconf exit 2），configure 未生成，随后 `sed -i 's/umask 077/umask 022/g' configure` 报 No such file。根因=配方依赖执行端设备本机 HNP autotools（aclocal 位于 `/storage/Users/currentUser/usr/local/bin`）且无 tool_requires，属配方自足性缺陷而非库缺陷（与 libzc 0.4.3 R02 同指纹）。修复：`build_requirements()` 声明 `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`（制品仓 1.18/2.5.4 实测可消费）；`generate()` 注入 `VirtualBuildEnv` 使 tool_requires bin 进入 conanbuild PATH；autogen.sh 以 `env="conanbuild"` 运行。合成依赖 CI 干净环境语义（无设备专属路径注入）验证通过；conandata.yml 修正为官方 GitHub URL 优先（移除 gh-proxy 前缀作唯一来源，保留作 fallback，R39/PF7）。
- 知识路径 A（reuse_existing，命中 E460 等），未创建草稿；依赖 0（无 requires）。
- 基线/共享框架/其他库文件零改动。