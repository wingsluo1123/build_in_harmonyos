# DRAFT-ohos-dlopen-rtld-global-reloc-invisible: OHOS 动态链接器对 dlopen(RTLD_GLOBAL) 模块的符号不做跨模块重定位解析

- **来源**：lib32 2.6.2（GNU libtool 2.6.2 / libltdl）适配（2026-10-06）
- **关联 run**：runs-v2/lib32-2.6.2（候选 notes.md §5b 组 118 实测记录）
- **申报域**：八分类之**链接**（次相关：musl/libc 差异）；机理分层 **L1**（平台/动态链接器语义差异，单库发现即可申报）
- **阻塞面**：链接失败/运行失败（上游 testsuite 组 118 真实失败日志 + 自包含探针阳性实证）
- **原则挂钩**：P-RUNTIME-002

## 问题（一句规则）

OHOS musl 动态链接器上，`dlopen(A, RTLD_GLOBAL)` 的符号**不参与**后续
`dlopen(B)` 的重定位解析（B 引用 A 的符号必然失败），但同一进程
`dlsym(RTLD_DEFAULT, "A 的符号")` 却能命中——注册与解析语义割裂。
跨 dlopen 模块的符号依赖必须改用**构建期 DT_NEEDED** 或**启动期 LD_PRELOAD**。

## 证据（真实失败 + 自包含探针）

1. 上游真实失败：GNU libtool 2.6.2 testsuite 组 118（lt_dladvise.at:26，设备实测
   两轮均 FAIL）：

   ```
   can't open the module libdepend!
   error was: file not found
   ```

   （testsuite.dir/118 独立重跑可稳定复现；libglobal 以 global advise 加载成功、
   仅 libdepend——引用 libglobal 的 f/i、构建期保留未定义符号——失败。）

2. 系统级 dlfcn 探针（原始 dlerror 对照，`probe-run1.log`）：

   ```
   P1a dlopen(./liba.so, NOW|GLOBAL)      = OK
   P1b dlopen(./libb.so, NOW|LOCAL)       = FAIL  dlerror: Error relocating ./libb.so: a_f: symbol not found
   P2  dlopen(./libb.so, LAZY|LOCAL)      = FAIL  dlerror: Error relocating ./libb.so: a_f: symbol not found
   P3  dlopen(./libb.so, NOW|GLOBAL)      = FAIL  dlerror: Error relocating ./libb.so: a_f: symbol not found
   P4  dlopen(./libb_needed.so, NOW|LOCAL)= OK    （构建期 DT_NEEDED 绕行）
   P5a/b dlopen(不存在文件)                = FAIL  dlerror: Error loading shared library ...: No such file or directory
   P6  dlsym(RTLD_DEFAULT, a_f)           = OK
   ```

3. LD_PRELOAD 环境级绕行（`probe2-run1.log`）：baseline FAIL →
   `LD_PRELOAD=./liba.so` 后 OK。

### 机理链（闭环）

1. libtool 组 118：libdepend.so 引用 libglobal 的 f/i 且允许未定义符号；
2. ltdl 先以 RTLD_GLOBAL 成功加载 libglobal（`global: 4` 正常输出）；
3. ltdl 加载 libdepend → `dlopen` 重定位阶段在平台链接器的重定位搜索域中
   找不到 f（尽管 libglobal 已 GLOBAL 注册）→ 系统原始报错
   `Error relocating ./libdepend.so: f: symbol not found`（探针 P1 同文）；
4. libltdl `tryall_dlopen` 穷尽候选后用自己的通用错误码 FILE_NOT_FOUND
   **覆盖**底层 dlerror → 测试只见误导性的 `file not found`（探针 P5 证明原生
   缺失文件报错文本不同源，可判定为 ltdl 合成错误）；
5. `can't open the module libdepend!` → main 返回 1 → 组 118 FAILED。

