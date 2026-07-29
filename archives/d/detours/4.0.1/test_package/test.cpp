#include <windows.h>
#include <detours.h>
#include <stdio.h>

int main() {
    BOOL isHelper = DetourIsHelperProcess();
    printf("DetourIsHelperProcess() = %d\n", (int)isHelper);
    printf("Detours library linked successfully.\n");
    return 0;
}
