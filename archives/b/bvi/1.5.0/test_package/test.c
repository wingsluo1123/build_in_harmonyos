#include <stdlib.h>

int main(void)
{
    int ret = system("bvi --version");
    return ret == 0 ? 0 : 1;
}
