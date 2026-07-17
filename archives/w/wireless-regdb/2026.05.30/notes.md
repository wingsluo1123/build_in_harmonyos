# wireless-regdb 2026.05.30 适配笔记

## 编译环境
- 构建系统: makefile (无 configure)
- 编译日期: 2026-07-15
- 状态: built
- 平台: HarmonyOS PC (aarch64)

## 编译步骤
- `make -j1` → PASS
- `make install DESTDIR=$TEST_PREFIX PREFIX=/usr` → PASS

## 遇到的问题与解决方案
- wireless-regdb 是纯数据包 (regulatory database)，无 ELF 二进制文件
- Python 脚本 shebang `#!/usr/bin/env python` 在 OHOS 上不存在，需改为 `#!/usr/bin/env python3`
- gen-pubcert.sh shebang `#!/bin/bash` 在 OHOS 上不存在，需改为 `#!/usr/bin/env bash`
- 补丁: 0001-fix-shebangs-for-ohos.patch (修复所有 shebang)

## 验证结果
- regulatory.bin, regulatory.db, regulatory.db.p7s 生成成功
- 安装文件:
  - /lib/firmware/regulatory.db
  - /lib/firmware/regulatory.db.p7s
  - /usr/lib/crda/regulatory.bin
  - /usr/lib/crda/pubkeys/wens.key.pub.pem
  - /usr/share/man/man5/regulatory.bin.5.gz
  - /usr/share/man/man5/regulatory.db.5.gz
---

**编译结束**: 2026-07-15 18:28
**最终状态**: built
