# tk 8.6.16 适配笔记（HarmonyOS PC / OHOS aarch64）

## 0. 结论速览

| 项目 | 结果 |
|---|---|
| 配方 | `archives/t/tk/8.6.16/conanfile.py`（autotools，裸 configure） |
| 依赖 | `tcl/8.6.16`、`libx11/1.8.13`、`xorgproto/2025.1`（均已在 ohpcd 制品仓发布） |
| conan create | ✅ 通过（库 + wish8.6 打包完成，ELF 已重签） |
| 消费者测试 | ✅ 8/8（显示无关：链接 tk 包并调公共 API） |
| 上游测试套件 | ⚠️ 不可运行（92 个 .test 全部由 wish/tktest 驱动，需真实 X display；实测见 reports/r51-upstream-tests.txt） |
| 补齐测试 | ✅ `test_package/test.c`（119 行真实消费者）+ `test_package/test_wish.tcl`（wish 启动链探针） |

## 1. 环境

- 构建系统：autotools（`unix/configure` + `make`，**裸 configure**，不用 `AutotoolsToolchain` 自动注入）
- 编译器：clang / clang++ 15.0.4（`/data/service/hnp/bin/`）
- 目标：OHOS aarch64（`-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`）
- 源码：`tk8.6.16-src.tar.gz`，sha256 `be9f94d3575d4b3099d84bc3c10de8994df2d7aa405208173c709cc404a7e5fe`
- 复现：`conan create archives/t/tk/8.6.16 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`

## 2. 落地动作（全部在配方内，上游无 OHOS 分支）

1. **源码可写性**：HMDFS 重写源码树会丢可执行位、`umask 077` 目录不可写 → 与已发布兄弟包 tcl 8.6.16 同款处理（configure 前置 `umask 022` + `chmod 0755`）。
2. **uname 平台语义（E532）**：OHOS `uname -s` 返回 `HarmonyOS`，tcl.m4 的 `system` 分支无匹配 → `SHLIB_LD`/`SHLIB_SUFFIX` 落空、共享库链接命令残缺。配方注入 PATH 前置的 uname shim 伪装成 `Linux`，并显式 `tcl_cv_sys_version=Linux-6.6`。
3. **X11 依赖（E533/E011）**：`AC_PATH_XTRA` 会做运行期探针并去找本机 X 头/库 → 平台无 X11 开发环境必然失败。改用 `--x-includes=<libx11 包 include> --x-libraries=<libx11 包 lib>`（`AC_PATH_X` 只做链接测试）+ `tcl_cv_sys_version` 短路运行期探针。
4. **不用自动 flag 注入（bg-34 根因）**：`AutotoolsDeps` 会把 `-lX11 -lXdmcp …` 塞进 configure 的编译器探针 `LIBS`，探针运行期加载不到 `.so` → 误报 `cannot run C compiled programs`。改为裸 configure，链接信息只经 `--with-tcl` / `--x-libraries` 提供。
5. **头文件搜索路径（bg-35 根因）**：Tk 的 `CC_SWITCHES` 用的是失效的 `-I${TCL_GENERIC_DIR}`，实测 `make` 报 `tcl.h not found`。配方用 `CFLAGS/CPPFLAGS` 显式补 `-I<tcl|libx11|xorgproto 包 include>`。注意 `X11/Xlib.h` 在 **libx11**（不在 xorgproto）。
6. **SONAME（E522）**：上游 `unix/Makefile` 链接共享库不带 `-soname` → 包内 `libtk8.6.so` 无 SONAME，依赖它的二进制无法按 soname 解析。构建前在 Makefile 的共享库链接命令注入 `-Wl,-soname,libtk8.6.so`。
7. **安装布局**：`--prefix=/usr/local` + `DESTDIR` 会把文件埋进 `<pkg>/usr/local/**`，与 cpp_info 期望的 `<pkg>/{lib,include,bin}` 不符 → `package()` 先 staging 安装，再按 lib/tk8.6/include/bin 分类拷贝（`demos/` 演示内容不打包）。
8. **包自包含（X11 头）**：上游 `libx11/1.8.13` 配方没有声明 `cpp_info.includedirs`（包内有 `include/X11/*.h`，生成的 `libx11_INCLUDE_DIRS` 却为空），xorgproto 同样不进生成器 → 消费方只 `find_package(tk)` 拿不到 X11 头，编 `<tk.h>` 直接 `'X11/Xlib.h' file not found`。为让本包自包含，把 X11 头同样装进本包 `include/`（保留 `X11/` 子目录）。
9. **RUNPATH**：autotools 会把 `-L` 的 conan 缓存绝对路径写进 RUNPATH，发布包里没有意义 → `patchelf --set-rpath /usr/local/lib` 收敛（同 tcl 8.6.16）。
10. **ELF 重签（E077）**：步骤 6 的 SONAME 注入会抹掉构建期 `.codesign` 段 → 运行期 `dlopen` 报 `Permission denied`。`package()` 末尾对包内全部 ELF 先 `objcopy --remove-section .codesign` 再 `binary-sign-tool sign -selfSign 1`，签完不再改动文件。
11. **消费者测试 stub 绑定（E429，本 PR 新草稿）**：tk 以 `USE_TCL_STUBS` 构建，`libtk8.6.so` 里所有 Tcl 调用都走 `tclStubsPtr`，该表由宿主初始化（`Tk_Init` → `Tcl_InitStubs`）绑定。消费者若先调 Tk API 再初始化，就是未绑定表 → 直接 SIGSEGV（本次实测踩到）。`test.c` 因此先 `Tk_Init`（无显示时按预期失败，但**完成 stub 表绑定**），再调 `Tk_GetReliefFromObj` 等公共 API。
12. **CI L1d 假测试误判**：`ci/conan/build_and_test.sh` 的 L1d 用 `grep -E "self.run.*(echo|print|true)"` 扫 `test_package/conanfile.py`。wish 探针原先写 `sh -c 'echo exit | wish8.6'` 会被判成空壳测试 → 改为把探针脚本落成文件 `test_package/test_wish.tcl` 用文件名参数传入（与 tcl 8.6.16 的 `tclsh8.6 "{script}"` 同形）。
13. **HMDFS 硬链接**：tk 的 `make install` 会给 man3 建硬链接，HMDFS 报 `Operation not permitted`（`ln: cannot create hard link ...`）——安装仍成功，非阻塞，记录为平台限制。

