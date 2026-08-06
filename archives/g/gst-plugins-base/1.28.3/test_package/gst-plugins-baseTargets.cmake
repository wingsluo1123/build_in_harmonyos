# Load the debug and release variables
file(GLOB DATA_FILES "${CMAKE_CURRENT_LIST_DIR}/gst-plugins-base-*-data.cmake")

foreach(f ${DATA_FILES})
    include(${f})
endforeach()

# Create the targets for all the components
foreach(_COMPONENT ${gst-plugins-base_COMPONENT_NAMES} )
    if(NOT TARGET ${_COMPONENT})
        add_library(${_COMPONENT} INTERFACE IMPORTED)
        message(${gst-plugins-base_MESSAGE_MODE} "Conan: Component target declared '${_COMPONENT}'")
    endif()
endforeach()

if(NOT TARGET gst-plugins-base::gst-plugins-base)
    add_library(gst-plugins-base::gst-plugins-base INTERFACE IMPORTED)
    message(${gst-plugins-base_MESSAGE_MODE} "Conan: Target declared 'gst-plugins-base::gst-plugins-base'")
endif()
# Load the debug and release library finders
file(GLOB CONFIG_FILES "${CMAKE_CURRENT_LIST_DIR}/gst-plugins-base-Target-*.cmake")

foreach(f ${CONFIG_FILES})
    include(${f})
endforeach()