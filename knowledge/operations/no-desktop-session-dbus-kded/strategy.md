# 处理策略：无桌面会话（D-Bus 会话总线 / KDED 装载）

本文件给出检测脚本 `detect-session-bus-deps.sh` 命中后**该做什么、禁止做什么**，以及每一条策略的适用前提与验证口径。

## 策略选择总表

| 命中形态 | 首选策略 | 禁止 |
|---|---|---|
| 上游有「插件 / 独立程序」双形态，且由一项外部能力联动（`cmake_dependent_option(X ... "<能力宏>" <强制值>)`） | **A：触发上游自带降级开关**（零补丁） | 手改上游 CMake 去删 `find_package(KF6DBusAddons)` |
| 上游有双形态但开关默认锁死在插件形态，无联动能力 | **B：显式钉住无会话形态**（缓存变量，不改源码） | 编出插件形态交付（`plugins/kf6/kded/*.so` 在 OHOS 永不加载） |
| 硬依赖只出现在可选的辅助 target（示例/工具/测试） | **C：裁剪该 target**（`-DBUILD_<X>=OFF`） | 为了让示例编过而引入整条 `kdbusaddons` 链 |
| 只有运行期 `SOFT` 命中（`QDBusConnection::sessionBus()`、`KNotification`） | **D：接受运行期降级**，保持上游代码不动 | 删除通知代码 / 落空壳 stub 假装有通知 |
| 上游只有一个纯 KDED 插件形态，无可降级路径 | **E：判定不可交付**（`env_unsupported`） | 硬改上游编插件、或伪造 `kdbusaddons` 顶替 |

## 策略 A：触发上游自带降级开关（首选，零补丁）

**前提**：上游确实存在联动项，且被联动的那项能力在目标平台**真的**不可用（不能为了走捷径把能力探测改成假值）。

以 kwrited 6.7.2 为例，上游原文：

```cmake
cmake_dependent_option(BUILD_AS_EXECUTABLE "Whether to build kwrited as executable" OFF
    "KPty_HAVE_UTEMPTER" ON)
```

- `KPty_HAVE_UTEMPTER` 由 `find_package(KF6 ... COMPONENTS Pty)` 之后的 **KF6Pty 包配置**提供；
- OHOS 侧的 `kpty/6.26.0` 是无 UTEMPTER 构建，包内 `lib/cmake/KF6Pty/...` 导出 `KPty_HAVE_UTEMPTER=FALSE`；
- 于是 `BUILD_AS_EXECUTABLE` 被强制为 `ON` —— 产物是 `bin/kwrited`，**不进入** `find_package(KF6DBusAddons REQUIRED)` 分支。

配方侧需要做的只是把这个事实**验证并记录**（不需要写任何补丁）：

```python
# 形态由 KF6Pty 包配置决定，无需补丁；交付物断言在 test_package/ 里
# 可执行分支把 autostart 文件装到 etc/xdg/autostart/（插件分支才落 plugins/kf6/kded/）
assert os.path.exists(os.path.join(dep.package_folder, "etc", "xdg", "autostart",
                                   "kwrited-autostart.desktop"))
```

**验证口径（三步全要）**：
1. 配置日志里 `BUILD_AS_EXECUTABLE` 的实际取值为 `ON`（`grep` 构建目录的 `CMakeCache.txt`）；
2. 产物落在 `bin/` 而不是 `lib/plugins/kf6/kded/`；
3. 消费者用例实跑该产物（不能只断言文件存在）。

## 策略 B：显式钉住无会话形态（无联动项时）

当上游把形态开关留着但默认值是插件形态时，用**缓存变量**覆盖，不碰源码：

```python
tc.variables["BUILD_AS_EXECUTABLE"] = "ON"     # 或上游对应的开关名
```

必须在 `notes.md` 写明：偏离了上游默认形态、依据是什么（本平台无 KDED）、验证方式是什么。若该开关使能后又要求 `KF6::DBusAddons` 链，说明上游没有真正的无会话路径 → 退回策略 E。

## 策略 C：裁剪只服务于桌面会话的 target

示例程序、桌面端工具、KDED 相关测试在 OHOS 上无意义，直接关闭：

```python
tc.variables["BUILD_EXAMPLES"] = "OFF"
tc.variables["BUILD_TESTING"] = "OFF"          # 上游测试需要会话总线时
```

注意 R51：关闭上游测试必须在 `notes.md` 与 `test_package/MANIFEST.yml` 说明**具体技术原因**与替代覆盖（消费者用例）。

## 策略 D：运行期降级（SOFT 命中）

`SOFT` 命中不阻塞交付：OHOS 无会话总线 → 通知/服务注册静默失败。保持上游代码不动，在 `notes.md` 记「功能降级清单」，不要为了"看起来干净"去删通知代码或写空壳 stub（R8 禁止空壳，且会让上游行为偏离）。

## 策略 E：不可交付的判定

若一个库的产品**只有** KDED 插件形态（无独立程序、无可裁剪 target），在 OHOS 上没有任何加载路径 → 按 `result --status env_unsupported` 上报，`--failed-reason` 写明「产物为 KDED 插件，OHOS 无 KDED 装载路径」，不要编出永不加载的 `.so` 充数。

## 反模式清单（一律禁止）

1. **伪造 `kdbusaddons` 包**顶替依赖（R34/R36：依赖必须真实发布，假包=无效依赖）。
2. **`#ifdef __OHOS__` 包住 `find_package(KF6DBusAddons REQUIRED)`**：平台宏补丁（R8），且只掩盖配置错误、不改变产物形态。
3. **把插件装到 `plugins/kf6/kded/` 就交差**：OHOS 无 KDED，该目录永远不会被扫描。
4. **为了让仓库里多一个包而手动打包/改 `.ci-result.json`**：门禁口径禁止（R20/R29）。
5. **只验证"编译通过"不看形态**：本主题的失败模式恰恰是「编译通过但产物永远不生效」——消费者用例必须实跑产物。

## 与检测脚本的对应关系

| 脚本规则 | 默认策略 |
|---|---|
| `cmake:KF6DBusAddons` / `cmake:KF6_COMPONENTS_DBus` / `cmake:DBusAddons_target` | A → B → E（按上游是否有联动/降级路径） |
| `cmake:kded_plugin` / `code:KDEDModule` / `code:KPluginFactory_kded` / `cmake:plugin_install_dir` | A → B → E |
| `code:session_bus` / `code:dbus_call` / `code:notifications` / `code:kdedsrv` / `env:session_bus_addr` | D（确认降级路径后放行） |
