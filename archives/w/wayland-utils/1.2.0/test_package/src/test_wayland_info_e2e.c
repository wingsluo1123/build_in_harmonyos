/* test_wayland_info_e2e.c — wayland-utils 1.2.0 层 1 消费者 E2E 测试
 *
 * 消费链与上游 wayland-info/meson.build 完全一致：test_package 配方用
 * 静态构建的 wayland-scanner（主配方同款：OHOS 禁止 execve conan 缓存
 * 内解出的二进制）对 wayland-protocols 1.48 安装集内上游实际消费的
 * 5 组协议 XML（generated_protocols 字典：presentation-time /
 * drm-lease-v1 / linux-dmabuf-unstable-v1 / tablet-unstable-v2 /
 * xdg-output-unstable-v1，共 19 个接口）生成 client-header +
 * private-code，与本程序一起编译链接。
 *
 * 运行时逐接口核验编译态接口数据与包内 XML 定义一致：
 *   ① 接口名（wl_interface::name）
 *   ② 版本号（wl_interface::version）
 *   ③ 消息计数（method_count + event_count > 0）——接口已被填充。
 *      注意 wp_presentation_feedback 是纯事件接口（0 个 request），
 *      因此不能要求 method_count > 0，否则对合法的空请求接口误报。
 *   ④ 包内 XML 原样包含 name="..." 与 version="N" 属性
 *
 * 19 用例 × 4 检查点 = 76 项，每例独立 TEST PASS/FAIL，末行 TEST
 * SUMMARY，任一失败退出码 1。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "wayland-util.h"

#include "presentation-time-client-protocol.h"
#include "drm-lease-v1-client-protocol.h"
#include "linux-dmabuf-unstable-v1-client-protocol.h"
#include "tablet-unstable-v2-client-protocol.h"
#include "xdg-output-unstable-v1-client-protocol.h"

struct probe {
    const char *label;
    const struct wl_interface *iface;
    const char *expect_name;
    int expect_version;
    const char *xml_rel; /* 相对 pkgdatadir 的 XML 路径 */
};

/* 19 个接口：上游 wayland-info/meson.build generated_protocols 字典的
 * 5 组协议（wayland-protocols 1.48 安装集），接口名/版本取自包内 XML
 * 实测（grep '<interface name=... version=...' 逐个核对）。 */
static struct probe probes[] = {
    /* presentation-time (stable) */
    {"stable/presentation-time.wp_presentation",
     &wp_presentation_interface, "wp_presentation", 2,
     "stable/presentation-time/presentation-time.xml"},
    {"stable/presentation-time.wp_presentation_feedback",
     &wp_presentation_feedback_interface, "wp_presentation_feedback", 2,
     "stable/presentation-time/presentation-time.xml"},

    /* drm-lease-v1 (staging) */
    {"staging/drm-lease.wp_drm_lease_device_v1",
     &wp_drm_lease_device_v1_interface, "wp_drm_lease_device_v1", 1,
     "staging/drm-lease/drm-lease-v1.xml"},
    {"staging/drm-lease.wp_drm_lease_connector_v1",
     &wp_drm_lease_connector_v1_interface, "wp_drm_lease_connector_v1", 1,
     "staging/drm-lease/drm-lease-v1.xml"},
    {"staging/drm-lease.wp_drm_lease_request_v1",
     &wp_drm_lease_request_v1_interface, "wp_drm_lease_request_v1", 1,
     "staging/drm-lease/drm-lease-v1.xml"},
    {"staging/drm-lease.wp_drm_lease_v1",
     &wp_drm_lease_v1_interface, "wp_drm_lease_v1", 1,
     "staging/drm-lease/drm-lease-v1.xml"},

    /* linux-dmabuf-unstable-v1 (unstable) */
    {"unstable/linux-dmabuf.zwp_linux_dmabuf_v1",
     &zwp_linux_dmabuf_v1_interface, "zwp_linux_dmabuf_v1", 5,
     "unstable/linux-dmabuf/linux-dmabuf-unstable-v1.xml"},
    {"unstable/linux-dmabuf.zwp_linux_buffer_params_v1",
     &zwp_linux_buffer_params_v1_interface, "zwp_linux_buffer_params_v1", 5,
     "unstable/linux-dmabuf/linux-dmabuf-unstable-v1.xml"},
    {"unstable/linux-dmabuf.zwp_linux_dmabuf_feedback_v1",
     &zwp_linux_dmabuf_feedback_v1_interface, "zwp_linux_dmabuf_feedback_v1", 5,
     "unstable/linux-dmabuf/linux-dmabuf-unstable-v1.xml"},

