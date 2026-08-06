# Load the debug and release variables
file(GLOB DATA_FILES "${CMAKE_CURRENT_LIST_DIR}/opencore-amrnb-*-data.cmake")

foreach(f ${DATA_FILES})
    include(${f})
endforeach()

# Create the targets for all the components
foreach(_COMPONENT ${opencore-amrnb_COMPONENT_NAMES} )
    if(NOT TARGET ${_COMPONENT})
        add_library(${_COMPONENT} INTERFACE IMPORTED)
        message(${opencore-amrnb_MESSAGE_MODE} "Conan: Component target declared '${_COMPONENT}'")
    endif()
endforeach()

if(NOT TARGET opencore-amrnb::opencore-amrnb)
    add_library(opencore-amrnb::opencore-amrnb INTERFACE IMPORTED)
    message(${opencore-amrnb_MESSAGE_MODE} "Conan: Target declared 'opencore-amrnb::opencore-amrnb'")
endif()
# Load the debug and release library finders
file(GLOB CONFIG_FILES "${CMAKE_CURRENT_LIST_DIR}/opencore-amrnb-Target-*.cmake")

foreach(f ${CONFIG_FILES})
    include(${f})
endforeach()