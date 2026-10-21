/* OHOS (HarmonyOS PC) 端到端消费者用例 — uim 1.9.6
 *
 * 四段式真实业务闭环（非断言清单）：
 *   段1 构造输入：uim_init() 初始化库（setlocale + Scheme 运行时数据装载）
 *   段2 真实执行：uim_create_context() 创建真实输入上下文（注册真实 commit 回调）
 *   段3 产出结果：枚举上下文的输入法集合，逐个校验名称/语言/编码/描述，
 *                并按 locale 查询默认输入法（均为库内真实业务数据）
 *   段4 校验内容：每步按业务语义强校验，失败返回 1，全通过返回 0
 *
 * 强校验说明（不放过数据缺失回归）：
 *   - uim_get_nr_im() 必须 >= 1：若返回 0 说明 Scheme 运行时数据（share/uim 下的
 *     *.scm）未装载成功，属产品缺陷，必须失败而非容忍。
 *   - uim_get_im_name(uc, 0) 必须非 NULL 且非空串。
 *   - uim_get_im_name_for_locale("zh_CN") / uim_get_default_im_name("zh_CN")
 *     必须非 NULL 且非空串。
 */

#include <stdio.h>
#include <string.h>
#include <uim/uim.h>

/* 真实 commit 回调：统计提交次数并记录最近一次提交串 */
static int g_commit_count = 0;
static char g_last_commit[256];

static void commit_cb(void *ptr, const char *str) {
    (void)ptr;
    if (str) {
        g_commit_count++;
        snprintf(g_last_commit, sizeof(g_last_commit), "%s", str);
    }
}

static int fail(const char *msg, uim_context uc) {
    fprintf(stderr, "FAIL: %s\n", msg);
    if (uc) {
        uim_release_context(uc);
    }
    uim_quit();
    return 1;
}

int main(void) {
    /* 段1: 构造 — 初始化 uim 库（0 = 成功，-1 = 失败） */
    int init_ret = uim_init();
    printf("[step1] uim_init -> %d\n", init_ret);
    if (init_ret != 0) {
        fprintf(stderr, "FAIL: uim_init returned %d\n", init_ret);
        return 1;
    }

    /* 段2: 真实执行 — 创建输入上下文（UTF-8 编码，真实 commit 回调） */
    uim_context uc = uim_create_context(NULL, "UTF-8", NULL, NULL, NULL, commit_cb);
    printf("[step2] uim_create_context -> %p\n", (void *)uc);
    if (!uc) {
        uim_quit();
        return fail("uim_create_context returned NULL", NULL);
    }

    /* 段3: 产出 — 校验上下文的输入法集合（库内真实数据，不允许为零） */
    int nr = uim_get_nr_im(uc);
    printf("[step3] uim_get_nr_im -> %d\n", nr);
    if (nr < 1) {
        return fail("uim_get_nr_im < 1 (Scheme runtime data not loaded)", uc);
    }

    for (int i = 0; i < nr; i++) {
        const char *name = uim_get_im_name(uc, i);
        const char *lang = uim_get_im_language(uc, i);
        const char *enc = uim_get_im_encoding(uc, i);
        const char *desc = uim_get_im_short_desc(uc, i);
        printf("[step3] im[%d]: name=%s language=%s encoding=%s desc=%s\n",
               i,
               name ? name : "(null)",
               lang ? lang : "(null)",
               enc ? enc : "(null)",
               desc ? desc : "(null)");
        if (!name || name[0] == '\0') {
            return fail("uim_get_im_name returned NULL/empty", uc);
        }
        if (!lang || lang[0] == '\0') {
            return fail("uim_get_im_language returned NULL/empty", uc);
        }
        if (!enc || enc[0] == '\0') {
            return fail("uim_get_im_encoding returned NULL/empty", uc);
        }
    }

    /* 段3b: 按 locale 查询默认输入法（真实查表路径） */
    const char *im_zh = uim_get_im_name_for_locale("zh_CN");
    const char *im_default = uim_get_default_im_name("zh_CN");
    printf("[step3] uim_get_im_name_for_locale(zh_CN) -> %s\n",
           im_zh ? im_zh : "(null)");
    printf("[step3] uim_get_default_im_name(zh_CN) -> %s\n",
           im_default ? im_default : "(null)");
    if (!im_zh || im_zh[0] == '\0') {
        return fail("uim_get_im_name_for_locale(\"zh_CN\") returned NULL/empty", uc);
    }
    if (!im_default || im_default[0] == '\0') {
        return fail("uim_get_default_im_name(\"zh_CN\") returned NULL/empty", uc);
    }

    /* 段4: 校验 + 清理 — 上下文生命周期回收、库退出
     * 纯查询流程不应触发任何 commit 回调：回调计数必须为 0，
     * 否则说明库在非提交路径上误触发消费者回调（副作用回归）。
     * 注：真实的输入提交（im-commit）是 uim 的 Scheme 层原语，C 消费者 API
     * 没有对应入口，无法从 C 侧驱动一次真实提交；因此这里校验的是
     * 「回调已注册但未被误触发」这一消费者可见行为，而非伪造提交。 */
    uim_release_context(uc);
    uim_quit();
    printf("[step4] ims=%d commit_cb=%d last_commit=\"%s\"\n",
           nr, g_commit_count, g_commit_count ? g_last_commit : "");
    if (g_commit_count != 0) {
        fprintf(stderr, "FAIL: commit callback fired %d time(s) during query-only flow\n",
                g_commit_count);
        return 1;
    }

    printf("uim consumer e2e: PASS (init=0, context ok, nr_im=%d, locale lookup ok)\n", nr);
    return 0;
}