    /* tablet-unstable-v2 (unstable) */
    {"unstable/tablet.zwp_tablet_manager_v2",
     &zwp_tablet_manager_v2_interface, "zwp_tablet_manager_v2", 1,
     "unstable/tablet/tablet-unstable-v2.xml"},
    {"unstable/tablet.zwp_tablet_seat_v2",
     &zwp_tablet_seat_v2_interface, "zwp_tablet_seat_v2", 1,
     "unstable/tablet/tablet-unstable-v2.xml"},
    {"unstable/tablet.zwp_tablet_tool_v2",
     &zwp_tablet_tool_v2_interface, "zwp_tablet_tool_v2", 1,
     "unstable/tablet/tablet-unstable-v2.xml"},
    {"unstable/tablet.zwp_tablet_v2",
     &zwp_tablet_v2_interface, "zwp_tablet_v2", 1,
     "unstable/tablet/tablet-unstable-v2.xml"},
    {"unstable/tablet.zwp_tablet_pad_ring_v2",
     &zwp_tablet_pad_ring_v2_interface, "zwp_tablet_pad_ring_v2", 1,
     "unstable/tablet/tablet-unstable-v2.xml"},
    {"unstable/tablet.zwp_tablet_pad_strip_v2",
     &zwp_tablet_pad_strip_v2_interface, "zwp_tablet_pad_strip_v2", 1,
     "unstable/tablet/tablet-unstable-v2.xml"},
    {"unstable/tablet.zwp_tablet_pad_group_v2",
     &zwp_tablet_pad_group_v2_interface, "zwp_tablet_pad_group_v2", 1,
     "unstable/tablet/tablet-unstable-v2.xml"},
    {"unstable/tablet.zwp_tablet_pad_v2",
     &zwp_tablet_pad_v2_interface, "zwp_tablet_pad_v2", 1,
     "unstable/tablet/tablet-unstable-v2.xml"},

    /* xdg-output-unstable-v1 (unstable) */
    {"unstable/xdg-output.zxdg_output_manager_v1",
     &zxdg_output_manager_v1_interface, "zxdg_output_manager_v1", 3,
     "unstable/xdg-output/xdg-output-unstable-v1.xml"},
    {"unstable/xdg-output.zxdg_output_v1",
     &zxdg_output_v1_interface, "zxdg_output_v1", 3,
     "unstable/xdg-output/xdg-output-unstable-v1.xml"},
};

static int n_pass = 0;
static int n_fail = 0;

static void check(int ok, const char *what, const char *detail)
{
    if (ok) {
        printf("  TEST PASS %s%s%s\n", what, detail ? " " : "",
               detail ? detail : "");
        n_pass++;
    } else {
        printf("  TEST FAIL %s%s%s\n", what, detail ? " " : "",
               detail ? detail : "");
        n_fail++;
    }
}

/* 读包内 XML，核对 name="..." 与 version="N" 是否原样存在 */
static int xml_has(const char *pkgdatadir, const char *rel,
                   const char *name, int version)
{
    char path[2048];
    char want[1024];
    char *buf;
    FILE *f;
    long n;
    int ok;

    snprintf(path, sizeof path, "%s/%s", pkgdatadir, rel);
    f = fopen(path, "rb");
    if (!f)
        return 0;
    fseek(f, 0, SEEK_END);
    n = ftell(f);
    fseek(f, 0, SEEK_SET);
    buf = (char *)malloc((size_t)n + 1);
    if (!buf) {
        fclose(f);
        return 0;
    }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) {
        free(buf);
        fclose(f);
        return 0;
    }
    fclose(f);
    buf[n] = '\0';

    snprintf(want, sizeof want, "name=\"%s\"", name);
    ok = strstr(buf, want) != NULL;
    if (ok) {
        snprintf(want, sizeof want, "version=\"%d\"", version);
        ok = strstr(buf, want) != NULL;
    }
    free(buf);
    return ok;
}

int main(int argc, char **argv)
{
    const char *pkgdatadir;
    size_t i;

    if (argc < 2) {
        fprintf(stderr, "usage: test_wayland_info_e2e <pkgdatadir>\n");
        return 2;
    }
    pkgdatadir = argv[1];

    for (i = 0; i < sizeof probes / sizeof probes[0]; i++) {
        struct probe *p = &probes[i];
        printf("TEST CASE %s\n", p->label);
        check(p->iface && p->iface->name &&
              strcmp(p->iface->name, p->expect_name) == 0,
              "- 接口名",
              (p->iface && p->iface->name) ? p->iface->name : "NULL");
        check(p->iface && p->iface->version == p->expect_version,
              "- 版本号", NULL);
        check(p->iface &&
              (p->iface->method_count + p->iface->event_count) > 0,
              "- 方法/事件计数", NULL);
        check(xml_has(pkgdatadir, p->xml_rel, p->expect_name,
                      p->expect_version),
              "- 包内XML一致", p->xml_rel);
    }
    printf("TEST SUMMARY: %d passed, %d failed\n", n_pass, n_fail);
    return n_fail == 0 ? 0 : 1;
}
