/*
 * Tk 8.6.16 消费者测试（显示无关，E530 口径）。
 *
 * 本平台与 CI worker 都没有 X display（wish / tests/tktest 起不来），因此消费者测试走
 * 不需要显示服务器的真实消费者路径：
 *   ① 头文件契约：tk.h 自己会引 <tcl.h>/<X11/Xlib.h>，能编过即证明本包公开头自包含；
 *   ② Tcl 侧（tk 的运行期依赖）：Tcl_FindExecutable / Tcl_CreateInterp / Tcl_Init，
 *      再真实执行 Tcl 脚本，并校验 tcl_patchLevel 与 tk 依赖的 tcl 同版本；
 *   ③ Tk 侧：Tk_Init 在无显示环境下必然失败，但它的失败"原因"必须是缺显示——其他原因
 *      （库加载失败 / 未签名 Permission denied / 找不到 tk 脚本库）都会在这里暴露；
 *      Tk_Init 同时完成 Tk 内部 Tcl stub 表绑定，之后即可真实调用 Tk 公共 API；
 *   ④ 共享库契约：dlopen 包内 libtk8.6.so，校验 stub / 入口符号存在（扩展挂载契约）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

#include <tcl.h>
#include <tk.h>

static int fail(const char *msg)
{
    printf("FAIL: %s\n", msg);
    return 1;
}

int main(void)
{
    /* 输出走管道时 libc 默认块缓冲，崩溃会吞掉未刷新行；测试输出必须逐行可见 */
    setvbuf(stdout, NULL, _IOLBF, 0);
    printf("compile-time: TK_VERSION=%s TK_PATCH_LEVEL=%s TK_MAJOR_VERSION=%d TK_MINOR_VERSION=%d\n",
           TK_VERSION, TK_PATCH_LEVEL, TK_MAJOR_VERSION, TK_MINOR_VERSION);
    if (strcmp(TK_PATCH_LEVEL, "8.6.16") != 0) {
        return fail("TK_PATCH_LEVEL != 8.6.16");
    }

    /* ② Tcl 侧：tk 的运行期依赖，走 tcl/8.6.16 兄弟包验证过的初始化路径 */
    Tcl_FindExecutable("tclsh");
    Tcl_Interp *interp = Tcl_CreateInterp();
    if (interp == NULL) {
        return fail("Tcl_CreateInterp");
    }
    if (Tcl_Init(interp) != TCL_OK) {
        printf("FAIL: Tcl_Init: %s\n", Tcl_GetStringResult(interp));
        Tcl_DeleteInterp(interp);
        return 1;
    }
    const char *tcl_version = Tcl_GetVar(interp, "tcl_patchLevel", TCL_GLOBAL_ONLY);
    if (tcl_version == NULL || strcmp(tcl_version, "8.6.16") != 0) {
        printf("FAIL: tcl_patchLevel=%s (tk 8.6.16 需要 tcl 8.6.16)\n",
               tcl_version ? tcl_version : "(NULL)");
        Tcl_DeleteInterp(interp);
        return 1;
    }
    printf("runtime: tcl_patchLevel=%s\n", tcl_version);
    if (Tcl_Eval(interp, "expr 2 + 3") != TCL_OK
            || strcmp(Tcl_GetStringResult(interp), "5") != 0) {
        printf("FAIL: Tcl_Eval(expr 2 + 3) -> %s\n", Tcl_GetStringResult(interp));
        Tcl_DeleteInterp(interp);
        return 1;
    }
    printf("runtime: Tcl_Eval(expr 2 + 3) -> 5\n");

    /* ③ Tk 侧：无显示时 Tk_Init 失败，但必须只因缺显示；同时绑定 Tk 内部 Tcl stub 表 */
    int tk_rc = Tk_Init(interp);
    if (tk_rc == TCL_OK) {
        printf("runtime: Tk_Init OK (本环境有可用的 X display)\n");
    } else {
        const char *err = Tcl_GetStringResult(interp);
        printf("runtime: Tk_Init -> %s\n", err ? err : "(NULL)");
        if (err == NULL || strstr(err, "display") == NULL) {
            printf("FAIL: Tk_Init 失败原因不是缺显示（库加载/签名/脚本库问题）\n");
            Tcl_DeleteInterp(interp);
            return 1;
        }
    }

    /* 真实 Tk 公共 API：选项字符串 → 枚举值（纯选项表，不需要显示服务器） */
    Tcl_Obj *obj = Tcl_NewStringObj("sunken", -1);
    Tcl_IncrRefCount(obj);
    int relief = -1;
    int rc = Tk_GetReliefFromObj(interp, obj, &relief);
    Tcl_DecrRefCount(obj);
    if (rc != TCL_OK || relief != TK_RELIEF_SUNKEN) {
        printf("FAIL: Tk_GetReliefFromObj rc=%d val=%d (期望 %d)\n", rc, relief, TK_RELIEF_SUNKEN);
        Tcl_DeleteInterp(interp);
        return 1;
    }
    printf("runtime: Tk_GetReliefFromObj(\"sunken\") -> %d (TK_RELIEF_SUNKEN)\n", relief);

    /* ④ 共享库契约：dlopen 包内 libtk8.6.so，校验入口符号（ELF 不可加载或签名不合法
       ——OHOS 对未签名 ELF 报 Permission denied——都会在这里暴露）。Tk_InitStubs 不在
       共享库里，由静态 stub 库提供，单独在下面按链接期契约校验。 */
    void *h = dlopen("libtk8.6.so", RTLD_NOW | RTLD_GLOBAL);
    if (h == NULL) {
        printf("FAIL: dlopen(libtk8.6.so): %s\n", dlerror());
        Tcl_DeleteInterp(interp);
        return 1;
    }
    const char *needed[] = {"Tk_Init", "Tk_SafeInit", "Tk_MainEx",
                            "Tk_GetReliefFromObj", NULL};
    for (int i = 0; needed[i] != NULL; i++) {
        if (dlsym(h, needed[i]) == NULL) {
            printf("FAIL: libtk8.6.so 缺少符号 %s\n", needed[i]);
            Tcl_DeleteInterp(interp);
            return 1;
        }
    }
    printf("runtime: libtk8.6.so 导出 Tk 入口符号 OK\n");

    /* ⑤ 扩展挂载契约：Tk_InitStubs 由静态 stub 库（libtkstub8.6.a）提供，Tk 扩展靠它
       挂进宿主；链接期解析不出去（stub 库缺失）则本测试直接链接失败。 */
    printf("runtime: Tk_InitStubs(stub 库) -> %p\n", (void *)Tk_InitStubs);

    Tcl_DeleteInterp(interp);
    printf("PASS: tk %s consumer test (no X display needed)\n", TK_PATCH_LEVEL);
    return 0;
}
