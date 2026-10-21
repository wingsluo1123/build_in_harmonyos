# OHOS hmdfs hmmac 内容完整性保护: .so 落盘后任何字节改写均拒载 — SKIP_RPATH 全禁优于 install-copy 覆盖

- **草稿 ID**: DRAFT-manifold-3.5.2-hmmac-so-rewrite-reject-skip-rpath
- **来源**: manifold 3.5.2 HarmonyOS PC 适配（共享库 install 后 `Permission denied` 排障 + 系统性机制实验）
- **分类**: cmake / conan / ohos-loader / shared-lib / install
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **关联正式条目**: 对 E504（CMake install 期 RPATH_CHANGE 重写 .so 后 musl loader 无法加载）的**机制补充与方案升级**

## 问题 / 错误签名

- **test_package（或任何 dlopen/exec）阶段报错**：
  ```
  Error loading shared library libmanifold.so.3: Permission denied
  ```
  且 `LD_LIBRARY_PATH` 指向正确目录也无效；`ls -l` 权限正常（0755）。
- **触发条件**：CMake install（`file(RPATH_CHANGE)`）或任何工具在 .so 链接落盘**之后**改写了其字节。

## 根因（实验证据链）

OHOS 开发者模式的 `/storage` 为 hmdfs，启用 `hmmac=use_task` 完整性保护。
对"改写已落盘 ELF"的行为，做了四组决定性实验（manifold 3.5.2 真实产物 + 最小复现库）：

| 实验 | 操作 | 结果 |
|------|------|------|
| A | `cp` 原字节到新文件名，dlopen | **可加载** |
| B | 改 RUNPATH 字符串区 127 字节（新文件、单次 write syscall） | 拒载 |
| C | 只改文件末尾 LOAD padding **1 字节**（新文件、单次 write） | 拒载 |
| D | 全新 clang 链接的最小库，改 1 字节 padding 再 dlopen | 拒载 |

结论：
1. 判定与 inode/文件名/写入方式无关，与**内容**相关；
2. 链接器（ld.lld）产出的内容可加载，**任何事后修改**（哪怕 1 字节无关 padding、哪怕由全新文件名一次写入）都被拒载；
3. 因此 CMake install 的 `file(RPATH_CHANGE)`、`patchelf`、`chrpath` 等一切字节级后处理在 hmdfs 上都不可用（与 E077 的 codesign 重签路径互斥——重签是另一个子系统，不解决 hmmac）。

## 方案升级（相对 E504）

E504 推荐 `CMAKE_SKIP_INSTALL_RPATH=TRUE` + `package()` 用 build 产物覆盖 install 产物。
本次适配发现该方案有**隐藏缺陷**并给出更优解：

### E504 方案的缺陷：build-host RUNPATH 污染

conan 2 CMakeDeps 会给依赖（**即使全是静态库**）注入 `INTERFACE_LINK_DIRECTORIES`，
cmake 由此在 build 树 .so 里写入指向 Conan cache 的绝对路径 RUNPATH（如
`/storage/.../.conan2/p/b/clipp.../lib`）。copy 覆盖会把该 RUNPATH 原样带进最终包：
- 泄漏构建机绝对路径（可复现性/安全检查不通过）；
- 消费者机器上该路径不存在，musl 逐目录搜索时虽被跳过，但属无效字段。

### 推荐方案：`CMAKE_SKIP_RPATH` 全禁 + 构建期 LD_LIBRARY_PATH

```python
# generate():
if self.settings.os == "OHOS" and self.options.shared:
    tc.variables["CMAKE_SKIP_RPATH"] = "ON"
```

适用前提（本类仓库绝大多数包满足）：**运行期依赖全部静态链入**，
`.so` 的 RUNPATH 本来就没有存在价值。效果：
- 链接器输出即最终字节，install 是纯复制，零改写；
- build 树与包内产物都无 RUNPATH，无 build-host 泄漏（可用 `readelf -d | grep -E 'RPATH|RUNPATH'` 断言为空）。

代价与配套：SKIP_RPATH 同时去掉 build 树 rpath，若上游构建期需要**运行**产物
（`gtest_discover_tests` 的 POST_BUILD 探测、ctest），需用 `LD_LIBRARY_PATH` 补：
见下方"conan 2 环境传导三坑"。

### 方案选型决策表

| 场景 | 方案 |
|------|------|
| 运行期依赖全静态（DT_NEEDED ⊆ {libc, libc++_shared, 包内}） | `CMAKE_SKIP_RPATH=ON`（首选） |
| 确有外部共享依赖 | 让**链接器**直接产出 `$ORIGIN` 相对 RUNPATH（`-Wl,-rpath,'$ORIGIN'`），严禁 install 期写入 |
| 无法控制链接命令 | E504 的 copy 覆盖（最后手段，注意 M6 类 RUNPATH 污染） |

## 机制补充 1：cmake 4.1 的 BUILD_RPATH 不再注入链接命令

最小实验：cmake 4.1 下无论 `CMAKE_BUILD_RPATH` cache 变量还是目标的
`BUILD_RPATH` 属性，**link.txt 中都不出现 `-Wl,-rpath`**（cmake 3.x 会出现）。
rpath 仅由 install 的 `RPATH_CHANGE` 事后写入。影响：
- 指望 `BUILD_RPATH` 让 build 树可执行文件找到 .so 的项目会静默失效；
- 构建期运行一律用 `LD_LIBRARY_PATH`（musl 完整支持）更可靠。