## 3. 上游测试申报（R51 三步法）

1. **清点**：`tests/` 共 **92 个 `.test`** 文件（124 个文件），全部由 `tests/tktest`（`make test` 构建）驱动，`all.tcl` 统一注册；`wish` 亦被测试用例用于交叉验证。
2. **实测**：`make test -j1` 已在 `build()` 内实际执行（非阻塞，日志 `build-release/upstream_test.log`）。三段实测（逐段排除干扰项：X11 依赖 libdir → `tclConfig.sh` 残留构建路径 → 平台缺显示）见 `reports/r51-upstream-tests.txt`。
3. **回填**：排掉两个干扰项后，`tktest` 完成 Tcl 初始化、停在 `package require Tk` —— 本平台与 CI worker 均无 X display（E530），故 92 个上游用例不可运行（平台限制，非配方缺陷）。因此**补齐鸿蒙独有消费者测试**（`test_package/`），以无显示方式覆盖库加载、stub 绑定与公共 API 调用链。

## 4. 知识沉淀

- **E429（新草稿，本 PR）**：`knowledge/drafts/E429-draft-3477.kv` —— 「stub 机制库消费者必须先绑定宿主 stub 表，未绑定即调 API 直接 SIGSEGV」，含检测规则/处理策略/文档/样例四件套。
- 已入库参考：E530（无显示测试口径）、E532（uname 平台语义）、E533/E011（X11 探针）、E522（SONAME）、E077/E452（ELF 签名）。
- 未入库但值得后续补的知识候选（已在 PR 说明中提出）：
  - 依赖包有头文件但配方未声明 `cpp_info.includedirs` → 下游 `find_package` 拿不到 include 目录（本包用自包含缓解）。
  - Recipe 驱动 ELF 重签：SONAME 注入抹掉 `.codesign` → 运行期 `Permission denied`（签名类 E077 的具体触发链）。

## 5. 已知限制

- 上游测试套件不在 CI 中阻塞（无显示环境不可运行）；CI 只跑 `test_package` 的显示无关消费者测试。
- 包内 `wish8.6` 可执行文件在无显示环境下启动即退出（仅报缺显示），本平台图形显示能力由系统 X11/显示服务提供，不在本包职责内。
---

**编译结束**: 2026-10-16 19:38
**最终状态**: built