RTLD_LAZY 无效（P2）：平台默认 BIND_NOW（E078 已收录事实），加载期即全量重定位；
B 侧 RTLD_GLOBAL 也无效（P3）：问题在重定位搜索域，不在加载标志。

### 诚实边界

- 本机无 glibc/上游 musl 对照环境，"上游 musl 支持 RTLD_GLOBAL 后续解析"依据
  musl dynlink 文档语义推断（阴性对照未测，OHOS 单机阳性已闭环）。

## 解法（方案空间）

| 优先级 | 方案 | 实证 | 权衡 |
| --- | --- | --- | --- |
| rec（构建期） | 依赖方 .so 链接期显式挂被依赖库（`-lA`，DT_NEEDED）；libtool 模块间 `-la` 互链或合并单 .so / dlpreopen | 探针 P4 = OK | 保守可移植，glibc 上无副作用；上游按"运行期 GLOBAL 解析"建模时按 R51 如实记录平台性失败 |
| fallback（环境级） | `LD_PRELOAD=<被依赖库>.so` 启动期预载 | probe2 = OK | 仅限可控启动环境（自启进程/测试 harness/test_package）；宿主进程不受控时不可用，属掩盖依赖而非建立链接 |
| **禁止** | 运行期靠 RTLD_GLOBAL 预加载解决跨 dlopen 模块符号解析（glibc 惯例正确写法，本平台确定性反模式；ltdl 下报错被合成为 file not found，误导排查方向） | 探针 P1 = FAIL | 运行期插件加载必失败 |
| **禁止** | 注释/删除上游该类测试组、跳过整个 testsuite、改测试 oracle | — | 态度审计第 2 条：平台限制逐条如实记录（R51），不污染上游判定 |

## 适用范围

任何在 OHOS 上使用 `dlopen(RTLD_GLOBAL)` 预载依赖、再 `dlopen` 加载依赖方模块的
插件/模块系统：libltdl（`lt_dlopenadvise` global）、自研 dlfcn 插件框架、脚本语言
运行时互载 C 扩展、基于 RTLD_GLOBAL 的符号共享方案。

## 去重证据（确认 knowledge/graph 未覆盖）

检索（worktree 根，2026-10-06）：

- `grep -il "rtld_global" knowledge/graph/*.kv` → 仅 **E286**（enzyme/LLVM SDK
  组件缺失条目，其 rec 提到用 RTLD_GLOBAL 预载 libLLVM-15.so 的 test_package
  技巧，但未把"RTLD_GLOBAL 不参与后续 dlopen 重定位"作为机理收录，与本条
  结论方向相反，恰为本条 forbid_1 的反模式案例）。
- `grep -il "relocating" knowledge/graph/*.kv` → E078（musl BIND_NOW + 解释器
  扩展缺主库 NEEDED）、E142（gettext 缺 g_libintl_dgettext）、E176（icudata
  stubdata）、E274/E316（SONAME 实体缺失）、E509（OpenSSL 版本符号）——全部是
  "特定库缺符号/缺制品/缺 NEEDED"事件类，无一条收录"RTLD_GLOBAL 跨模块
  重定位不可见 + dlsym 可见性割裂"的平台语义类。
- 检索词：`rtld_global / relocating / dlopen / symbol not found / DT_NEEDED /
  LD_PRELOAD / libltdl`；范围：`knowledge/graph/`、`knowledge/drafts/`。

本条新增价值：平台动态链接器语义层（L1）+ dlsym/重定位割裂判据 + ltdl 错误码
掩盖链 + 两种实证绕行，跨库可复用（所有插件式加载系统命中同一阻塞面）。

## 附录 A：自包含验证探针

