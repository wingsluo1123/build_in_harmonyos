#include <stdio.h>

#include <gfbgraph/gfbgraph.h>
#include <gfbgraph/gfbgraph-album.h>
#include <gfbgraph/gfbgraph-node.h>
#include <gfbgraph/gfbgraph-photo.h>
#include <gfbgraph/gfbgraph-user.h>
#include <gfbgraph/gfbgraph-simple-authorizer.h>

int main(void) {
    int passed = 0;

    GFBGraphAlbum *album = gfbgraph_album_new();
    if (album == NULL || !GFBGRAPH_IS_ALBUM(album)) {
        fprintf(stderr, "FAIL: album_new\n");
        return 1;
    }
    gfbgraph_album_set_name(album, "Vanilla Sky");
    printf("PASS: album_new + set_name\n");
    passed++;
    g_object_unref(album);

    GFBGraphNode *node = gfbgraph_node_new();
    if (node == NULL || !GFBGRAPH_IS_NODE(node)) {
        fprintf(stderr, "FAIL: node_new\n");
        return 1;
    }
    printf("PASS: node_new\n");
    passed++;
    g_object_unref(node);

    GFBGraphPhoto *photo = gfbgraph_photo_new();
    if (photo == NULL || !GFBGRAPH_IS_PHOTO(photo)) {
        fprintf(stderr, "FAIL: photo_new\n");
        return 1;
    }
    printf("PASS: photo_new\n");
    passed++;
    g_object_unref(photo);

    GFBGraphUser *user = gfbgraph_user_new();
    if (user == NULL || !GFBGRAPH_IS_USER(user)) {
        fprintf(stderr, "FAIL: user_new\n");
        return 1;
    }
    printf("PASS: user_new\n");
    passed++;
    g_object_unref(user);

    GFBGraphSimpleAuthorizer *auth =
        gfbgraph_simple_authorizer_new("test-access-token");
    if (auth == NULL || !GFBGRAPH_IS_SIMPLE_AUTHORIZER(auth)) {
        fprintf(stderr, "FAIL: simple_authorizer_new\n");
        return 1;
    }
    printf("PASS: simple_authorizer_new\n");
    passed++;
    g_object_unref(auth);

    printf("gfbgraph consumer checks passed: %d/5\n", passed);
    return passed == 5 ? 0 : 1;
}
