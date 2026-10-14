/*
 * libcddb 安装包消费者测试（OHOS 上真实执行，全程离线）。
 *
 * 断言公开 API 真的可用（符号在运行时真实解析、对象生命周期正确），
 * 而非仅"能编译能链接"：
 *   1) CDDB_VERSION（<cddb/version.h>）必须自报 1.3.2 —— 证明头文件与库配套；
 *   2) cddb_new() 必须返回可用句柄，cddb_destroy() 必须能安全释放；
 *   3) 句柄上的只读查询（cddb_errno）与设置（cddb_set_timeout）可调用，
 *      状态码为合法整数 —— 覆盖真实调用路径。
 * 任一断言失败即以非零退出码结束，使 test_package 真实失败。
 */
#include <cddb/cddb.h>
#include <cddb/version.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    printf("libcddb version: %s\n", CDDB_VERSION);
    if (strncmp(CDDB_VERSION, "1.3.2", 5) != 0) {
        fprintf(stderr, "CDDB_VERSION 自报 %s，期望 1.3.2\n", CDDB_VERSION);
        return 1;
    }

    libcddb_init();

    cddb_conn_t *conn = cddb_new();
    if (conn == NULL) {
        fprintf(stderr, "cddb_new() 返回 NULL\n");
        libcddb_shutdown();
        return 1;
    }

    cddb_set_timeout(conn, 1);
    int err = cddb_errno(conn);
    printf("cddb_errno() = %d（新建连接的初始状态）\n", err);
    if (err != 0) {
        /* 新建且未做任何 I/O 的连接不应带错误状态 */
        fprintf(stderr, "新建连接的 cddb_errno() 非 0：%d\n", err);
        cddb_destroy(conn);
        libcddb_shutdown();
        return 1;
    }

    cddb_destroy(conn);
    libcddb_shutdown();
    printf("cddb_new/cddb_destroy 生命周期正常\n");
    return 0;
}
