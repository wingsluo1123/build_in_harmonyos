/*
 * kamailio 模块导出表结构镜像（ABI 消费端）
 *
 * 逐字段对齐上游 kamailio 6.0.6 src/core/sr_module.h：
 *   - module_exports_t_m  ← struct module_exports   (sr_module.h:288)
 *   - cmd_export_t_m      ← struct cmd_export       (sr_module.h:206)
 *   - param_export_t_m    ← struct param_export     (sr_module.h:234)
 * 函数指针类型统一以 void * 等价替代（同宽同对齐），字段顺序/宽度与上游一致，
 * 故 sizeof 与上游相同：module_exports=80、cmd_export=48、param_export=24。
 * 80 字节已用 `llvm-readelf --dyn-symbols xhttp_prom.so` 实测 exports 符号
 * （OBJECT GLOBAL, size 80）交叉校验；消费者用例启动时再做一次 sizeof 自校验。
 */
#ifndef KAMAILIO_EXPORTS_MIRROR_H
#define KAMAILIO_EXPORTS_MIRROR_H

/* struct cmd_export (cmd_export_t) */
typedef struct {
	char *name;
	void *function;
	int param_no;
	void *fixup;
	void *free_fixup;
	unsigned int flags;
} cmd_export_t_m;

/* struct param_export (param_export_t) */
typedef struct {
	char *name;
	int type;
	void *param_pointer;
} param_export_t_m;

/* struct module_exports (module_exports_t) */
typedef struct {
	char *name;
	unsigned int dlflags;
	cmd_export_t_m *cmds;
	param_export_t_m *params;
	void *rpc_methods;
	void *pv_items;
	void *response_f;
	void *init_mod_f;
	void *init_child_f;
	void *destroy_mod_f;
} module_exports_t_m;

#endif /* KAMAILIO_EXPORTS_MIRROR_H */
