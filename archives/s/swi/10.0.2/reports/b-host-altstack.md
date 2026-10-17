# 备用信号栈初始化/借用对照

本报告补充E224，不声称sigaltstack家族零命中或已获得路径B分值。
已有控制的初始化函数与官方源相同，本次同线程路径已实现E224的注销后释放；
不表示该历史版本全部跨线程engine路径均完整满足E224。两种runtime真实加载路径由dladdr记录并核对。

## 直接嵌入，显式 PL_cleanup(0)

```text
CASE=E224-cleanup-only RC=1
RUNTIME_LIBRARY=/storage/Users/currentUser/work/frj__/swi-validation-cache/p/b/swid110b35116d66/b/build/Release/src/libswipl.so.10
INITIAL_STACK_FLAGS=0 SIZE=28672 POINTER=0x5aac820000
HOST_STACK_AT_INIT=overwritten
REAL_PROLOG_CALL=1
HOST_STACK_AFTER_CLEANUP=lost
HOST_STACK_TEST=failed

CASE=current-installed RC=0
RUNTIME_LIBRARY=/storage/Users/currentUser/work/frj__/swi-validation-cache/p/b/swi859ae7fc5da00/p/lib/swipl/lib/aarch64-ohos/libswipl.so.10
INITIAL_STACK_FLAGS=0 SIZE=28672 POINTER=0x59746a9000
HOST_STACK_AT_INIT=preserved
REAL_PROLOG_CALL=1
HOST_STACK_AFTER_CLEANUP=preserved
HOST_STACK_TEST=passed

HOST_STACK_DIFFERENTIAL_CONFIRMED
```

## 未改官方 calc.c/calc.pl，PL_halt 路径

```text
CASE=E224-cleanup-only RC=1
RUNTIME_LIBRARY=/storage/Users/currentUser/work/frj__/swi-validation-cache/p/b/swid110b35116d66/b/build/Release/src/libswipl.so.10
42
UPSTREAM_CALC_HOST_STACK_INIT=overwritten
UPSTREAM_CALC_HOST_STACK_AFTER_PL_HALT=lost
Welcome to SWI-Prolog (threaded, 64 bits, version 10.0.2)
SWI-Prolog comes with ABSOLUTELY NO WARRANTY. This is free software.
Please run ?- license. for legal details.

For online help and background, visit https://www.swi-prolog.org


CASE=current-installed RC=0
RUNTIME_LIBRARY=/storage/Users/currentUser/work/frj__/swi-validation-cache/p/b/swi859ae7fc5da00/p/lib/swipl/lib/aarch64-ohos/libswipl.so.10
42
UPSTREAM_CALC_HOST_STACK_INIT=preserved
UPSTREAM_CALC_HOST_STACK_AFTER_PL_HALT=preserved
Welcome to SWI-Prolog (threaded, 64 bits, version 10.0.2)
SWI-Prolog comes with ABSOLUTELY NO WARRANTY. This is free software.
Please run ?- license. for legal details.

For online help and background, visit https://www.swi-prolog.org


OFFICIAL_SOURCE_SHA256={"calc.c": "76a92586a9fc42fbf7c0dfa9fe2d877a16842707aa3b88e1bb13e8d1fe8e9db7", "calc.pl": "3ab6ca86af49bea19ccee7ff7aa2782f00ce3cf9e701ba0dea5988472ebea6ee"}
OFFICIAL_EMBEDDING_DIFFERENTIAL_CONFIRMED
```

PL_halt的Release策略不等同PL_cleanup(0)，因此标签明确分开。
两个版本均输出42，RC1来自新增的宿主注册三元组断言，不是原上游用例失败。

## 控制构建的源码与指纹

Release控制libswipl SHA256 `3a44257b781120f17d18d8e1e03dd5393c4418b6c7f9acdacf15065a5066283e`。
控制pl-setup.c SHA256 `3bc8d1e615edcea2b4cd72f1aa4018648aae764d101be5fb3e579dcf3221f422`。
当前安装libswipl SHA256 `157cefa569e4a307343c17ce24456fe3b54dbbd5d8f6e3caf79a7cbc2ad58b96`。
活动配置：`CMAKE_BUILD_TYPE:STRING=Release ; CMAKE_CXX_FLAGS:STRING=-stdlib=libc++ ; CMAKE_CXX_FLAGS_RELEASE:STRING='-O2 ' ; CMAKE_C_FLAGS:STRING= ; CMAKE_C_FLAGS_RELEASE:STRING=-O3 -DNDEBUG`。

原版初始化函数（已与官方发布源核对相同）：

