# Load the debug and release variables
file(GLOB DATA_FILES "${CMAKE_CURRENT_LIST_DIR}/qt-libiodbc-*-data.cmake")

foreach(f ${DATA_FILES})
    include(${f})
endforeach()

# Create the targets for all the components
foreach(_COMPONENT ${qt-libiodbc_COMPONENT_NAMES} )
    if(NOT TARGET ${_COMPONENT})
        add_library(${_COMPONENT} INTERFACE IMPORTED)
        message(${qt-libiodbc_MESSAGE_MODE} "Conan: Component target declared '${_COMPONENT}'")
    endif()
endforeach()

if(NOT TARGET qt-libiodbc::qt-libiodbc)
    add_library(qt-libiodbc::qt-libiodbc INTERFACE IMPORTED)
    message(${qt-libiodbc_MESSAGE_MODE} "Conan: Target declared 'qt-libiodbc::qt-libiodbc'")
endif()
# Load the debug and release library finders
file(GLOB CONFIG_FILES "${CMAKE_CURRENT_LIST_DIR}/qt-libiodbc-Target-*.cmake")

foreach(f ${CONFIG_FILES})
    include(${f})
endforeach()