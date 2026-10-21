/*
 * test.c — w-calc 2.5 消费者视角测试
 *
 * 真实执行安装产物 bin/wcalc（路径经 argv[1] 传入，来自被测 conan 包的
 * package_folder，避免依赖 PATH），共 8 个确定性断言：
 *   1. 二进制存在且可执行
 *   2. wcalc --version 退出码为 0 且输出含 "2.5"
 *   3. wcalc -q '1+2' 输出为 3
 *   4. wcalc -q -P10 '1/3' 输出为 0.3333333333（精度设置生效）
 *   5. wcalc -q -h '255' 输出为 0xff（十六进制输出）
 *   6. wcalc -q 'x=7' 'x*3' 末行输出为 21（变量跨参数持久）
 *   7. 标准输入 "1+2"（printf 管道）输出为 3（普通交互模式）
 *   8. wcalc -q 'foo(' 输出含 "syntax error"（语法错误诊断）
 *
 * R34：非空壳——真实调用被测二进制并逐项断言，任何一项失败返回非零。
 * 计数（discovered/passedCount）由本程序真实断言结果得出，并输出
 * HMBS_TEST_PACKAGE_RESULT 标记供门禁读取。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int g_discovered = 0;
static int g_passed = 0;

/* 去掉首尾空白（含换行） */
static void trim(char *s) {
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r' ||
                     s[n - 1] == ' ' || s[n - 1] == '\t')) {
        s[--n] = '\0';
    }
    size_t start = 0;
    while (s[start] == ' ' || s[start] == '\t') {
        start++;
    }
    if (start > 0) {
        memmove(s, s + start, n - start + 1);
    }
}

/* 取最后一个非空行（去掉首尾空白）；无则返回空串 */
static const char *last_line(const char *buf) {
    static char keep[4096];
    static char line[4096];
    keep[0] = '\0';
    const char *p = buf;
    while (p && *p) {
        const char *nl = strchr(p, '\n');
        size_t len = nl ? (size_t)(nl - p) : strlen(p);
        if (len >= sizeof(line)) {
            len = sizeof(line) - 1;
        }
        memcpy(line, p, len);
        line[len] = '\0';
        trim(line);
        if (line[0] != '\0') {
            strcpy(keep, line);
        }
        if (!nl) {
            break;
        }
        p = nl + 1;
    }
    return keep;
}

/* 运行 `bin [extra]`（stdin 可为 NULL），输出写入 out */
static int run_wcalc(const char *bin, const char *args,
                     const char *stdin_data, char *out, size_t outsz) {
    char cmd[4096];
    if (stdin_data) {
        snprintf(cmd, sizeof(cmd), "printf '%%s' '%s' | \"%s\" %s 2>&1",
                 stdin_data, bin, args);
    } else {
        snprintf(cmd, sizeof(cmd), "\"%s\" %s 2>&1", bin, args);
    }
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        return -1;
    }
    size_t n = fread(out, 1, outsz - 1, fp);
    out[n] = '\0';
    return pclose(fp);
}

static void check(const char *label, int ok, const char *detail) {
    g_discovered++;
    if (ok) {
        g_passed++;
        printf("PASS: %s\n", label);
    } else {
        printf("FAIL: %s (%s)\n", label, detail ? detail : "");
    }
}

int main(int argc, char *argv[]) {
    const char *bin = (argc > 1) ? argv[1] : "wcalc";
    char out[8192];

    printf("Testing wcalc binary: %s\n", bin);

    /* 1. 二进制存在且可执行 */
    check("binary executable", access(bin, X_OK) == 0, "not executable");

    /* 2. --version 含 2.5 */
    out[0] = '\0';
    int rc = run_wcalc(bin, "--version", NULL, out, sizeof(out));
    check("version reports 2.5",
          rc == 0 && strstr(out, "2.5") != NULL, out);

    /* 3. 整数算术 */
    out[0] = '\0';
    run_wcalc(bin, "-q '1+2'", NULL, out, sizeof(out));
    {
        const char *v = last_line(out);
        check("arithmetic 1+2=3", strcmp(v, "3") == 0, v);
    }

    /* 4. 精度设置 */
    out[0] = '\0';
    run_wcalc(bin, "-q -P10 '1/3'", NULL, out, sizeof(out));
    {
        const char *v = last_line(out);
        check("precision -P10 1/3", strcmp(v, "0.3333333333") == 0, v);
    }

    /* 5. 十六进制输出 */
    out[0] = '\0';
    run_wcalc(bin, "-q -h '255'", NULL, out, sizeof(out));
    {
        const char *v = last_line(out);
        check("hexadecimal 255=0xff", strcmp(v, "0xff") == 0, v);
    }

    /* 6. 变量跨参数持久 */
    out[0] = '\0';
    run_wcalc(bin, "-q 'x=7' 'x*3'", NULL, out, sizeof(out));
    {
        const char *v = last_line(out);
        check("variables persist", strcmp(v, "21") == 0, v);
    }

    /* 7. 标准输入交互模式 */
    out[0] = '\0';
    run_wcalc(bin, "-q", "1+2\n", out, sizeof(out));
    {
        const char *v = last_line(out);
        check("stdin evaluated", strcmp(v, "3") == 0, v);
    }

    /* 8. 语法错误诊断 */
    out[0] = '\0';
    run_wcalc(bin, "-q 'foo('", NULL, out, sizeof(out));
    check("syntax diagnostic",
          strstr(out, "syntax error") != NULL, out);

    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
           "\"command\":\"test_wcalc %s\",\"discovered\":%d,\"passedCount\":%d}\n",
           (g_passed == g_discovered) ? "true" : "false",
           bin, g_discovered, g_passed);

    if (g_passed != g_discovered) {
        fprintf(stderr, "wcalc consumer tests FAILED: %d/%d\n",
                g_passed, g_discovered);
        return 1;
    }
    printf("All %d wcalc consumer tests passed\n", g_discovered);
    return 0;
}
