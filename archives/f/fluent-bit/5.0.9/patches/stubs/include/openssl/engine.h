#ifndef OPENSSL_ENGINE_H_STUB
#define OPENSSL_ENGINE_H_STUB
#include <stddef.h>
/* HarmonyOS stub: FLB_TLS=Off - ENGINE type defined by fluent-bit itself */
#define ENGINE_METHOD_ALL 0xffff
static inline void *ENGINE_by_id(const char *id) { (void)id; return NULL; }
static inline int ENGINE_init(void *e) { (void)e; return 0; }
static inline int ENGINE_set_default(void *e, unsigned int f) { (void)e;(void)f; return 0; }
static inline void ENGINE_free(void *e) { (void)e; }
static inline void ENGINE_cleanup(void) {}
static inline void ENGINE_load_builtin_engines(void) {}
static inline void ENGINE_register_all_complete(void) {}
#endif
