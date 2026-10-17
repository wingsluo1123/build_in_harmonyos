# SWI-Prolog 10.0.2 原生适配

路径 C 候选；任务 10947，分支 `feat/swi-10.0.2`。最终归类由委员会确认。
源码使用官方完整发布归档，SHA256 `e42cc098f7b8a6051c4f79a99b55162d467098aba60f69649bdc7583f0734b57`。

## 构建范围

原生 OHOS/aarch64、Release、SDK clang 15。保留线程、引擎、信号、GC、GMP、
BASIC、JSON、PCRE、YAML、SSL、archive、libedit。未构建六个可选扩展组：
GUI、Java、Python/Janus、ODBC、Berkeley DB、TIPC。
源码清点为 633 个 C、10 个 C++、1264 个 Prolog 文件。

## 三项补丁

1. `0001`：上游对 ELF 模块默认不链接 libswipl；OHOS 的动态加载闭包导致
   `PL_open_foreign_frame: symbol not found`。增加显式链接开关并启用，保留真实 FLI。
2. `0002`：上游安装脚本覆盖用户 RPATH；保留传入的相对 `$ORIGIN` 路径，并在链接时
   直接使用最终安装 RPATH，防止安装后修改 ELF 而破坏工具链生成的代码签名。
   安装后二进制和扩展均已逐个核对，复制包后的资源定位和扩展加载已运行验证。
3. `0003`：备用信号栈是 OS 线程资源，不能随可迁移的 Prolog engine 释放。
   原实现在线程结束前直接释放仍注册的 backing memory，真机会在后续分配中崩溃。
   用 pthread key 由拥有者线程管理：同一 OS 线程的多个 engine 复用，退出时先
   `sigaltstack(SS_DISABLE)` 再 free。查询/注销失败保留内存；单线程配置也先注销。

## 决定性对照

- 独立 C 程序：线程注册备用栈后直接 free，循环返回 139；先注销再 free，1000 次通过。
- 修复后的 Release：连续 1000 次线程创建回收通过；主线程创建 engine、worker 销毁，
  同时核对主线程备用栈地址稳定，1000 次通过。
- 消费者固定覆盖 1000 次线程复用和 100 次跨线程 engine 销毁；没有关闭信号/GC/线程，
  没有用 ASan 产物代替 Release，也没有排除上游失败组。
- 回收机制按既有 E224 复用；另就初始化不干扰宿主既有注册补充 B 候选，见知识草稿及 b-host-altstack 报告。

## 配方与环境

- CMake 明确目标 Linux/POSIX 构建逻辑，包内架构名为 `aarch64-ohos`；原生执行包装器
  让 `try_run` 实际执行；mkvmi/defatom 使用 profile 中的编译器。
- 系统同名依赖静态链接；libarchive 由 Conan imported target 保留传递依赖。
- build/package 通过有作用域的 VirtualRunEnv 提供 host 共享依赖，再加入 build/src；
  这使构建时工具使用最终相对 RPATH 仍可加载 archive，安装后不泄漏构建目录。
- 使用已发布 libedit；Conan CMakeToolchain list 用分号字符串，避免 Python list 路径。
- 上游旧 Find 模块优先，显式检查 archive/PCRE/YAML/SSL 四个测试组均注册。
- HMDFS 不能创建 Unix socket 路径端点；原生 `/data/storage/el2/base/temp` 可以。
  配方用真实 bind 探针选择任务私有目录，同时传 `TMP`、`TMPDIR`、`TEMP`。
  原始 AF_UNIX、MQI 测试保持原样并通过。
- 验证使用任务独立 Conan 缓存，避免与共享缓存中的其他构建互相写入；没有安装第二套工具链。

## 测试口径与结果

上游：全部 **84/84 CTest 组通过**，耗时 168.2 秒；无排除列表。
消费者：**29/29 Prolog + 1/1 C embedding = 30/30**；`conan create` RC=0。
另验证复制包后的 CLI、资源目录、GMP、SSL/archive 加载和 1000 次线程循环。

静态清点：221 个 `.pl` 文件中 `^\s*test\(` 共 4035 条声明，其中六个未启用扩展目录
占 366 条。它们是静态声明口径，不能当成全部逐条运行的 4035/4035；组内条件执行
和动态展开由原始上游框架负责。本次实际执行结果按 84 个注册组记录。

```sh
conan create archives/s/swi/10.0.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -c tools.build:jobs=1
ctest --show-only=json-v1
```

原生完整 create 日志 SHA256：`e7d1df394f0a6eb4355583916dd89d0da3aea633ff35b4e0df50cad27d797957`。
包尚未由合并后的 release 流水线上传，元数据状态为 `built`。

## B 知识补强候选

初始化前已有宿主备用栈时，借用不产生覆盖、注销或释放权。E224-only回收修复控制仍在初始化覆盖宿主注册；当前补丁保留。新增地址/大小/标志三元组回归及官方calc未改示例对照均通过，细节见 reports/b-host-altstack.md。消费者仍按29+1=30计数；新断言后conan test RC0。该候选补充E224，不声称同族零命中，B资格与转正方式待复审。

## CI 并发资源限制

CI #93279在CMake配置完成后以-j20运行Ninja，posix_spawn返回Resource temporarily unavailable。主构建与消费者追加build_tool_args=["-j1"]，把本包构建限制到已验证的单任务方式；不改公共profile/CI脚本。jobs=20下的消费者30/30再通过，6任务Ninja探针最大同时运行数=1。生产源代码/三补丁及84组测试范围未变；详见reports/ci-serial-build.md。
