/* klystrack 0.20171212 consumer test
 * 验证 klystrack 二进制：--version 输出非空 + --help 退出码 0 + SDL2 运行时可用 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <SDL2/SDL.h>

int main(void) {
    /* aireview P2: 增 SDL_Init/SDL_Quit 验证 SDL2 运行时可用性（非仅 --help） */
    /* P3: SDL_INIT_VIDEO 在无头 CI 可能误报失败 → 改 SDL_INIT_EVENTS 避无头环境依赖 */
    if (SDL_Init(SDL_INIT_EVENTS) != 0) {
        fprintf(stderr, "FAIL: SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    SDL_Quit();

    /* 1. 验证 klystrack --version 输出非空 */
    FILE *fp = popen("klystrack --version 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run klystrack --version\n");
        return 1;
    }
    char buf[256] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    /* P2: pclose 返回值检查（aireview: 忽略致二进制运行失败时仍报通过） */
    /* P3: pclose 返 shell 退出码需 WEXITSTATUS 解析真实退出码避误报 */
    int pc_ret = pclose(fp);
    if (pc_ret != 0) {
        int real_code = WIFEXITED(pc_ret) ? WEXITSTATUS(pc_ret) : -1;
        fprintf(stderr, "FAIL: klystrack --version exited with code %d (pclose raw %d)\n", real_code, pc_ret);
        return 1;
    }
    if (n == 0 || strlen(buf) == 0) {
        fprintf(stderr, "FAIL: klystrack --version produced no output\n");
        return 1;
    }
    printf("klystrack version: %s", buf);

    /* 2. 验证 klystrack --help 退出码 0 */
    int ret = system("klystrack --help > /dev/null 2>&1");
    if (ret != 0) {
        /* P3: system 返 shell 退出码需 WEXITSTATUS 解析真实退出码避误报 */
        int real_code = WIFEXITED(ret) ? WEXITSTATUS(ret) : -1;
        fprintf(stderr, "FAIL: klystrack --help exited with code %d (system raw %d)\n", real_code, ret);
        return 1;
    }
    printf("klystrack --help OK\n");

    printf("klystrack smoke test PASSED\n");
    return 0;
}
