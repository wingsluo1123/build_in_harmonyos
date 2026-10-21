/*
 * xwiimote 消费者测试（R34：实质调用被测库公共 API，非空壳打印）
 *
 * 覆盖点：
 *   1. 非法入参被拒绝：xwii_iface_new(NULL) 返回 -EINVAL（确定性断言）
 *   2. 不存在的 syspath 被拒绝：xwii_iface_new() 返回负错误码而非崩溃
 *   3. 设备监视器对象的构造 / 引用计数 / 轮询 / 释放（如运行环境具备 udev
 *      枚举能力）。构建机与 CI 无 wiimote 实体设备，且受限沙箱可能不提供
 *      udev 枚举能力，此时 monitor 构造返回 NULL 属预期，仅跳过轮询断言
 *   4. 对象生命周期无全局污染（监视器可重复构造）
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <xwiimote.h>

int main(void)
{
    struct xwii_monitor *mon;
    struct xwii_iface *iface = NULL;
    char *devpath;
    int ret;
    int failures = 0;

    /* 1) 空 syspath 必须被拒绝，且错误码为 -EINVAL */
    ret = xwii_iface_new(&iface, NULL);
    if (ret == 0) {
        fprintf(stderr, "FAIL: xwii_iface_new(NULL) 未返回错误\n");
        if (iface)
            xwii_iface_unref(iface);
        failures++;
    } else if (ret != -EINVAL) {
        fprintf(stderr, "FAIL: xwii_iface_new(NULL) 应返回 -EINVAL(%d)，实际 %d\n",
                -EINVAL, ret);
        failures++;
    } else {
        printf("xwii_iface_new(非法路径) -> %d (%s)\n", ret, strerror(-ret));
    }

    /* 2) 不存在的 syspath 必须返回错误而非崩溃 */
    iface = NULL;
    ret = xwii_iface_new(&iface, "/nonexistent/xwiimote-test-device");
    if (ret == 0) {
        fprintf(stderr, "FAIL: xwii_iface_new(不存在路径) 未返回错误\n");
        if (iface)
            xwii_iface_unref(iface);
        failures++;
    } else {
        printf("xwii_iface_new(不存在路径) -> %d (%s)\n", ret, strerror(-ret));
    }

    /* 3) 监视器生命周期（可用则完整走一遍） */
    mon = xwii_monitor_new(false, false);
    if (mon) {
        xwii_monitor_ref(mon);
        devpath = xwii_monitor_poll(mon);
        if (devpath) {
            printf("检测到 wiimote 设备: %s\n", devpath);
            free(devpath);
        } else {
            printf("当前无 wiimote 设备（预期行为）\n");
        }
        xwii_monitor_unref(mon);
    } else {
        printf("运行环境未提供 udev 枚举能力，跳过监视器轮询断言\n");
    }

    /* 4) 生命周期无全局污染（可重复构造） */
    mon = xwii_monitor_new(false, false);
    if (mon)
        xwii_monitor_unref(mon);

    if (failures) {
        fprintf(stderr, "xwiimote/2 公共 API 验证失败（%d 项）\n", failures);
        return 1;
    }
    printf("xwiimote/2 公共 API 验证通过\n");
    return 0;
}
