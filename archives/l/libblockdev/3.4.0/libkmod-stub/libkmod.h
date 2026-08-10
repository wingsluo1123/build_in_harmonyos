/*
 * libkmod stub for HarmonyOS - provides no-op implementations
 * of the kmod API functions needed by libblockdev.
 * All functions return NULL or -2 (error) as appropriate.
 */
#ifndef LIBKMOD_H
#define LIBKMOD_H

#include <stddef.h>
#include <stdarg.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Opaque types */
struct kmod_ctx;
struct kmod_module;
struct kmod_list;

/* Log function type */
enum {
	KMOD_LOG_ERR = 3,
	KMOD_LOG_WARNING = 4,
	KMOD_LOG_INFO = 6,
	KMOD_LOG_DEBUG = 7,
};

/* Module initstate */
enum kmod_module_initstate {
	KMOD_MODULE_BUILTIN = 0,
	KMOD_MODULE_LIVE,
	KMOD_MODULE_COMING,
	KMOD_MODULE_GOING,
};

/* Flags */
#define KMOD_MODULE_INSERT_FORCE_VERMAGIC (1 << 0)
#define KMOD_MODULE_INSERT_FORCE_MODVERSION (1 << 1)
#define KMOD_MODULE_REMOVE_FORCE (1 << 0)
#define KMOD_MODULE_REMOVE_NOWAIT (1 << 1)
#define KMOD_PROBE_FAIL_ON_LOADED (1 << 2)

/* Context functions */
struct kmod_ctx *kmod_new(const char *dirname, const char * const *config_paths);
struct kmod_ctx *kmod_ref(struct kmod_ctx *ctx);
struct kmod_ctx *kmod_unref(struct kmod_ctx *ctx);
void kmod_set_log_priority(struct kmod_ctx *ctx, int priority);
typedef void (*kmod_log_fn)(struct kmod_ctx *ctx, int priority, const char *file, int line, const char *fn, const char *format, va_list args);
void kmod_set_log_fn(struct kmod_ctx *ctx, void (*log_fn)(), void *log_data);

/* Module functions */
int kmod_module_new_from_lookup(struct kmod_ctx *ctx, const char *name, struct kmod_list **list);
int kmod_module_new_from_name(struct kmod_ctx *ctx, const char *name, struct kmod_module **mod);
int kmod_module_new_from_loaded(struct kmod_ctx *ctx, struct kmod_list **list);
struct kmod_list *kmod_list_next(struct kmod_list *list, struct kmod_list *curr);
struct kmod_module *kmod_module_get_module(struct kmod_list *list);
const char *kmod_module_get_name(struct kmod_module *mod);
const char *kmod_module_get_path(struct kmod_module *mod);
int kmod_module_get_initstate(struct kmod_module *mod);
const char *kmod_module_get_initstate_str(struct kmod_module *mod);
int kmod_module_probe_insert_module(struct kmod_module *mod, unsigned int flags, const char *extra_options, int (*run_install)(struct kmod_module *m, const char *cmdline, void *data), void *data, const void *print_action);
int kmod_module_remove_module(struct kmod_module *mod, unsigned int flags);
struct kmod_module *kmod_module_unref(struct kmod_module *mod);
int kmod_module_unref_list(struct kmod_list *list);

#ifdef __cplusplus
}
#endif

#endif /* LIBKMOD_H */