```c
bool
initGuardCStack(void)
{
#ifdef O_C_STACK_GUARDED
  GET_LD
  stack_t ss = {0};

  if ( (LD->signal.alt_stack = malloc(SIGSTKSZ)) )
  { ss.ss_sp = LD->signal.alt_stack;
    ss.ss_size = SIGSTKSZ;
    ss.ss_flags = 0;

    if ( sigaltstack(&ss, NULL) == 0)
    { DEBUG(MSG_SIGNAL, Sdprintf("Setup altstack (%zd bytes)\n", SIGSTKSZ));

      if ( LD == &PL_local_data )	/* main thread, only need this once */
      { struct sigaction sa = {0};

	sa.sa_flags = SA_ONSTACK;
	sa.sa_handler = alt_segv_handler;
	sigemptyset(&sa.sa_mask);

	if ( sigaction(SIGSEGV, &sa, NULL) == 0 )
	{ DEBUG(MSG_SIGNAL, Sdprintf("Setup SEGV on altstack\n"));
	  return true;
	}
      }
    }
  }
#endif

  return false;
}
```

控制已具备的E224回收修复：

```c
#ifdef O_C_STACK_GUARDED
  if ( ld->signal.alt_stack )
  { stack_t current;

    /* The owner must unregister an alternate stack before freeing its
       backing memory.  Retain it if querying or disabling fails, including
       cleanup invoked while executing on the alternate stack itself. */
    if ( sigaltstack(NULL, &current) == 0 )
    { bool release = (current.ss_flags & SS_DISABLE) ||
                     current.ss_sp != ld->signal.alt_stack;
      if ( !release )
      { stack_t disabled = {0};
        disabled.ss_flags = SS_DISABLE;
        release = sigaltstack(&disabled, NULL) == 0;
      }
      if ( release )
      { free(ld->signal.alt_stack);
        ld->signal.alt_stack = NULL;
      }
    }
  }
#endif
```

## 复现诊断

先将Conan包路径设为SWI_PACKAGE_DIR，将未改官方10.0.2解包目录设为SWI_SOURCE_DIR。
将CC设为当前原生profile的SDK C编译器，启用该依赖图的conanrun环境。

```sh
CC="$HOME/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin/clang"
RECIPE="$PWD/archives/s/swi/10.0.2"
"$CC" "$RECIPE/test_package/diagnostics/host_stack_probe.c" -I"$SWI_PACKAGE_DIR/lib/swipl/include" -L"$SWI_PACKAGE_DIR/lib/swipl/lib/aarch64-ohos" -lswipl -Wl,-rpath,"$SWI_PACKAGE_DIR/lib/swipl/lib/aarch64-ohos" -o host-stack-probe
SWI_HOME_DIR="$SWI_PACKAGE_DIR/lib/swipl" ./host-stack-probe
"$CC" "$SWI_SOURCE_DIR/man/calc.c" "$RECIPE/test_package/diagnostics/calc_host_fixture.c" -I"$SWI_PACKAGE_DIR/lib/swipl/include" -L"$SWI_PACKAGE_DIR/lib/swipl/lib/aarch64-ohos" -lswipl -Wl,--wrap=PL_initialise -Wl,-rpath,"$SWI_PACKAGE_DIR/lib/swipl/lib/aarch64-ohos" -o calc-host-probe
SWI_CALC_SOURCE="$SWI_SOURCE_DIR/man/calc.pl" SWI_HOME_DIR="$SWI_PACKAGE_DIR/lib/swipl" ./calc-host-probe '6*7'
```

负例需另建保持上述原始初始化函数、仅改为所列E224回收块的任务私有控制版本，
以LD_LIBRARY_PATH选择其libswipl、SWI_HOME_DIR选择其home，再运行相同探针。
本次历史控制版本的实际来源、源码和库哈希已记录；没有改写共享依赖缓存。

## 知识查重与边界

全量正文查询命令：遍历knowledge/graph/*.kv、knowledge/doc/*.md、knowledge/drafts正文，
按`sigaltstack|alternate.*stack|备用.*信号栈|ss_sp|SS_DISABLE`逐行匹配。
正式条目命中E224及doc镜像；其余为无关匹配/引用。E224是相关原理，不能声称全家族0命中。

```sh
rg --hidden --no-ignore -n -i 'sigaltstack|alternate.{0,25}stack|备用.{0,12}信号栈|signal.{0,12}stack|ss_sp|SS_DISABLE' knowledge/graph knowledge/doc knowledge/drafts -g '*.kv' -g '*.md'
```

本候选的区别在初始化已启用资源的借用/所有权，而不是重复注销/free顺序。
未检查真实信号投递或宿主SIGSEGV handler；不声明完整信号互操作已验证。

## 增量消费者结果

生产配方/补丁未变；仅强化原embedding用例，30/30再次通过，CONAN_TEST_RC=0。
日志SHA256 `7653fc45ee57a7b8fae635e05e4a29ae14b60207eeeb0d62c5c851bb9120c6c1`；原始上游84/84组结果沿用此前同一运行时的完整create证据。
