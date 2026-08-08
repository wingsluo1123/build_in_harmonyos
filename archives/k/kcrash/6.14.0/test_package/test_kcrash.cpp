// test_kcrash.cpp — Verify KF6Crash library links correctly
#include <KCrash>
#include <cstdio>

int main() {
    // Verify KF6Crash is linkable by calling an exported function
    KCrash::HandlerType handler = KCrash::crashHandler();
    (void)handler; // Initially null, no handler set yet

    printf("kcrash test: KF6Crash linked and functional\n");
    return 0;
}
