# w-calc

w-calc 是一个任意精度的命令行科学计算器，基于 GMP 与 MPFR。它支持算术表达式、
变量、多种进制、单位换算以及交互式标准输入。许可证为 GPL-2.0-or-later。

## OpenHarmony PC 适配

Conan 配方使用 OHOS 原生 Clang 工具链构建 w-calc 2.5，依赖已发布的
`gmp/6.3.0` 与 `mpfr/4.2.2.1` Conan 包。readline 为可选依赖，本适配通过
`--without-readline` 关闭；命令历史与补全不可用，但标准输入交互不受影响。

上游 `configure` 脚本以 `umask 077` 创建 `config.status` 的临时目录，在 OHOS
HMDFS 上该目录对构建用户不可写，`config.status` 会以 `subs1.awk: Permission
denied` 失败。仅在 `os=OHOS` 时应用的补丁 `patches/0001-configure-hmdfs-umask.patch`
将该处 umask 改为 `022`。

配方在 `build()` 中真实运行上游 `make check`：`test/Makefile.am` 登记的 21 个
automake 测试全部执行，其中 12 个正向测试 PASS、9 个上游声明的预期失败（XFAIL）
按预期结果计为通过，0 FAIL、0 ERROR。消费者视角测试另执行打包后的 `bin/wcalc`
共 8 项确定性断言。

上游项目主页：https://wcalc.sourceforge.net/
