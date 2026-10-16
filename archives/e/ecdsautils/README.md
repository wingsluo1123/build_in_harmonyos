# ecdsautils

ECDSA signing / verification command line tools and small companion library
from the freifunk-gluon project.

- 上游: https://github.com/freifunk-gluon/ecdsautils
- 版本: 0.4.2 (tag `v0.4.2`)
- 构建系统: CMake
- 许可: BSD-2-Clause
- 硬依赖: libuecc (upstream `find_package(libuecc REQUIRED)`)

产物:

| 产物 | 说明 |
|---|---|
| `lib/libecdsautil.a` | `libecdsautil` 目标、`OUTPUT_NAME ecdsautil` |
| `bin/ecdsautil` | 多合一 CLI，`-s/-p` 走 ecdsakeygen、`-n` 走 ecdsasign 等 |
| `bin/ecdsakeygen` `bin/ecdsasign` `bin/ecdsaverify` | 安装期 `ln -sf ecdsautil` 生成的软链 |
| `lib/pkgconfig/ecdsautil.pc` | pkg-config 元数据 |
| `include/ecdsautil-0.4.2/ecdsautil/{ecdsa,sha256}.h` | 公开头文件 |
