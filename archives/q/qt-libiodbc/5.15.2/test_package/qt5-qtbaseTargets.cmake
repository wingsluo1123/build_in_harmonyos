# Load the debug and release variables
file(GLOB DATA_FILES "${CMAKE_CURRENT_LIST_DIR}/qt5-qtbase-*-data.cmake")

foreach(f ${DATA_FILES})
    include(${f})
endforeach()

# Create the targets for all the components
foreach(_COMPONENT ${qt5-qtbase_COMPONENT_NAMES} )
    if(NOT TARGET ${_COMPONENT})
        add_library(${_COMPONENT} INTERFACE IMPORTED)
        message(${qt5-qtbase_MESSAGE_MODE} "Conan: Component target declared '${_COMPONENT}'")
    endif()
endforeach()

if(NOT TARGET qt5-qtbase::qt5-qtbase)
    add_library(qt5-qtbase::qt5-qtbase INTERFACE IMPORTED)
    message(${qt5-qtbase_MESSAGE_MODE} "Conan: Target declared 'qt5-qtbase::qt5-qtbase'")
endif()
# Load the debug and release library finders
file(GLOB CONFIG_FILES "${CMAKE_CURRENT_LIST_DIR}/qt5-qtbase-Target-*.cmake")

foreach(f ${CONFIG_FILES})
    include(${f})
endforeach()