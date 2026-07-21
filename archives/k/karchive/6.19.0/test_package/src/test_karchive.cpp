// R34: 实质调用 KZip 验证链通
#include <KZip>
#include <KArchive>
#include <cstdio>

int main() {
    KZip zip(QStringLiteral("/tmp/test_nonexistent.zip"));
    (void)zip;
    printf("karchive link OK\n");
    return 0;
}
