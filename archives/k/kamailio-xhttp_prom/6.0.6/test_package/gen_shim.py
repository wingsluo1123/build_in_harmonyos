#!/usr/bin/env python3
"""生成 kamailio 核心符号 shim（供消费者用例 dlopen 模块时满足符号重定位）。

背景：xhttp_prom.so 由 kamailio 运行时 loadmodule 加载，其未定义符号中约 34 个
是 kamailio 核心符号（_pkg_root / parse_params / fixup_spve_* 等），由 kamailio
主程序在运行期导出。消费者用例是独立进程，故需自带这些符号的占位定义才能
dlopen 成功（模块以 -Wl,-z,now 构建，全部重定位在加载期完成）。占位符不会被
调用，仅用于满足重定位；唯一例外是 sr_kemi_modules_add，它会被 mod_register()
调用，故生成真实空实现。

符号来源：
  1) 固定清单（PINNED，取自 6.0.6 上游产物 llvm-readelf --dyn-symbols 实测）
  2) 若存在 readelf，再从实际产物补齐 PINNED 之外的未定义符号（跨构建稳健）
libc / 编译器内建符号不生成——由 OHOS libc 提供，正是消费者用例要验证的平台能力。

用法: gen_shim.py <module.so> <out_shim.c>
"""
import shutil
import subprocess
import sys

# kamailio 核心符号（模块运行期由主程序提供）—— kamailio 6.0.6 实测清单
PINNED = [
    "dprint_crit", "get_debug_level", "_ksr_slog_func", "log_level_info",
    "get_debug_facility", "log_stderr", "log_color", "dprint_color", "process_no",
    "my_pid", "log_prefix_val", "dprint_color_reset", "_km_log_func", "pt",
    "up_since", "counter_iterate_grp_names", "counter_iterate_grp_vars",
    "counter_lookup_str", "counter_get_group", "counter_get_name",
    "counter_get_val", "_pkg_root", "_shm_root", "parse_params", "free_params",
    "rpc_register_array", "pkg_mem_size", "fixup_spve_null",
    "fixup_free_spve_null", "fixup_spve_igp", "fixup_free_spve_igp",
    "get_str_fparam", "get_int_fparam", "find_export",
]

# 需以真实函数实现（消费者用例会调用 mod_register，其内部调用此符号）
FUNCS = {
    "sr_kemi_modules_add": "int sr_kemi_modules_add(void *keng) { return 0; }",
}

# 平台（OHOS libc / 编译器内建）提供，不由 shim 生成
PLATFORM = {
    "fprintf", "vsnprintf", "__assert_fail", "gettimeofday", "memset", "strncmp",
    "memcpy", "strlen", "time", "atof", "snprintf", "memcmp", "sched_yield",
    "__cxa_finalize", "stderr", "__register_frame_info", "__deregister_frame_info",
    "__at_fini",
}


_LIBC = None


def resolve_in_libc(name):
    """符号是否由 OHOS libc 提供：True/False，无法判定时 None。"""
    global _LIBC
    if _LIBC is None:
        try:
            import ctypes
            _LIBC = ctypes.CDLL("libc.so")
        except OSError:
            _LIBC = False
    if not _LIBC:
        return None
    return hasattr(_LIBC, name)


def readelf_undefs(module):
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if not readelf:
        print("[warn] 未找到 readelf，仅使用固定清单生成 shim")
        return []
    out = subprocess.run([readelf, "--dyn-symbols", module],
                         capture_output=True, text=True).stdout
    names = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 8 and "UND" in parts[6:7]:
            names.append(parts[7])
    return names


def main():
    if len(sys.argv) < 3:
        print("usage: gen_shim.py <module.so> <out_shim.c>", file=sys.stderr)
        return 2
    module, out_path = sys.argv[1], sys.argv[2]

    # 平台符号必须由 OHOS libc 解析（不被 shim 遮蔽），否则消费者用例会失去
    # "平台符号可解析"的验证意义；故候选符号先查 libc 再决定是否生成占位符。
    candidates = [n for n in readelf_undefs(module)
                  if n and n not in PINNED and n not in FUNCS and n not in PLATFORM]
    extra = [n for n in candidates if resolve_in_libc(n) is not True]
    libc_provided = [n for n in candidates if n not in extra]
    objects = list(dict.fromkeys(PINNED + extra))

    with open(out_path, "w") as fh:
        fh.write("/* 由 test_package/gen_shim.py 生成：kamailio 核心符号 shim。"
                 "占位符不被调用，仅用于满足模块 -z now 全量重定位。 */\n")
        for name in objects:
            fh.write(f'char {name}[64] __attribute__((used, visibility("default")));\n')
        for name, body in FUNCS.items():
            fh.write(f'__attribute__((used, visibility("default"))) {body}\n')
    print(f"shim generated: {out_path} ({len(objects)} objects + {len(FUNCS)} funcs)")
    if extra:
        print(f"  由产物补齐的额外符号: {' '.join(extra)}")
    if libc_provided:
        print(f"  由 OHOS libc 提供(不生成占位符): {' '.join(libc_provided)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
