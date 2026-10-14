# uniutils 2.28 适配笔记

## 上游信息

- 上游发布页：https://billposer.org/Software/uniutils.html
- 构建系统：Autotools
- 产物：unidesc、uniname、unihist、ExplicateUTF8、unireverse、unifuzz、
  unisurrogate，以及 utf8lookup 脚本

## 构建

```sh
./configure --prefix=<package>
make -j1
make install
```

## OHOS 适配点

`uniname.c` 调用了 `isspace()` 但只依赖旧式隐式声明。OHOS 的 clang 默认按
严格 C99/C11 规则把隐式函数声明视为错误，因此补丁显式加入 `<ctype.h>`。
`configure` 在 `config.status` 阶段使用 `mktemp -d` 创建临时目录；OpenDesk
真机上的 mktemp 目录会得到当前用户不可写的权限，因此第二个补丁改用
`umask 022 && mkdir`。其余源码保持上游原样。

OHOS SDK 的 sysroot 中虽然有 `libintl.h`，但当前 libc 不导出 `gettext`、
`bindtextdomain`、`textdomain`。上游只用头文件存在性决定是否启用 NLS，会
导致编译失败；第三个补丁将 `HAVE_LIBINTL_H` 改为头文件与三个运行时符号
全部可链接时才定义，否则源码自动回退到恒等 gettext 路径。

`unifuzz.c` 与 `putu8.c` 保留了大量 K&R 风格隐式 int 函数。OHOS clang 15 在
严格 C99 下不允许非 void 函数执行无值 `return`，并且 `putchar()`、`time()`
缺少声明；第四个补丁把这些辅助函数改成明确的 `void` 签名并补齐标准头文件。
`unisurrogate.c` 还使用了 BSD 专有的 `u_int32_t` 且 `main` 缺少返回类型；
同一补丁替换为 `<stdint.h>` 的 `uint32_t`，使源码可在 OHOS sysroot 下编译。

OHOS 默认 `char` 为无符号类型，`unireverse.c` 里 `ibuf[i] >= 0` 会把所有字节都误判为 ASCII，并且 `getc()` 的返回值被截断到 `char` 后无法识别 EOF。第五个补丁改用 `unsigned char` 判断 UTF-8 高位，并用 `int` 接收 `getc()` 返回值；该修复保持输入/输出字节顺序不变，只修正平台类型语义。

Autotools 的 `configure` 会在构建目录复制一份 `install-sh`。OpenDesk 的 HMDFS 在复制后没有保留该文件的可执行位，`make install` 会以 `Permission denied` 失败；配方在 `build()` 中显式将生成的 `install-sh` 恢复为 `0755`，不修改上游脚本内容。

此外，上游 `install` 规则的二进制与脚本目标会同时创建同一个 `bin/` 目录。Conan 默认并行安装时会触发 `mkdir ... File exists` 竞争，因此 `package()` 强制使用 `make install -j1`，只串行化安装步骤，不影响前面的并行构建配置。

## 测试

上游没有 `make check` 或正式测试目标。配方不伪造上游测试，而是提供真实的
消费者测试：安装后的 `uniname` 处理包含 `A` 和希腊字母 β 的 UTF-8 输入，
断言输出包含对应的 Unicode 名称；同时检查多个安装程序的 `--help/usage`
入口。

## 已知边界

- `unifuzz` 是随机输入生成器，不作为常规回归测试运行。
- `utf8lookup` 依赖上游 shell 行为，配方只验证它已安装。
