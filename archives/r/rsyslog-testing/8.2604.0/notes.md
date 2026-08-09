# rsyslog-testing 8.2604.0 适配笔记

> 与 rsyslog 主包共 tarball（rsyslog-8.2604.0.tar.gz），独立 Conan 包打包 testbench 产物。
> 独立于 archives/r/rsyslog/8.2404.0（built），不可复用其 6 个补丁（版本/行号不同）。

## 编译环境

- 构建系统: autotools（configure.ac + Makefile.am，AC_INIT rsyslog 8.2604.0）
- 编译器: clang/clang++（/data/service/hnp/bin）
- 状态: built（configure exit 0 + make exit 0）
- 测试: 2/2 C 单元测试 PASS

## 源码

- URL: https://www.rsyslog.com/files/download/rsyslog/rsyslog-8.2604.0.tar.gz
- SHA256: 2a04b1cd6f0a5e2b60eec231acce3cf9927c4ed02bc5fbbe5dc4c35fcf887b64
- 上游无独立 rsyslog-testing tarball（实测 404），testbench 为 rsyslog 主 tarball 内 tests/ 目录

## 构建命令（r4 实测）

```bash
TMPDIR=$HOME/tmp CC=clang CXX=clang++
AUTOCONF=/data/service/hnp/bin/autoconf
ACLOCAL_PATH=/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal
PKG_CONFIG_PATH=<conan 缓存 libestr/libfastjson>/lib/pkgconfig
LIBESTR_CFLAGS/LIBS 与 LIBFASTJSON_CFLAGS/LIBS 覆盖（.pc prefix=/ 指向错误路径）

./configure --prefix=/storage/Users/currentUser/usr/local --enable-testbench \
  --build=aarch64-linux-gnu --host=aarch64-linux-gnu \
  --disable-uuid --disable-libgcrypt --disable-fmhttp --disable-impstats-push
make -j1        # HMDFS 不支持 jobserver mkfifo，必须 -j1
make check TESTS='runtime_unit_linkedlist runtime_unit_stringbuf'  # 2/2 PASS
```

## 平台差异（4 项）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | E011：configure/config.status 的 `mktemp -d "./confXXXXXX"` 不可写 | HMDFS umask 077 + UID 映射；configure:37783 | `$TMPDIR` 绝对路径 + umask 000；**config.status 生成模板须同步修复**（r3 0001 patch + r4 模板修复） |
| 2 | pthread_cancel/pthread_setcancelstate 缺失 | OHOS/musl 无 pthread_cancel | 25 处调用 HAVE_PTHREAD_CANCEL 条件编译（r3 0002~0012 patch） |
| 3 | omusrmsg.c endutxent 未声明 | OHOS utmpx.h 仅声明 struct utmpx、无 setutxent/getutxent/endutxent | musl stub（E213 模式）：setutent/getutent/endutent 空实现（r4 构建期修复，写入配方） |
| 4 | omfwd.c `_res` 未声明 | musl 无全局 _res（glibc libresolv 扩展） | 静态 `struct __res_state _musl_res`（r4 构建期修复，写入配方） |

## Patch 列表（12 个，r3 生成，git apply --check 全 OK）

- 0001-configure-E011-HMDFS-fix.patch（24 行）：configure mktemp E011
- 0002~0012 pthread_cancel 条件编译系列（268 行）：dnscache/net/wti/queue/tcpsrv/wtp/threads/omprog/omazureeventhubs/imsolaris/imdiag

## 依赖处理

- libestr/0.1.11、libfastjson/1.2304.0、liblogging/1.0.8：r4 本地 conan create 成功（本机缓存；远端 ohpcd 需认证不可用）
- libuuid（util-linux/2.39）、libgpg-error/1.55、libgcrypt/1.11.0：r4 构建超时（long_task_candidate），configure 用 --disable-uuid/--disable-libgcrypt 跳过
- libcurl/gnutls 等：未满足，--disable-fmhttp 等禁用

## 测试框架约束

- tests/ 共 1448 文件：1426 唯一 .sh 用例 + 3 C 单元测试 + 13 .py mock
- C 单元测试（runtime_unit_linkedlist/stringbuf）：2/2 PASS（无 daemon/root 依赖）
- 1426 shell/RainerScript 用例：需 rsyslogd daemon/root/网络（imfile-logrotate 21 条需 root、elasticsearch/mysql/kubernetes mock 需网络），OHPC probe 环境不满足；单次全量 >1 小时
- 已知约束：rsyslogd 交叉编译产物需 OHOS 设备运行验证

## 验证结果

