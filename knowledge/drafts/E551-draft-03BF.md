# E551（草稿）libxml2 2.11+ 对旧消费者的两处破坏：`xmlEntity.checked` 移除与 nanohttp 声明被宏隐藏

- **状态**: 草稿（待主编审核提升编号）
- **严重度**: 3
- **类别**: libxml2, dependency, portability
- **来源**: raptor2/2.0.16 适配（路径 A，2026-10-16；依赖 OHPCD libxml2/2.15.3.1）
- **与既有条目的关系**: 见文末「去重与新增点」

## 错误特征

```
src/raptor_libxml.c:256:14: error: no member named 'checked' in 'struct _xmlEntity'

raptor_www_libxml.c:113:15: warning: call to undeclared function 'xmlNanoHTTPMethod';
                            ISO C99 and later do not support implicit function declarations
raptor_www_libxml.c:113:13: error: incompatible integer to pointer conversion
                            assigning to 'void *' from 'int'

# 以及（不报错但功能静默退化的形态）
checking WWW libraries available...  libxml 2.15.3.1
checking WWW library to use... libxml 2.15.3.1 via pkg-config     # 默认本应是 libcurl
```

## 触发条件（最小复现）

1. 取任一「老消费库 + 新 libxml2」组合：
   ```sh
   grep -n 'xmlEntity' <libxml2_prefix>/include/libxml2/libxml/entities.h   # 2.15 中无 checked 字段
   grep -c 'LIBXML_HTTP_STUBS_ENABLED' <libxml2_prefix>/include/libxml2/libxml/nanohttp.h
   ```
   `nanohttp.h` 中所有 `xmlNanoHTTP*` 声明都包在 `#ifdef LIBXML_HTTP_STUBS_ENABLED` 内；OHPCD
   libxml2/2.15.3.1 未开启 HTTP stubs（该宏未定义）→ 头文件在但函数无声明 → 隐式声明 → clang 报 int→指针转换错误。
2. raptor2 2.0.16 的 `configure.ac` 存在一处探测缺陷，使"上游默认 libcurl 后端"静默失效：
   只有在 **找到 `curl-config` 脚本** 时才执行到 `have_libcurl=1`；当 libcurl 仅由 pkg-config 发现
   （`CURL_CONFIG` 为空）时 `have_libcurl` 恒为 0，于是 `--with-www=curl`（默认值）在
   `for www_name in $www curl xml libfetch none` 循环里轮到 `curl` 分支不成立、继续落到 `xml` 分支。

## 根因

| 现象 | 根因 |
|---|---|
| `no member named 'checked'` | libxml2 **2.11.0** 移除了 `struct _xmlEntity` 的私有字段 `checked`（其语义并入内部 `flags`）。老库（如 raptor2 的 CVE-2012-0037 XXE 防护补丁）守卫只有下界 `#if LIBXML_VERSION >= 20627`，在上界失效 |
| `xmlNanoHTTPMethod` 未声明 | libxml2 **2.13** 起 nanohttp 不再是默认公开 API，声明被 `#ifdef LIBXML_HTTP_STUBS_ENABLED` 包住；发行版若未以 `--with-http` 构建，声明即不可见 |
| www 后端静默从 curl 退化为 xml | 探测缺陷（见上）＋ nanohttp 不可用，二者叠加：既丢了上游默认功能，又恰好选中一个编译不过的后端 |

## 解决方案

1. **`xmlEntity.checked`**：把守卫补上界，与上游/发行版既定修复一致（SUSE `hotfix-libxml-2.11.patch`）：
   ```diff
   -#if LIBXML_VERSION >= 20627
   +#if LIBXML_VERSION >= 20627 && LIBXML_VERSION < 21100
        /* Mark this entity as having been checked - never do this again */
        if(!ret->checked)
          ret->checked = 1;
    #endif
   ```
   注意：libxml2 ≥ 2.11 自身已把"实体已解析"语义落到内部 `flags`（`XML_ENT_PARSED`），因此跳过该赋值是正确降级，不是丢功能（另见 CVE-2024-40896 的分析）。
2. **nanohttp 不可用**：不要继续用 libxml WWW 后端，改走 libcurl（上游默认），并修探测守卫：
   ```diff
   -if test "X$CURL_CONFIG" != X; then
   +if test "X$CURL_CONFIG" != X || test "X$libcurl_source" = "Xpkg-config"; then
      CPPFLAGS="$CPPFLAGS $LIBCURL_CFLAGS"
      LIBS="$LIBS $LIBCURL_LIBS"
   ```
   同时在 `configure.ac` 做同一处修改，使 configure 日后重新生成仍保留该修复。
   **不要**用 Conan 包内自带的 `curl-config` 绕：实测 OHPCD curl/8.22.0 的 `bin/curl-config` 输出指向
   `/…/.cache/conan2/p/b/…`（构建期路径，已失效），走它会注入坏 `-I/-L`；优先 pkg-config 分支。

## 验证方法

```sh
conan create archives/<letter>/<name>/<version> -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 期望：编译通过；configure 摘要为
#   WWW library : libcurl <ver> via pkg-config
# 并且上游测试套件整体退出码 0
```

## 限制与反例

- 若目标 libxml2 是以 HTTP stubs 构建的（`LIBXML_HTTP_STUBS_ENABLED` 已定义），症状 2 不出现；判断必须看头文件/构建配置，不能只看版本号。
- 若消费者显式 `--with-www=none`，症状 2 也不出现，但那属于功能裁剪，不应作为"通过"。
- 本条目针对**下游消费者**；libxml2 自身升级不在范围内。

## 去重与新增点

| 条目 | 覆盖 | 本条的**新增** |
|---|---|---|
| E120 / E132 / E266 / E341 | libxml2.so.16 与 OHOS SDK lld 同名库、LD_LIBRARY_PATH 遮蔽（**运行时**链接问题） | 本条是**编译期 API/ABI 变更**问题，与同名库遮蔽无关；两者在同一任务中同时出现，需分别处置 |
| E216 | CMake/conan 的 libxml2 components/GLOB 用法 | 不涉及 |
| 无既有条目 | — | ①libxml2 2.11 移除私有字段 `xmlEntity.checked` 的**版本上界守卫**模式；②libxml2 2.13+ nanohttp 被 `LIBXML_HTTP_STUBS_ENABLED` 隐藏、导致老库默认 www 后端不可用；③"pkg-config 发现时 `have_libcurl` 不置位"这一类**上游探测缺陷**如何识别（对比 `--with-www` 摘要与依赖检出结果）与修复 |
