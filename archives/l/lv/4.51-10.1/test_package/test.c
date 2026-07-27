#include <stdlib.h>
#include <stdio.h>
#include <sys/wait.h>

int main() {
    int ret = system("lv --help > /dev/null 2>&1");
    /* system() 返回值是 wait status，需用 WEXITSTATUS 解码出子进程退出码 */
    if (ret == -1 || !WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        printf("FAIL: lv --help failed with exit code %d\n", ret);
        return 1;
    }
    printf("test lv 4.51-10.1: OK (lv --help passed)\n");
    return 0;
}