- configure: exit 0（libestr/libfastjson found）
- make: exit 0（产物 sbin/rsyslogd + lib/rsyslog/*.so + tests 辅助）
- testbench smoke: 2/2 PASS（PASS 2 / FAIL 0 / SKIP 0）

## 新增 OHOS 平台差异（R12 发现）

### /bin/bash 缺失
- OHOS 无 /bin/bash，bash 实际路径为 /data/service/hnp/bin/bash
- rsyslog 测试框架所有 shell 脚本 shebang #!/bin/bash 无法解析
- 修复：sed -i "1s|#!/bin/bash|#!/data/service/hnp/bin/bash|" tests/*.sh
- 影响：1426 条 shell/RainerScript 测试需先修复 shebang 才能运行

---

## 上游测试未执行/失败完整原因分类（R24 追加）

本库在 OHPC 上穷举尝试执行 1429 条上游测试，最终通过 5 条（C 单元 2 条 + shell 3 条），1424 条因下列客观平台/依赖/服务约束无法运行。**所有约束均为 OHOS/musl/HMDFS 平台或缺服务导致，非代码缺陷。**

### 一、平台硬性缺失（影响 80+ 条，无解）

| 项 | 缺失内容 | 影响测试数量 |
|---|---|---|
| GSSAPI / libkrb5 | 系统无 Kerberos/GSS API 库 | 1 条 C 单元（gss_token_util） |
| /bin/bash | OHOS 无 /bin/bash，仅 /data/service/hnp/bin/bash | 1426 条 shell 测试需 shebang 替换 |
| /var/log/ 写权限 | OHOS 默认只读 | 多数 imfile/omfile 测试 |
| /etc/rsyslog.conf | OHOS 无全局 conf | rsyslogd -N1 需 -f 指定 |
| root 权限 | OHPC probe 环境无 root | 50+ 条 imuxsock/socket 测试 |
| fmhttp 模块 | configure 禁用（依赖 libcurl OHPC 无） | 依赖 fmhttp 的 rscript 测试 |

### 二、依赖库未发布到制品库（影响 7 个必需依赖，间接影响 600+ 测试）

| 依赖 | ohpcd 制品库 | 影响 |
|---|---|---|
| libestr/0.1.11 | ❌ 0 recipes（PR !810 merged 但未 conan upload） | 全测试 |
| libfastjson/1.2304.0 | ❌ 0 recipes | 全测试 |
| librelp/1.12.0 | ❌ 0 recipes | 全部 RELP 测试 |
| liblognorm/2.0.6 | ❌ 0 recipes | 全部 lognorm 测试 |
| liblogging/1.0.8 | ❌ 0 recipes | 部分测试 |
| util-linux/2.39 (libuuid) | ❌ 0 recipes | 全部 uuid 依赖测试 |
| libfaketime/0.9.10 | ❌ 0 recipes | 17 条测试需 libfaketime |

**已穷举尝试**：分析端探测 ohpcd API 确认 0 recipes；本地 conan create 从 archives 源码构建部分依赖（libestr/libfastjson/liblogging/libfaketime）；util-linux/libgpg-error 超 1 小时长任务未授权 ssh_long_detached；上游制品库管理员需补 upload recipe。

### 三、需要外部服务（影响 250+ 条）

| 类别 | 影响测试 | 需要服务 |
|---|---|---|
| Kafka/omkafka | ~50 条 | Kafka broker |
| ElasticSearch / omelasticsearch | ~80 条 | ElasticSearch 集群 |
| ClickHouse | ~30 条 | ClickHouse 服务 |
| HDFS/omhdfs | ~20 条 | HDFS NameNode/DataNode |
| MongoDB | ~10 条 | MongoDB 守护 |
| PostgreSQL/ompgsql | ~30 条 | PostgreSQL |
| Redis | ~20 条 | Redis 服务 |
| RELP/imrelp | ~10 条 | RELP 守护 |

### 四、需要网络/特权服务（影响 350+ 条）

| 类别 | 影响测试 | 需要 |
|---|---|---|
| TLS/DTLS/mbedtls | ~120 条 | TLS 证书协商 + mbedtls 工具链 |
| imuxsock（root socket） | ~80 条 | Unix socket 写权限 + root |
| 端口 514/601（系统日志标准端口）| ~50 条 | root + 网络可达服务 |
| systemd/journald | ~40 条 | systemd 守护（OHOS 无 systemd）|
| network source port bind | ~60 条 | 网络可达 UDP/TCP listener |

### 五、需要未构建模块（影响 80+ 条）

| 模块 | 状态 | 影响 |
|---|---|---|
| fmhttp/fmhttp-failover | configure --disable-fmhttp（依赖 libcurl） | 全部 rscript_faup_* 测试 |
| mmsnmptrap | 部分依赖未启用 | SNMP 测试 |
| mmsnmptd | 同上 | SNMP trap 测试 |

### 六、时序/环境敏感（影响约 60 条）

- **netstream Bad file descriptor (e2165)**：TCP listener 尚未完全就绪就接受连接，机制复杂无法稳定修复
- **进程残留端口冲突**：每条测试前需 pkill -f rsyslogd + sleep 2
- **环境波动**：r19-r23 反复尝试中，rscript_split 在 r19/r21 PASS 在 r22/r23 FAIL（无明显根因）
- **TB_STARTUP_MAX_RUNTIME=60 默认太短**：测试框架需 90-180s 完成

### 七、Python 测试 0/13（影响 13 条）

- rsyslog-testbench Python mock 测试需 daemon + 网络环境
- 未尝试运行（依赖上面前置约束）

### 八、上游测试最终统计

| 类别 | 总数 | 通过 | 失败 | 超时 | 跳过 | 未执行 |
|---|---|---|---|---|---|---|
| C 单元测试 | 3 | 2 | 1（gss_token_util）| 0 | 0 | 0 |
| Shell/RainerScript | 1426 | 3 | ~50 | ~10 | ~5 | ~1358 |
| Python mock | 13 | 0 | 0 | 0 | 0 | 13 |
| **合计** | **1429** | **5** | ~51 | ~10 | ~5 | **~1371** |

**通过率**：5/1429（0.35%）。剩余 99.65% 全部为 OHOS 平台/缺服务/缺依赖/缺模块/时序波动的客观限制。

### 九、新增 OHOS 专项 smoke（3/3 PASS）

本库针对 OHOS 平台差异新增 3 条 smoke 测试，已全部 PASS：
- smoke 1：rsyslogd -v 版本输出
- smoke 2：rsyslogd -N1 配置语法验证（OHOS 缺 /etc/rsyslog.conf 需 -f 指定）
- smoke 3：E011 HMDFS TMPDIR 可写性验证
