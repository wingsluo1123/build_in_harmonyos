/* fixtures/process_deactivate_unguarded.c
 *
 * 上游未修补形态的忠实摘录（jalv 1.10.0 src/process_setup.c，插补丁前）。
 * 专供检测脚本 L1 源码通道自校验用：真实上游源码里只有一条分支，
 * 而 samples/graceful_cleanup_demo.c 用 #if GUARD 同时携带两种形态，
 * 会让「清理函数里是否已有守卫」这一判定失真。
 *
 * 期望：detect_absent_service_crash.py scan --src samples/fixtures
 *       → ABSENT_SERVICE_CLEANUP_CANDIDATE=yes
 */
#include <stdint.h>
#include <stdlib.h>

typedef struct { void* evbuf; } JalvPort;
typedef struct {
  void*       instance;
  uint32_t    num_ports;
  JalvPort*   ports;
} JalvProcess;

typedef struct { JalvProcess process; } Jalv;

extern void lv2_evbuf_free(void* evbuf);
extern void lilv_instance_connect_port(void* instance, uint32_t port, void* data);
extern void lilv_instance_free(void* instance);

static void
jalv_process_deactivate(Jalv* jalv)
{
  JalvProcess* const proc = &jalv->process;

  for (uint32_t i = 0U; i < proc->num_ports; ++i) {
    lv2_evbuf_free(proc->ports[i].evbuf);
    lilv_instance_connect_port(proc->instance, i, NULL);
    proc->ports[i].evbuf = NULL;
  }

  lilv_instance_free(proc->instance);
  proc->instance = NULL;
}
