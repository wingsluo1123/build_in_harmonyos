#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gfbgraph/gfbgraph.h>
#include <gfbgraph/gfbgraph-simple-authorizer.h>

static int checks;

static void expect(int cond, const char *name)
{
        if (!cond) {
                fprintf(stderr, "FAIL %s\n", name);
                exit(1);
        }
        checks++;
        printf("PASS %d %s\n", checks, name);
}

int main(void)
{
        GFBGraphNode *node;
        GFBGraphAlbum *album;
        GFBGraphPhoto *photo;
        GFBGraphUser *user;
        GFBGraphSimpleAuthorizer *auth;

        node = gfbgraph_node_new();
        expect(node != NULL && GFBGRAPH_IS_NODE(node), "node_new");
        gfbgraph_node_set_id(node, "offline-node");
        expect(g_strcmp0(gfbgraph_node_get_id(node), "offline-node") == 0, "node_id");

        album = gfbgraph_album_new();
        expect(album != NULL && GFBGRAPH_IS_ALBUM(album) && GFBGRAPH_IS_NODE(album), "album_new");
        gfbgraph_album_set_name(album, "Vanilla Sky");
        expect(g_strcmp0(gfbgraph_album_get_name(album), "Vanilla Sky") == 0, "album_name");
        gfbgraph_album_set_description(album, "offline description");
        expect(g_strcmp0(gfbgraph_album_get_description(album), "offline description") == 0,
               "album_description");
        expect(gfbgraph_album_get_count(album) == 0, "album_count");

        photo = gfbgraph_photo_new();
        expect(photo != NULL && GFBGRAPH_IS_PHOTO(photo), "photo_new");

        user = gfbgraph_user_new();
        expect(user != NULL && GFBGRAPH_IS_USER(user), "user_new");
        expect(gfbgraph_user_get_name(user) == NULL, "user_name_unset");

        auth = gfbgraph_simple_authorizer_new("offline-token");
        expect(auth != NULL && GFBGRAPH_IS_AUTHORIZER(auth), "simple_authorizer");

        g_object_unref(auth);
        g_object_unref(user);
        g_object_unref(photo);
        g_object_unref(album);
        g_object_unref(node);

        if (checks != 10) {
                fprintf(stderr, "FAIL count %d\n", checks);
                return 1;
        }
        printf("CONSUMER_RESULT %d/%d\n", checks, checks);
        return 0;
}
