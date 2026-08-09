#ifndef SQLITE3_H_STUB
#define SQLITE3_H_STUB
/* HarmonyOS stub: FLB_SQLDB=Off */
typedef struct sqlite3 sqlite3;
typedef struct sqlite3_stmt sqlite3_stmt;
typedef long long sqlite3_int64;
#define SQLITE_OK 0
#define SQLITE_ERROR 1
#define SQLITE_BUSY 5
#define SQLITE_ROW 100
#define SQLITE_DONE 101
#define SQLITE_INTEGER 1
#define SQLITE_TEXT 3
#define SQLITE_OPEN_READWRITE 2
#define SQLITE_OPEN_CREATE 4
static inline int sqlite3_open(const char *f, sqlite3 **d) { return SQLITE_ERROR; }
static inline int sqlite3_open_v2(const char *f, sqlite3 **d, int f2, const char *v) { return SQLITE_ERROR; }
static inline int sqlite3_close(sqlite3 *d) { return SQLITE_OK; }
static inline int sqlite3_prepare_v2(sqlite3 *d, const char *sql, int n, sqlite3_stmt **s, const char **t) { return SQLITE_ERROR; }
static inline int sqlite3_step(sqlite3_stmt *s) { return SQLITE_DONE; }
static inline int sqlite3_finalize(sqlite3_stmt *s) { return SQLITE_OK; }
static inline const char *sqlite3_errmsg(sqlite3 *d) { return "stub: SQLite not available"; }
static inline int sqlite3_bind_int(sqlite3_stmt *s, int i, int v) { return SQLITE_OK; }
static inline int sqlite3_bind_int64(sqlite3_stmt *s, int i, sqlite3_int64 v) { return SQLITE_OK; }
static inline int sqlite3_bind_text(sqlite3_stmt *s, int i, const char *v, int n, void(*d)(void*)) { return SQLITE_OK; }
static inline int sqlite3_column_count(sqlite3_stmt *s) { return 0; }
static inline int sqlite3_column_type(sqlite3_stmt *s, int i) { return SQLITE_INTEGER; }
static inline int sqlite3_column_int(sqlite3_stmt *s, int i) { return 0; }
static inline sqlite3_int64 sqlite3_column_int64(sqlite3_stmt *s, int i) { return 0; }
static inline const char *sqlite3_column_text(sqlite3_stmt *s, int i) { return NULL; }
static inline const char *sqlite3_column_name(sqlite3_stmt *s, int i) { return NULL; }
static inline int sqlite3_exec(sqlite3 *d, const char *sql, int(*cb)(void*,int,char**,char**), void *a, char **e) { return SQLITE_ERROR; }
static inline int sqlite3_bind_parameter_count(sqlite3_stmt *s) { return 0; }
static inline int sqlite3_clear_bindings(sqlite3_stmt *s) { return SQLITE_OK; }
static inline int sqlite3_reset(sqlite3_stmt *s) { return SQLITE_OK; }
#endif
