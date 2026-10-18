/* graceful_cleanup_demo.c — 「运行期服务缺失 → 清理路径崩溃」最小可复现样例.
 *
 * 形态完全对标真实宿主程序（jalv 1.10.0 实测）：
 *   - 处理链的句柄 instance 是**惰性初始化**的：只有连上运行期服务之后才创建
 *   - 清理函数 process_deactivate() 里有一个「遍历端口 → 对 instance 操作」的循环
 *   - 服务缺失时 instance 仍为 NULL，循环无条件解引用 → SIGSEGV
 *
 * 编译两种形态（同一份源码，只差一个守卫）：
 *   无守卫（复现原始缺陷）：-DGUARD=0  → 运行即崩溃（SIGSEGV / rc=139）
 *   加守卫（本 SKILL 策略） ：-DGUARD=1  → 优雅失败，退出码 1
 *
 * 依赖：只用 libc，不依赖任何三方库，便于在任意 OHOS PC 工具链上复现。
 */
#include <stdio.h>
#include <stdlib.h>

typedef struct {
  int dummy;
} Instance;

typedef struct {
  Instance* instance; /* 惰性初始化：服务连上之前恒为 NULL */
  unsigned  num_ports;
  void**    ports;
} Process;

/* 模拟运行期服务（音频服务器 / 显示服务 / DBus）不存在 */
static int
service_connect(void)
{
  fprintf(stderr, "Cannot connect to server: No such file or directory\n");
  fprintf(stderr, "error: Failed to connect to audio system\n");
  return -1;
}

/* 上游清理函数：崩在「循环里无守卫地解引用惰性句柄」 */
static void
process_deactivate(Process* const proc)
{
  for (unsigned i = 0; i < proc->num_ports; ++i) {
    free(proc->ports[i]);
    proc->ports[i] = NULL;
#if GUARD
    if (proc->instance) {
      proc->instance->dummy = (int)i; /* 真实项目里是 connect_port(instance, ...) */
    }
#else
    proc->instance->dummy = (int)i; /* ← instance 为 NULL 时 SEGV */
#endif
  }
}

int
main(void)
{
  Process proc = {NULL, 4U, NULL};

  /* 端口结构先建立（后端连接之前就会建好，所以 num_ports > 0） */
  proc.ports = calloc(proc.num_ports, sizeof(void*));
  if (!proc.ports) {
    return 2;
  }

  /* 服务缺失 → 句柄保持 NULL，走失败清理路径 */
  if (service_connect()) {
    fprintf(stderr, "graceful: releasing partial state\n");
    process_deactivate(&proc);
    free(proc.ports);
    fprintf(stderr, "graceful: exit 1 (no crash)\n");
    return 1;
  }

  free(proc.ports);
  return 0;
}
