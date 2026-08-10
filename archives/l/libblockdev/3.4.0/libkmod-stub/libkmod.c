/*
 * libkmod stub implementation for HarmonyOS
 * All functions return NULL or -2 (error) - no kernel module support on OHOS
 */
#include <stdlib.h>
#include <string.h>
#include "libkmod.h"

/* Context functions */
struct kmod_ctx *kmod_new(const char *dirname, const char * const *config_paths) {
    (void)dirname; (void)config_paths;
    return NULL;
}

struct kmod_ctx *kmod_ref(struct kmod_ctx *ctx) {
    (void)ctx;
    return NULL;
}

struct kmod_ctx *kmod_unref(struct kmod_ctx *ctx) {
    (void)ctx;
    return NULL;
}

void kmod_set_log_priority(struct kmod_ctx *ctx, int priority) {
    (void)ctx; (void)priority;
}

void kmod_set_log_fn(struct kmod_ctx *ctx, void (*log_fn)(), void *log_data) {
    (void)ctx; (void)log_fn; (void)log_data;
}

/* Module functions */
int kmod_module_new_from_lookup(struct kmod_ctx *ctx, const char *name, struct kmod_list **list) {
    (void)ctx; (void)name;
    if (list) *list = NULL;
    return -2;
}

int kmod_module_new_from_name(struct kmod_ctx *ctx, const char *name, struct kmod_module **mod) {
    (void)ctx; (void)name;
    if (mod) *mod = NULL;
    return -2;
}

int kmod_module_new_from_loaded(struct kmod_ctx *ctx, struct kmod_list **list) {
    (void)ctx;
    if (list) *list = NULL;
    return -2;
}

struct kmod_list *kmod_list_next(struct kmod_list *list, struct kmod_list *curr) {
    (void)list; (void)curr;
    return NULL;
}

struct kmod_module *kmod_module_get_module(struct kmod_list *list) {
    (void)list;
    return NULL;
}

const char *kmod_module_get_name(struct kmod_module *mod) {
    (void)mod;
    return NULL;
}

const char *kmod_module_get_path(struct kmod_module *mod) {
    (void)mod;
    return NULL;
}

int kmod_module_get_initstate(struct kmod_module *mod) {
    (void)mod;
    return -2;
}

const char *kmod_module_get_initstate_str(struct kmod_module *mod) {
    (void)mod;
    return NULL;
}

int kmod_module_probe_insert_module(struct kmod_module *mod, unsigned int flags, const char *extra_options, int (*run_install)(struct kmod_module *m, const char *cmdline, void *data), void *data, const void *print_action) {
    (void)mod; (void)flags; (void)extra_options; (void)run_install; (void)data; (void)print_action;
    return -2;
}

int kmod_module_remove_module(struct kmod_module *mod, unsigned int flags) {
    (void)mod; (void)flags;
    return -2;
}

struct kmod_module *kmod_module_unref(struct kmod_module *mod) {
    (void)mod;
    return NULL;
}

int kmod_module_unref_list(struct kmod_list *list) {
    (void)list;
    return 0;
}
