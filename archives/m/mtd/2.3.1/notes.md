# mtd 2.3.1 (mtd-utils) 适配笔记

## 编译环境
- 构建系统: autotools (autoreconf, mtd-utils git 源码无 configure)
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4 / clang++ (HarmonyOS PC arm64, native)
- 状态: built

## 编译步骤

1. **W0 依赖发布检查**: `bash ci/scripts/preflight_check.sh mtd/2.3.1` +
   `conan download --only-recipe -r=ohpcd` 逐项验证 zlib/lzo/lz4/zstd/openssl/
   libuuid 均已在 ohpcd 制品仓发布。mtd-utils 2.3.1 实际不依赖 lz4。
2. **W1 同步主仓库**: `git checkout main && git pull origin main`
3. **init-build**: 官方 tarball 源 Savannah(404)/GitHub Linux-MTD(404) 不可用;
   用 `git://git.infradead.org/mtd-utils.git` tag v2.3.1 clone + `git archive`
   生成 tarball 放入 `$TMPDIR/builds/mtd-2.3.1.tar.gz`, init-build 检测到
   tarball 存在跳过下载; `--url=https://git.infradead.org/mtd-utils.git`
   (R39: 官方源)
4. **R47 语言预检**: `lang-preflight` → task=cpp, detected=c (C/C++ 兼容族,
   exit 0)
5. **手动编译** (Step 2):
   - `sh ./autogen.sh` (autoreconf 生成 configure; config.guess 2.72 已识别
     HarmonyOS, 输出 aarch64-unknown-linux-ohos, 无需 E007 补丁)
   - configure 报 "missing one or more dependencies": 缺 uuid (mkfs.ubifs)
     → conan install 依赖到 `$TMPDIR/mtd-deps` (zlib/lzo/zstd/libuuid/openssl),
     `PKG_CONFIG_PATH=$TMPDIR/mtd-deps ./configure --prefix=$DEFAULT_PREFIX`
   - **E011**: config.status 报 "can't create ./confXXX/subs1.awk:
     Permission denied" — HMDFS 上 umask 077 创建 0700 临时目录, UID 映射
     导致进程不可写 → sed 将 configure/config.status 中 umask 077 改 022
   - uuid 头: 上游 `#include <uuid.h>` 但 conan libuuid 提供
     include/uuid/uuid.h → 改 `#include <uuid/uuid.h>`
   - `make -j2` 成功, 生成全部 50+ 工具
   - `make install DESTDIR=$TEST_PREFIX` 成功 (staging 隔离)
   - **make check**: 1/1 PASS (tests/jittertest/filename_bounds.sh)
6. **conan-init**: 生成 conanfile.py/conandata.yml/test_package 模板,
   AI 完善: requirements (zlib/lzo/zstd/libuuid/openssl), patches,
   test_package 实质 smoke test
