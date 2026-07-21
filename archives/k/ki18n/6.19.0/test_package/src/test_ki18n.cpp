// R34: 实质调用 KLocalizedString API 验证链通
#include <KLocalizedString>
#include <cstdio>

int main() {
    KLocalizedString kl = kxi18n("Hello");
    (void)kl;
    printf("ki18n link OK\n");
    return 0;
}