## 机制补充 2：conan 2 环境传导三坑（LD_LIBRARY_PATH 到不了 cmake 子进程）

要让 `LD_LIBRARY_PATH` 在 `cmake --build`/`ctest` 子进程生效，以下三条路**都不通**：
1. `build()` 里改 `os.environ`：conan 2 的 `run()` 用 generate() 时固化的 conanbuildenv 包装命令，不读运行期 os.environ；
2. `generate()` 里 `self.buildenv_info.append_path(...)`：实测不落盘到任何 env 文件（对无 `VirtualBuildEnv` generator 的 recipe）；
3. `CMake.build(env=Environment对象)`：此参数只接受 **env 文件名字符串列表**。

**可行做法**：generate() 里手写 env 文件，build()/test() 以文件名引用：

```python
# generate() 里:
env = Environment()
for sub in ("src", "bindings/c", "samples"):     # build 树 .so 所在目录
    env.append_path("LD_LIBRARY_PATH",
                    os.path.join(base, "build", cfg, sub))
vars_ = env.vars(self, "build")
lines = ['export %s="%s${%s:+:$%s}"' % (k, v, k, k) for k, v in vars_.items()]
save(self, os.path.join(self.generators_folder, "ohos_buildpath_env.sh"),
     "\n".join(lines) + "\n")

# build() 里 (此 conan 版本 CMake.build 无 env 转发, 用私有 _build):
cmake._build(env=["conanbuild", "ohos_buildpath_env"])
# test() 里:
cmake.test(output_on_failure=True, env=["conanbuild", "conanrun", "ohos_buildpath_env"])
```

注意 `base` 用 `self.folders.base_build`（绝对）而非 `self.folders.build`（相对）；
generate() 阶段 build 树尚未创建，只能按 `cmake_layout` 固定布局 `build/<config>/<subdir>` 推导，不能 `os.path.isdir` 探测。

## 实际验证结果

- **环境**：HarmonyOS PC（HongMeng Kernel, aarch64, musl + libc++），clang 15（OHOS SDK），cmake 4.1.2，conan 2.x。
- **共享库变体**：`conan create -o &:shared=True` EXIT=0；
  上游 CTest 427/427 通过（`Total Tests: 427`；408 fast 组 + 19 长测组分批运行全 Passed）；
  test_package 12 项 PASS；OHOS ABI 专项 M0-M10 全过，其中 M6 断言 RUNPATH 为 none。
- **静态库变体**：`conan create`（默认）EXIT=0；一次完整 `ctest --parallel 8`：`100% tests passed, 0 tests failed out of 427`。
- **产物核验**：`readelf -d` 显示两个 .so 均无 RPATH/RUNPATH；DT_NEEDED 仅 `libc.so`/`libc++_shared.so`/`libmanifold.so.3`（包内）；`.note.ohos.ident` 存在。

## 适用范围

- 在 HarmonyOS PC hmdfs（`hmmac=use_task`）上构建 CMake 共享库，且 install 产物需可被 dlopen/exec 的任何包。
- 错误签名 `Error loading shared library ...: Permission denied` 且 `LD_LIBRARY_PATH` 无效时。
- 使用 conan 2 + CMakeDeps（会注入 INTERFACE_LINK_DIRECTORIES）的项目。

## 非适用边界

- 常规 ext4/tmpfs 构建环境（可自由改写 .so 字节）无需此方案。
- 运行期确需外部共享依赖的包：SKIP_RPATH 会让消费者找不到依赖，应改用链接器直出的 `$ORIGIN` RUNPATH。
- E077 的 codesign 场景（开发者模式签名校验）是另一子系统，症状相似但解法不同；若同时命中需分别处理。

## 查重差异

- **E504**：同一错误签名，但推荐 `SKIP_INSTALL_RPATH + copy 覆盖`。本条目补充了 hmmac 内容指纹的四组实验证据（证明任何字节改写不可行而非仅 RPATH_CHANGE），指出 copy 方案的 build-host RUNPATH 污染缺陷（CMakeDeps 静态依赖也注入 link 目录），并升级为 SKIP_RPATH 全禁方案。
- **E077**（post-install-script 重签）：解的是 codesign 子系统；本条目实验证明 hmdfs 上重签/重写内容均不恢复可加载性，二者互补。
- **libfreenect DRAFT**（hmdfs symlink）：同为 hmdfs 限制但属 symlink(2) 不支持，与本条目的内容完整性保护是两个独立机制。

## 关联原则

- P004（如 E504 引用）：不改写链接产物字节。
- P010：在配方侧用标准 CMake 变量解决，零上游补丁。

## 禁止模式

1. **install 后 patchelf/chrpath/RPATH_CHANGE**：hmdfs 上必然拒载（实验 B/C/D）。
2. **copy 覆盖但不检查 build 树 RUNPATH**：会把 Conan cache 绝对路径泄漏进包（M6 类检查会抓到）。
3. **指望 cmake 4.1 的 BUILD_RPATH/CMAKE_BUILD_RPATH**：不再注入链接命令（机制补充 1）。
4. **在 build() 里改 os.environ 想传导给 cmake**：conan 2 运行期不读（三坑之 1）。

## 关联交付

- 本草稿与 `archives/m/manifold/3.5.2/**` 同属一次交付（conanfile.py 中 SKIP_RPATH + ohos_buildpath_env.sh 注入为方案的参考实现）。
- 正式 E 编号由知识库主编审核后分配（建议并入 E504 作为 v2 方案，或新开条目并 `supersedes` 其 rec_approach）。
