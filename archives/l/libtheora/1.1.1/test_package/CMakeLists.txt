cmake_minimum_required(VERSION 3.10)
project(test_theora C)

find_package(libtheora REQUIRED)
find_package(Ogg REQUIRED)

add_executable(test_theora src/test_theora.c)
target_link_libraries(test_theora libtheora::libtheora Ogg::ogg)

# Workaround: libogg's CMakeDeps data has empty INCLUDE_DIRS.
# Use the package folder variable, handling both Release and Debug build types.
if(DEFINED libogg_PACKAGE_FOLDER_RELEASE)
    set(OGG_INCLUDE_DIR "${libogg_PACKAGE_FOLDER_RELEASE}/include")
elseif(DEFINED libogg_PACKAGE_FOLDER_DEBUG)
    set(OGG_INCLUDE_DIR "${libogg_PACKAGE_FOLDER_DEBUG}/include")
else()
    # Fallback: try all known suffixes
    foreach(suffix _RELEASE _DEBUG _RELWITHDEBINFO _MINSIZEREL)
        if(DEFINED "libogg_PACKAGE_FOLDER${suffix}")
            set(OGG_INCLUDE_DIR "${libogg_PACKAGE_FOLDER${suffix}}/include")
            break()
        endif()
    endforeach()
endif()
if(OGG_INCLUDE_DIR)
    target_include_directories(test_theora PRIVATE ${OGG_INCLUDE_DIR})
endif()
