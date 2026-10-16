# DRAFT — 静态链接时 .init_array 顺序导致的启动 SIGSEGV

**草稿 ID**：`DRAFT-indi-nexdome-1.5-static-init-order`
**来源**：indi-nexdome 1.5+20221222183051 适配（HarmonyOS PC / aarch64）

## 现象

在本平台，libindi 的共享对象（`libindidriver.so.2` / `libindiAlignmentDriver.so.2`）
无法被加载，消费者被迫静态链接 INDI 框架。随后 `indi_nexdome -h` **启动即
SIGSEGV（exit 139），且没有任何输出**。

## 最小复现与定位

1. 只链接 INDI 静态库、不构造任何全局设备对象：`t5 -h` 正常打印框架 usage。
2. 增加一个**全局** `INDI::Dome` 子类实例：`t6 -h` 立即 SIGSEGV。
3. 在派生类构造体首行打点：**打点未执行** → 崩溃发生在基类 `INDI::Dome::Dome()`
   构造期间（成员初始化阶段）。
4. 把驱动目标文件/对象**放在 INDI 静态库之后**链接：
   `clang++ -o t6b -Wl,--start-group <libs> -Wl,--end-group t6.o`
   → 打印 `c1/c2/c3` 与 usage，**恢复正常**。

## 根因

链接器按输入文件顺序把各目标文件的 `.init_array` 拼接进最终映像。可执行文件
**自己的目标文件永远排在它链接的静态库之前**，因此驱动程序中需要框架初始化的
全局对象，会先于框架静态库自身的静态初始化器（`defaultdevice.cpp.o` /
`indilogger.cpp.o` / `sharedblob_parse.cpp.o` 均含 `.init_array`）运行。

- 共享库场景不触发：加载器先完成共享库的初始化，再跑可执行文件的初始化。
- 仅当「可执行文件自身含全局对象 + 依赖库也带静态初始化器 + 静态链接」三者同时
  成立才触发。

## 修复（primary）

把可执行文件自身的源码编成一个 STATIC 库，并用 `--whole-archive` 把它放在依赖
框架静态库**之后**链接：

```cmake
add_library(indi_nexdome_driver STATIC ${indi_nexdome_SRCS})
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/stub.c "/* intentionally empty */\n")
add_executable(indi_nexdome ${CMAKE_CURRENT_BINARY_DIR}/stub.c)
target_link_libraries(indi_nexdome
    -Wl,--start-group ${INDI_LIBRARIES} ${DEPS} -Wl,--end-group
    -Wl,--whole-archive indi_nexdome_driver -Wl,--no-whole-archive)
```

复现程序 `t6`（前置）由 SIGSEGV 变为 `t6b`（后置）正常打印 usage；正式驱动由
SIGSEGV 变为正常应答 INDI 协议 getProperties。

## 误判提示

- `__attribute__((constructor(65535)))` 无效：默认优先级已是 65535，同优先级
  仍按链接顺序。
- 不要把它错判为「代码签名 / codesign 失效」：后者表现为 `Operation not permitted`；
  本题是干净地 SIGSEGV。
- 与 E457（静态/共享混用导致运行时重复拷贝）、E444（GObject `.init_array` 显式
  init 入口）相关但不同：本条目是链接器拼接**顺序**问题。