7. **conan-verify** + **finish**: 见 .ci-result.json

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 tarball 404 (Savannah mtd/ 与 mtd-utils/、GitHub Linux-MTD) | 上游发布目录失效 | 用 git://git.infradead.org clone + git archive 生成 tarball; conandata 用 sigma-star GitHub 官方镜像 codeload (R39) |
| 2 | configure "missing one or more dependencies" (uuid) | mkfs.ubifs 需要 libuuid, 本机未装 | conan install zlib/lzo/zstd/libuuid/openssl 到私有 prefix, PKG_CONFIG_PATH 注入 |
| 3 | config.status "can't create ./confXXX/subs1.awk: Permission denied" | **E011**: HMDFS 上 umask 077 的 0700 临时目录因 UID 映射不可写 | conanfile.py build() 内 Python 替换 configure 的 umask 077→022 (autotools 工具链生成 configure 后、configure 执行前; configure 是构建产物, refresh-patch 无法追踪, 故不入 patches/) |
| 4 | mkfs.ubifs 编译 "uuid.h file not found" | 上游 `#include <uuid.h>` 非标准; libuuid 头在 include/uuid/uuid.h | patches/0001-ubifs-utils-mkfs.ubifs-mkfs.ubifs.c.patch (`#include <uuid/uuid.h>`) |
| 5 | **CI 第1轮**: `Can't exec aclocal: No such file or directory` | CI worker 无系统 automake/aclocal, autogen.sh(autoreconf --force --install) 在 aclocal 处失败 | `build_requirements()` 声明 tool_requires autoconf/2.72 + automake/1.18 + libtool/2.5.4 + pkgconf/3.0.5 补齐 bootstrap 工具链 (参考先例 archives/b/burp2/2.1.0) |
| 6 | **CI 第2/3轮**: conan perl/5.42.2 交叉编译版 Cwd.so 无法在构建机 dlopen, autoreconf 必挂 | autotools 的 tool_requires 传递依赖 perl/5.42.2 是 aarch64-ohos 交叉编译版, Cwd.so 与构建机不兼容 | build() 内强制系统 perl `/data/service/hnp/bin/perl` + 手动逐步执行 aclocal→autoheader→automake→autoconf (每次调用前 PERL5LIB 指向对应工具模块目录 share/automake-1.18 / share/autoconf) (参考先例 archives/b/burp2/2.1.0) |
| 7 | configure `checking build system type... cannot guess build type` | automake 1.18 (tool_requires) 的 config.guess/config.sub 不认识 HarmonyOS (本机 uname -s=HarmonyOS) | build() 内 `_patch_config_guess_sub()` 给生成的 config.guess/config.sub 打 OHOS triplet 识别补丁 (config.guess 加 HarmonyOS 早识别分支, config.sub 加 -linux-ohos) (参考先例 archives/b/burp2/2.1.0) |

## 源码修改 (patches/)

- `0001-ubifs-utils-mkfs.ubifs-mkfs.ubifs.c.patch`: mkfs.ubifs.c `#include <uuid.h>` →
  `#include <uuid/uuid.h>` (标准 libuuid 布局)
- configure-umask 修复 (E011): 在 conanfile.py build() 内 autotools 工具链生成
  configure 后 Python 替换 `umask 077` → `umask 022` (configure 为构建产物,
  无法用 refresh-patch 追踪)
- config.guess/config.sub OHOS 补丁 (E566): 在 conanfile.py build() 内
  `_patch_config_guess_sub()` 给 automake 1.18 生成的 config.guess/config.sub
  打 OHOS triplet 识别补丁

## 依赖版本

| 依赖 | 版本 | 制品仓状态 |
|------|------|-----------|
| zlib | 1.3.1 | published |
| lzo | 2.10 | published |
| zstd | 1.5.6 | published |
| libuuid | 2.42.2 | published |
| openssl | 3.0.21 | published |

注: mtd-utils 2.3.1 不依赖 lz4 (configure.ac 无 lz4 检查)

## 验证结果

```bash
# 手动编译产物
$SBIN/mtdinfo --version
# => mtdinfo (mtd-utils) 2.3.1
# make check
# => TOTAL: 1 PASS: 1 (filename_bounds.sh)
# conan create (W3): 见 .ci-result.json
```

## 注意事项

- E011 (umask 077) 是所有 autotools 项目在 HMDFS 上的通用问题,
  E011 补丁须在 autotools 工具链生成 configure 之后、configure 执行之前应用
- CI worker 与本地环境差异: 本地有系统 automake 1.16.5 / config.guess 2.72
  (已识别 HarmonyOS), CI 无系统 automake 且 automake 1.18 的 config.guess 不识别
  HarmonyOS → 必须依赖 build_requirements tool_requires + system perl 手动
  bootstrap + config.guess 补丁 (方案来自 burp2/2.1.0 先例)
- 官方 tarball 源 (Savannah) 已失效, 用 sigma-star GitHub 镜像
- 工具安装到 sbindir (--prefix=/ 时即 /sbin), package_info.bindirs=["sbin"]
---

**编译结束**: 2026-10-18 02:31
**最终状态**: built
