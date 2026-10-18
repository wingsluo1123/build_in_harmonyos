/*
 * consumer_test.cpp — unicon 3.0.4 消费者用例（业务上层调用模拟）
 *
 * 模拟业务上层组件（如 unicon 主程序）通过库的公开 API（ImmClient.h 的
 * IMM_* 一族）调用本库，验证 编译/链接/调用运行 三关：
 *   1. 连接输入法服务（进程内模式：链 libimmclient.a + libimm_server.so，
 *      无需独立守护进程，与 unicon 主程序 -D__DLL_SUPPORT__ 同一链接形态）
 *   2. 加载拼音输入模块 cce_pinyin 及其数据目录
 *   3. 设置双字节（汉字）输入模式
 *   4. 输入 "kexue"，断言候选列表含 科学（GBK: BF C6 D1 A7）
 *   5. 复位后输入 "zhongguo"，断言候选列表含 中国（GBK: D6 D0 B9 FA）
 *
 * 编译（进程内模式）:
 *   c++ -D__DLL_SUPPORT__ -I<unicon include> consumer_test.cpp \
 *       <libimmclient.a> <libimm_server.so> -o consumer_test
 * 用法: consumer_test <module.so 路径> <数据目录路径>
 * 退出码: 0 = 全过; 1 = 断言失败; 2 = 环境/设置错误
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ImmClient.h>

#ifdef __DLL_SUPPORT__
extern "C" int LibOpen ();
extern "C" int LibRelease ();
#endif

static int type_str (IMM *imm, const char *s)
{
    char buf[MAX_PHRASE_BUFFER];
    int len;
    const char *p;
    for (p = s; *p; p++)
    {
        len = 0;
        if (IMM_KeyFilter (imm, (u_char) *p, buf, &len) < 0)
            return -1;
    }
    return 0;
}

int main (int argc, char **argv)
{
    ImmServer_T t;
    IMM *imm;
    char sel[512];

    if (argc < 3)
    {
        fprintf (stderr, "usage: %s <module.so> <dict-dir>\n", argv[0]);
        return 2;
    }

#ifdef __DLL_SUPPORT__
    LibOpen ();
#endif
    t = IMM_OpenClient ("127.0.0.1", 54321);
    if (t == 0)
    {
        fprintf (stderr, "FAIL: IMM_OpenClient\n");
        return 2;
    }
    imm = IMM_OpenInput (t, argv[1], argv[2], IMM_CCE);
    if (imm == NULL)
    {
        fprintf (stderr, "FAIL: IMM_OpenInput module=%s dict=%s\n",
                 argv[1], argv[2]);
        return 2;
    }
    if (IMM_SetInputMode (imm, IMM_DOUBLE_BYTE_MODE) != 1)
    {
        fprintf (stderr, "FAIL: IMM_SetInputMode\n");
        return 2;
    }

    /* 用例1: kexue -> 候选列表含 科学（GBK BF C6 D1 A7） */
    if (type_str (imm, "kexue") != 0)
    {
        fprintf (stderr, "FAIL: IMM_KeyFilter(kexue)\n");
        return 1;
    }
    if (IMM_GetSelectDisplay (imm, sel, sizeof (sel)) < 0)
    {
        fprintf (stderr, "FAIL: IMM_GetSelectDisplay\n");
        return 2;
    }
    if (strstr (sel, "\xbf\xc6\xd1\xa7") == NULL)
    {
        fprintf (stderr, "FAIL: kexue selection has no 科学 (BF C6 D1 A7)\n");
        return 1;
    }
    printf ("PASS: kexue -> 科学\n");

    /* 用例2: zhongguo -> 候选列表含 中国（GBK D6 D0 B9 FA） */
    IMM_ResetInput (imm);
    if (type_str (imm, "zhongguo") != 0)
    {
        fprintf (stderr, "FAIL: IMM_KeyFilter(zhongguo)\n");
        return 1;
    }
    sel[0] = '\0';
    if (IMM_GetSelectDisplay (imm, sel, sizeof (sel)) < 0)
    {
        fprintf (stderr, "FAIL: IMM_GetSelectDisplay\n");
        return 2;
    }
    if (strstr (sel, "\xd6\xd0\xb9\xfa") == NULL)
    {
        fprintf (stderr, "FAIL: zhongguo selection has no 中国 (D6 D0 B9 FA)\n");
        return 1;
    }
    printf ("PASS: zhongguo -> 中国\n");

    IMM_CloseInput (imm);
    IMM_CloseClient (t);
#ifdef __DLL_SUPPORT__
    LibRelease ();
#endif
    printf ("CONSUMER-TEST PASS\n");
    return 0;
}
