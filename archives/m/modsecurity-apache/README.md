# ModSecurity v2 Apache 模块（modsecurity-apache）

ModSecurity v2 是开源 Web 应用防火墙（WAF），本目录适配其 Apache2 连接器
`mod_security2.so`（规则引擎、请求体解析、审计日志），版本 2.9.13。

## OHOS 适配要点

- **构建系统**：autotools。源码包自带 generated `configure`，无需 autoreconf。
- **平台识别**：modsecurity、apr-util、httpd 三套 `config.guess/config.sub`
  默认都不认识 HarmonyOS。配方在 `build()` 内用 Python 复刻仓库
  `scripts/patch-autotools-ohos.pl` 的 5 处修改（E007），`score<4` 直接失败，
  不猜数字、不绕 `--build/--host`。
- **依赖链**：apr / pcre / pcre2 / libxml2 / lua / curl / yajl 直接消费已发布的
  Conan 包；apr-util 与 httpd 尚无可消费的 Conan 包，配方从官方 Apache 归档
  私有构建（apr-util 取静态 PIC，httpd 只为提供 apxs 与头文件），构建产物
  不进包，包内只有 `mod_security2.so` 与配置资源。
- **mlogc 关停**：上游 `--disable-mlogc`（日志收集守护进程是独立交付物）。
- **上游测试**：`make check` 跑 `tests/run-unit-tests.pl`（58 个 `.t` 文件，
  tfn 29 + op 29 + action 空），回归测试需 live Apache，不在 `check` 内。

## 产物

- `lib/mod_security2.so`（Apache DSO，直接 `LoadModule`）
- `lib/modules/mod_security2.so`（同文件，APXS_MODULES 布局的副本）
- `res/modsecurity.conf-recommended`、`res/unicode.mapping`

## 参考

- 上游：https://github.com/owasp-modsecurity/ModSecurity
- 发布页：https://github.com/owasp-modsecurity/ModSecurity/releases/tag/v2.9.13
- 文档：https://github.com/owasp-modsecurity/ModSecurity/wiki/Reference-Manual-(v2.x)
