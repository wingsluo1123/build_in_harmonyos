# DRAFT: 框架自动补的 `.local` 主机名在无 mDNS 应答器的 OHOS 上不可解析

## 现象

pappl 1.4.12 上游 `testpappl -t all` 中 `jpeg/png` 类别（远程连接路径
`connect_to_printer(system, /*remote*/true, ...)`）**必然失败**：

```
jpeg: Connect to server: FAIL (Unable to connect: Name does not resolve)
png: SKIP
pwg-raster: SKIP
client-10x1000: SKIP
```

而 `client`/`pwg-raster` 类别（用字面量 `localhost` 连接）全部通过。

## 机制（逐层排除后的定位）

1. 探针程序：`papplSystemCreate` + `papplSystemGetHostName` 在设备上返回
   **`localhost.local`**；
2. libc 无辜：`gethostname()` 返回 `localhost`；`gethostbyname("localhost")`
   的 `h_name` 也是 `localhost`（musl 走 /etc/hosts 命中，无域名补充）；
3. **库代码所为**：pappl 的 `_papplSystemSetHostNameNoLock(system, NULL)` 在
   裸主机名（无 `.`）时主动追加 `.local`（mDNS 惯例，依赖
   avahi/nss-mdns 解析）；
4. OHOS 无 mDNS 应答器、无 nss-mdns → `localhost.local` 落到单播 DNS →
   NXDOMAIN → `EAI_NONAME`。

即：**这是「服务发布方按 mDNS 惯例命的名」与「解析环境没有 mDNS」之间的
结构性缺口**，不是 libc bug，也不是 pappl bug。

## 修复（testsuite 层回退，PR #15060 补丁 0003）

`connect_to_printer()` 在主机名连接失败且非 `localhost` 时，改用 loopback
重试（并重建 `printer-uri`）。不改断言、不改判定；上游全 6 类别
（含 10×1000 并发压力）随后全绿。

## 判别要点

- 裸主机名连接（`localhost`）不受影响（/etc/hosts 有 127.0.0.1 localhost）；
  只有 mDNS 风格限定名受影响；
- DNS-SD **注册失败**是另一条（pappl 按设计降级为日志错误
  `Unable to initialize DNS-SD: Daemon not running`，测试不受影响）；
  本条专门处理「把自己广播名当连接目标」的路径；
- 修 B 侧（消费方回退）而非 A 侧（库命名规则）。

## 禁止策略

1. 禁止剥掉库的 `.local` 后缀「修测试」——mDNS 网络上服务会找不到；
2. 禁止配方写 `/etc/hosts`——需要 root，且污染全局环境。

## 查重证据（2026-10-08，main tip）

- `git grep -i mdns/avahi/dns_sd/.local/hostname` 于 knowledge/：仅
  DRAFT-shairplay（**构建期** dns_sd.h 头文件门控，dlopen 路径——不同
  子族）、E443（autotools bootstrap，撞 avahi-glib 关键词）、E457（glib
  静态重复运行时）；
- `knowledge/graph/index.tsv` 无任何 mDNS/dnssd/hostname 行；
- musl-glibc 对比表只覆盖 libc API，不覆盖名称解析策略。

来源：pappl 1.4.12 适配（PR #15060，补丁 0003）。