```sh
mkdir -p rtld-probe && cd rtld-probe   # 放入 a.c b.c probe.c probe2.c（本机镜像 runs-v2/lib32-2.6.2/builder/probe/）
CC=/data/service/hnp/bin/clang
$CC -fPIC -shared -o liba.so a.c
$CC -fPIC -shared -o libb.so b.c                       # b.c 引用 a_f/a_i，不带 -la
$CC -fPIC -shared -o libb_needed.so b.c -L. -la -Wl,-rpath,.
$CC -o probe probe.c -ldl && $CC -o probe2 probe2.c -ldl
./probe                          # 阳性判据：P1b FAIL(symbol not found) 且 P6 dlsym OK
LD_PRELOAD=./liba.so ./probe2    # 绕行判据：baseline FAIL → 预载后 OK
```

a.c：`int a_f(int x){ return x-1; } int a_i = 5;`
b.c：`extern int a_f(int); extern int a_i; int b_g(int x){ return a_f(a_i)+x-3; } int b_j = 4;`

probe.c（全文）：

```c
#include <dlfcn.h>
#include <stdio.h>

static void rep(const char *tag, void *h) {
    const char *e = dlerror();
    printf("%-46s = %-8s", tag, h ? "OK" : "FAIL");
    if (e) printf("  dlerror: %s", e);
    printf("\n");
}

int main(void) {
    void *hA, *h;
    int (*g)(int);

    printf("== P1 组118场景: dlopen(A,GLOBAL|NOW) 再 dlopen(B,NOW|LOCAL) ==\n");
    dlerror();
    hA = dlopen("./liba.so", RTLD_NOW | RTLD_GLOBAL);
    rep("P1a dlopen(./liba.so, NOW|GLOBAL)", hA);
    if (!hA) return 1;
    dlerror();
    h = dlopen("./libb.so", RTLD_NOW | RTLD_LOCAL);
    rep("P1b dlopen(./libb.so, NOW|LOCAL)", h);

    printf("== P2 lazy 变体 ==\n");
    dlerror();
    h = dlopen("./libb.so", RTLD_LAZY | RTLD_LOCAL);
    rep("P2  dlopen(./libb.so, LAZY|LOCAL)", h);
    if (h) {
        g = (int (*)(int)) dlsym(h, "b_g");
        printf("P2b dlsym(b_g) = %p", (void *)g);
        if (g) { fflush(stdout); printf("  call g(4) -> %d\n", g(4)); }
        else printf("\n");
    }

    printf("== P3 global 变体 ==\n");
    dlerror();
    h = dlopen("./libb.so", RTLD_NOW | RTLD_GLOBAL);
    rep("P3  dlopen(./libb.so, NOW|GLOBAL)", h);

    printf("== P4 DT_NEEDED 绕行（libb_needed 链接期挂 liba.so） ==\n");
    dlerror();
    h = dlopen("./libb_needed.so", RTLD_NOW | RTLD_LOCAL);
    rep("P4  dlopen(./libb_needed.so, NOW|LOCAL)", h);

    printf("== P5 dlerror 文本对照 ==\n");
    dlerror();
    h = dlopen("./libnosuchfile.so", RTLD_NOW);
    rep("P5a dlopen(./libnosuchfile.so)", h);
    dlerror();
    h = dlopen("libnosuchfile.so", RTLD_NOW);
    rep("P5b dlopen(libnosuchfile.so)", h);

    printf("== P6 全局符号表可见性 ==\n");
    dlerror();
    h = dlsym(RTLD_DEFAULT, "a_f");
    rep("P6  dlsym(RTLD_DEFAULT, a_f)", h);

    return 0;
}
```

probe2.c（全文）：

```c
#include <dlfcn.h>
#include <stdio.h>

int main(void) {
    void *h;
    dlerror();
    h = dlopen("./libb.so", RTLD_NOW | RTLD_LOCAL);
    printf("dlopen(./libb.so, NOW|LOCAL) = %s", h ? "OK" : "FAIL");
    const char *e = dlerror();
    if (e) printf("  dlerror: %s", e);
    printf("\n");
    return h ? 0 : 1;
}
```
