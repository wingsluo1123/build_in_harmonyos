#include <stdio.h>
#include <mysql.h>

int main(void) {
    if (mysql_library_init(0, NULL, NULL) != 0) {
        fprintf(stderr, "mysql_library_init failed\n");
        return 1;
    }
    MYSQL *conn = mysql_init(NULL);
    if (conn == NULL) {
        fprintf(stderr, "mysql_init failed\n");
        mysql_library_end();
        return 1;
    }
    unsigned long version = mysql_get_client_version();
    printf("mariadb-connector-c client version: %lu\n", version);
    mysql_close(conn);
    mysql_library_end();
    return 0;
}
