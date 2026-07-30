#include <HYPRE_utilities.h>

int main(void)
{
    HYPRE_Int major = 0;
    HYPRE_Int minor = 0;
    HYPRE_Int patch = 0;
    HYPRE_Int single = 0;

    if (HYPRE_Initialize() != 0) {
        return 1;
    }
    if (HYPRE_VersionNumber(&major, &minor, &patch, &single) != 0) {
        return 2;
    }
    if (major != 3 || minor != 1 || patch != 0 || single != 30100) {
        return 3;
    }
    return HYPRE_Finalize() == 0 ? 0 : 4;
}
