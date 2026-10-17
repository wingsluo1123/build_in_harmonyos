# DRAFT-13369：没有 configure 的 autotools 快照 → 配方内直编

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-17
> Source: libosmo-cc 0.0-git20240818.7864594（`archives/l/libosmo-cc`）
> 对应：`knowledge/drafts/DRAFT-13369-autotools-snapshot-without-configure-direct-clang-build.kv`

## 现象

```text
$ autoreconf -fi
Can't exec "aclocal": No such file or directory
autoreconf: error: aclocal failed with exit status: 2
```

包只有 `configure.ac` + `Makefile.am`，没有 `configure`；设备有 autoconf 2.72，
但**没有 automake/aclocal/libtoolize**；上游 Gitea 也没有 release/tag 包。

## 与 DRAFT-10035 的边界

`DRAFT-10035-wmcdplay-1.1-autotools-bootstrap-ohos` 已经记录了通用的 autotools
自举方法：声明 `tool_requires("automake/1.18")`，再分步执行
`aclocal → autoconf → automake`。

本条不是重复该做法，适用的边界不同：

1. `libosmo-cc/configure.ac` 使用 `LT_INIT` / `AC_PROG_LIBTOOL`，还需要
   `libtoolize` 和 `libtool.m4`；
2. 检查制品仓时，`automake/1.18` 存在，但 `libtool/2.4.7` 不存在，
   因此 DRAFT-10035 的方案仍不能在当前制品仓完成全部自举；
3. 本包只有 11 个 C 文件，没有 `config.h`、生成头或需要 configure 探测的
   特性，适合直接 clang 编译；
4. 只要缺少 `config.h`/生成头且没有实质特性探测，这类低复杂度快照可直编；
   一旦项目依赖这些生成物，或 bootstrap 工具链已经补齐，仍应优先使用
   DRAFT-10035 的标准 autotools 流程。

## 根因

1. autotools 引导链缺 automake 侧工具（aclocal/automake/libtoolize），无法生成 `configure`/`Makefile.in`；
2. 没有带 `configure` 的官方发布包可替代；
3. 直编还需复现 libtool 的行为：soname、`.so`/`.so.N` 链接、`.pc`、`-no-undefined`。

## 正确做法（配方内直编）

```python
get(self, **self.conan_data["sources"], filename="libosmo-cc.tar.xz", strip_root=True)

clang -shared -fPIC -O2 -include sys/time.h \
      -I<src>/include -I<libosmocore> -I<talloc> ... \
      src/*.c \
      -Wl,-soname,libosmocc.so.2 -Wl,--no-undefined \
      -L<libosmocore> -L<talloc> ... -losmocore -ltalloc ... \
      -o libosmocc.so.2.0.0
```

package()：安装 `.so.2.0.0` + `.so.2`/`.so` 链接 + `include/osmocom/cc/*.h` + `libosmocc.pc`。

## 踩到的四个细节

| 细节 | 现象 | 处理 |
|---|---|---|
| snapshot URL 无扩展名 | `BadZipFile` | `get(..., filename="*.tar.xz")` |
| 依赖包缺主体库 | 消费者 `undefined reference ... referenced by libosmocc.so` | 显式 `-losmocore`；构建加 `--no-undefined` |
| musl 头包含 | `incomplete type 'struct timeval'` | `-include sys/time.h` |
| talloc 头链 | `talloc.h not found` → `talloc_strdup` 隐式声明 | include 路径取全部 host 依赖 |

## 验证（libosmo-cc 实测）

```text
CREATE_RC=0
libosmocc.so.2.0.0 + .so/.so.2 + libosmocc.pc + 11 headers
[ok] OSMO_CC_VERSION is OSMOCCv1
[ok] osmo_cc_msg_value2name(SETUP_REQ)
[ok] IE value/name round-trip
LIBOSMO_CC_CONSUMER_CHECKS=3 FAILURES=0 / LIBOSMO_CC_CONSUMER_OK
```

## 反例（禁止）

- 直编不加 `-Wl,--no-undefined` → 产出带未解析符号的 `.so`，构建"成功"但消费者失败；
- 只改 `configure.ac`/`Makefile.am` 以为能生效（没有 automake 重生成，构建系统根本不读）。

## 通用化建议

1. 判断能否直编：源码是否依赖 `config.h`/生成头、是否有大量特性探测；简单库直编成本最低，
   复杂库仍应优先找带 `configure` 的 release tarball。
2. 直编要复现 libtool 的四件事：soname、符号链接、pkg-config、`-no-undefined`。
3. 依赖包的 `cpp_info.libs` 可能只列传递库（libosmocore 就是），关键主体库要显式补，
   并用消费者链接（最好带 `--no-undefined`）验证。
