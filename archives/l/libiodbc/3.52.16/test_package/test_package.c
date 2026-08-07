#include <sql.h>
#include <sqlext.h>
#include <stdio.h>

int main(void) {
    SQLHENV env;
    SQLRETURN ret;

    ret = SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &env);
    if (ret != SQL_SUCCESS && ret != SQL_SUCCESS_WITH_INFO) {
        fprintf(stderr, "SQLAllocHandle failed: %d\n", (int)ret);
        return 1;
    }

    printf("iODBC environment handle allocated successfully\n");

    SQLFreeHandle(SQL_HANDLE_ENV, env);
    printf("iODBC test passed\n");
    return 0;
}
