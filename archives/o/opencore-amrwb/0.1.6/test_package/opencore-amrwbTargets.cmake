# Load the debug and release variables
file(GLOB DATA_FILES "${CMAKE_CURRENT_LIST_DIR}/opencore-amrwb-*-data.cmake")

foreach(f ${DATA_FILES})
    include(${f})
endforeach()

# Create the targets for all the components
foreach(_COMPONENT ${opencore-amrwb_COMPONENT_NAMES} )
    if(NOT TARGET ${_COMPONENT})
        add_library(${_COMPONENT} INTERFACE IMPORTED)
        message(${opencore-amrwb_MESSAGE_MODE} "Conan: Component target declared '${_COMPONENT}'")
    endif()
endforeach()

if(NOT TARGET opencore_amrwb::opencore_amrwb)
    add_library(opencore_amrwb::opencore_amrwb INTERFACE IMPORTED)
    message(${opencore-amrwb_MESSAGE_MODE} "Conan: Target declared 'opencore_amrwb::opencore_amrwb'")
endif()
# Load the debug and release library finders
file(GLOB CONFIG_FILES "${CMAKE_CURRENT_LIST_DIR}/opencore-amrwb-Target-*.cmake")

foreach(f ${CONFIG_FILES})
    include(${f})
endforeach()