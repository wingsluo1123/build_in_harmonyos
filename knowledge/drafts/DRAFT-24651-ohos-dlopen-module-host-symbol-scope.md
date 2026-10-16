# DRAFT-24651: OHOS 上 dlopen 插件的符号作用域 —— 宿主已加载库不参与模块重定位

- 条目主题：HarmonyOS PC 上 `dlopen(3)` 得到的插件/模块，**只在自己的 `DT_NEEDED` 依赖闭包里**
  解析未定义符号；宿主进程已经加载的库（以及"再 `dlopen(RTLD_GLOBAL)` 的库"）都不在其符号
  查找作用域内。因此"宿主提供符号、插件不链接宿主库"这一 Linux 常态实现在 OHOS 上直接失效。
- 状态：草稿（待知识库主编审核，拟提升为 Exxx）
- 关联软件：poldi 0.4.2-git20201120.5d67235（PAM 模块）；同类：pam_u2f 等 PAM 模块、
  GIO/GVfs/GTK 模块、NSS 模块、libtool `-module` 目标
- 关联条目：E345 / E442（host-loaded plugin 的打包与验证范式）、E489（CTest 前签名构建树
  ELF 闭包）、E013 / E004 / E078（-ldl、NEEDED、LDSHARED 链接细节）——**均不覆盖本条的作用域语义**

## 错误特征

```
Error relocating /…/lib/security/pam_poldi.so: pam_get_item: symbol not found
dlopen failed: Error relocating /…/plugin.so: foo_func: symbol not found
pam_authenticate … rc=28 (Module is unknown)      # PAM 栈侧表现
```

## 根因

Linux/glibc（以及多数 musl 发行版）上，插件用未定义符号、由宿主进程提供是**设计常态**：
PAM 模块故意不链接 libpam（符号由 PAM 栈解析）、GIO/NSS 模块同理，libtool 的 `-module`
目标也允许未定义符号。OHOS 的加载器不这样工作：重定位 `dlopen` 对象时只搜索该对象自身的
`DT_NEEDED` 闭包（加启动期预加载对象），宿主已加载库不在其中，于是 `dlopen` 立即失败。
对 PAM 而言失败被翻译为 `PAM_MODULE_UNKNOWN(28)`，模块完全不可用。

## 实测证据（三类对照，同一插件）

```bash
clang -shared -fPIC -o libhost.so.1 foo.c -Wl,-soname,libhost.so.1   # 提供 foo_func
clang -shared -fPIC -o use.so use.c                                  # 只声明 extern int foo_func(void);
clang -o m m.c -L. -lhost -Wl,-rpath,$PWD                            # m 调用 foo_func 且 dlopen(use.so)

./m ./use.so                                # ✗ Error relocating …: foo_func: symbol not found
# 宿主已 DT_NEEDED libhost 且调用了它的 foo_func（证明库确实已加载）——仍然解析失败

# 对提供者再 dlopen(RTLD_GLOBAL) 后再 dlopen 插件 → ✗ 仍失败
LD_PRELOAD=$PWD/libhost.so.1 ./m ./use.so   # ✓ dlopen OK
```

真实案例（poldi）：

```
模块未链接 libpam：pam_authenticate → rc=28 (Module is unknown)   ← libpam dlopen 模块失败
模块链接   libpam：pam_authenticate → rc=7  (Authentication failure) ← 入口真实执行
```

## 推荐修复

让插件**自带** `DT_NEEDED` 指向其符号提供者（最小改动：链接规则追加 `-l<provider>`）：

```python
# autotools 例（PAM 模块）
#   $(CC) $(LDFLAGS) -shared -o pam_poldi.so … $(LIBGCRYPT_LIBS) $(KSBA_LIBS) -lpam
# 验证
readelf -d <module> | grep NEEDED        # 期望出现 libpam.so.0
```

宿主已提供符号的平台上，多出的这个依赖是无害的 no-op（加载器对同 soname 只保留一份映射）。
在 OHOS 上，这恰好使模块第一次变得可用。

## 回退（仅过渡，不作为交付形态）

`LD_PRELOAD=<provider.so>` 在宿主启动前预加载提供者，可让未改动的插件工作（实测有效）；
但交付产物本身仍是坏的——真实宿主不会替我们预加载，故只用于临时验证。

## 明确禁止

- 用桩库/自实现 `pam_get_item` 之类顶替宿主符号（掩盖加载契约，包在真实宿主里仍失败）；
- 指望"先 `dlopen(RTLD_GLOBAL)` 提供者再 `dlopen` 插件"（OHOS 实测无效，属无效绕行）。

## 验证

poldi：补丁 0001 给 `pam_poldi.so` 加 `-lpam` 后，`conan create` 的 test_package 用真实
libpam 宿主跑通两个用例（控制例指向不存在模块 → `rc=28`；正例指向打包模块 → `rc=7`，
模块被加载且入口执行），`conan create` rc=0。
