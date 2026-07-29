#include <stdio.h>
#include <ktx.h>

int main(void) {
    /* Verify library links and basic API works */
    printf("KTX error string for KTX_SUCCESS: %s\n", ktxErrorString(KTX_SUCCESS));
    printf("KTX error string for KTX_INVALID_VALUE: %s\n", ktxErrorString(KTX_INVALID_VALUE));

    /* Create a KTX2 texture with VK_FORMAT_R8G8B8A8_UNORM (=37) */
    ktxTextureCreateInfo createInfo = {
        .glInternalformat = 0,
        .vkFormat = 37,
        .baseWidth = 64,
        .baseHeight = 64,
        .baseDepth = 0,
        .numDimensions = 2,
        .numLevels = 1,
        .numLayers = 1,
        .numFaces = 1,
        .isArray = KTX_FALSE,
        .generateMipmaps = KTX_FALSE,
    };

    ktxTexture2* texture = NULL;
    KTX_error_code result = ktxTexture2_Create(&createInfo,
                                                KTX_TEXTURE_CREATE_ALLOC_STORAGE,
                                                &texture);
    if (result == KTX_SUCCESS && texture) {
        printf("Created KTX2 texture: %ux%u\n", texture->baseWidth, texture->baseHeight);
        ktxTexture_Destroy(ktxTexture(texture));
        printf("Destroyed KTX texture\n");
    } else {
        printf("ktxTexture2_Create returned: %d (%s)\n", (int)result, ktxErrorString(result));
    }

    printf("KTX test passed!\n");
    return 0;
}
