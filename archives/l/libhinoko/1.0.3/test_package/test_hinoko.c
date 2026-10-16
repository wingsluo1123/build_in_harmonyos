/* test_hinoko.c — libhinoko test_package 独立测试源（R34/L0c）。
 *
 * 实质消费被测库：调用 hinoko 对外 API（HinokoFwIsoCtx 接口类型、
 * HinokoFwIsoResource 纯函数与 mkenums 生成枚举），链接 libhinoko.so
 * （连带 libhinawa/libgobject/libglib）并在运行期通过 GObject 类型系统
 * 注册路径加载它。注：不打开真实 /dev/fw* 设备（CI 沙箱无 1394 硬件），
 * 只走类型/枚举/纯函数 API。
 */
#include <stdio.h>
#include <hinoko.h>

int main(void)
{
    /* HinokoFwIsoCtx 接口的 GObject 类型在库初始化时注册；取类型并断言 */
    GType iso_ctx_type = hinoko_fw_iso_ctx_get_type();
    if (iso_ctx_type == 0) {
        fprintf(stderr, "FAIL: HinokoFwIsoCtx type not registered\n");
        return 1;
    }
    printf("[PASS] HinokoFwIsoCtx type: %s\n", g_type_name(iso_ctx_type));

    /* 纯函数（不触碰硬件）：S400 速率、0 字节 payload 的等时包 = 3 个头
     * quadlet（12 字节，见 fw_iso_resource.c calculate_bandwidth）。 */
    guint bw = hinoko_fw_iso_resource_calculate_bandwidth(0, HINOKO_FW_SCODE_S400);
    if (bw != 12) {
        fprintf(stderr, "FAIL: calculate_bandwidth() = %u, expected 12\n", bw);
        return 1;
    }
    printf("[PASS] hinoko_fw_iso_resource_calculate_bandwidth: %u\n", bw);

    /* 生成枚举（mkenums 产物，随包安装头 hinoko_enum_types.h）。
     * HINOKO_FW_ISO_CTX_MODE_IT 按 1394 OHCI 规范取 FW_CDEV_ISO_CONTEXT_TRANSMIT=0，
     * 断言其确为 0（== 0 才能真实校验枚举可用，< 0 恒假不可失败）。 */
    if (HINOKO_FW_ISO_CTX_MODE_IT != 0) {
        fprintf(stderr, "FAIL: HinokoFwIsoCtxMode enum value != 0 (got %d)\n", HINOKO_FW_ISO_CTX_MODE_IT);
        return 1;
    }
    printf("[PASS] HinokoFwIsoCtxMode enum available\n");
    return 0;
}
