/* Actual installed menu API state in UID-owned HarmonyOS storage. */
#include <libdbusmenu-glib/dbusmenu-glib.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    struct utsname u;
    struct stat st;
    char *real = NULL, *path = NULL, *text = NULL, *readback = NULL;
    GError *error = NULL;
    GVariant *parsed = NULL;
    DbusmenuMenuitem *item = NULL;
    int fd = -1, status = 1;
    gsize length = 0;
    if (argc != 2 || uname(&u) || strcmp(u.sysname, "HarmonyOS")) goto done;
    real = realpath(argv[1], NULL);
    if (!real || strcmp(real, argv[1]) || lstat(real, &st) ||
        !S_ISDIR(st.st_mode) || st.st_uid != getuid() || (st.st_mode & 0777) != 0700) goto done;
    item = dbusmenu_menuitem_new();
    if (!item || !dbusmenu_menuitem_property_set(item, DBUSMENU_MENUITEM_PROP_LABEL,
                                               "Harmony menu: 中文")) goto done;
    GVariant *value = dbusmenu_menuitem_property_get_variant(item, DBUSMENU_MENUITEM_PROP_LABEL);
    if (!value || !g_variant_is_of_type(value, G_VARIANT_TYPE_STRING)) goto done;
    text = g_variant_print(value, TRUE);
    path = g_strdup_printf("%s/menu-state-%ld", real, (long)getpid());
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0 || fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid != getuid() ||
        (st.st_mode & 0777) != 0600) goto done;
    size_t count = strlen(text), offset = 0;
    while (offset < count) {
        ssize_t written = write(fd, text + offset, count - offset);
        if (written <= 0) goto done;
        offset += (size_t)written;
    }
    if (close(fd)) { fd = -1; goto done; }
    fd = -1;
    if (!g_file_get_contents(path, &readback, &length, &error) || length != count) goto done;
    parsed = g_variant_parse(G_VARIANT_TYPE_STRING, readback, NULL, NULL, &error);
    if (!parsed || !g_variant_equal(value, parsed)) goto done;
    if (unlink(path)) goto done;
    status = 0;
    puts("HARMONY_TEST_COUNT=1\nHARMONY_DBUSMENU_OWNED_STATE=1/1 PASS\nHARMONY_TEST_PASS=1/1");
done:
    if (fd >= 0) close(fd);
    if (status && path) unlink(path);
    if (status) fputs("Actual Harmony menu state test failed\n", stderr);
    if (parsed) g_variant_unref(parsed);
    if (item) g_object_unref(item);
    if (error) g_error_free(error);
    free(real);g_free(path);g_free(text);g_free(readback);
    return status;
}
