#include <discid/discid.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int offsets[] = {30000, 150, 15000};
    DiscId *disc = discid_new();
    const char *id;

    if (!disc)
        return 1;
    if (!discid_put(disc, 1, 2, offsets)) {
        discid_free(disc);
        return 2;
    }
    id = discid_get_id(disc);
    if (!id || strlen(id) != 28) {
        discid_free(disc);
        return 3;
    }
    printf("libdiscid generated id: %s\n", id);
    discid_free(disc);
    return 0;
}
