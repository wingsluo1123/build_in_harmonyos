#include <mysql.h>
#include <stdio.h>

int main(void) {
    printf("MariaDB client version: %s\n", mysql_get_client_info());
    MYSQL *conn = mysql_init(NULL);
    if (conn == NULL) {
        fprintf(stderr, "mysql_init() failed\n");
        return 1;
    }
    printf("mysql_init() succeeded\n");
    mysql_close(conn);
    printf("mysql_close() succeeded\n");
    return 0;
}
