# Project the actual packaged feature header for FindHDF5 consumers. This is
# not an unconditional claim that a serial HDF5 library supports MPI.
file(READ "${CMAKE_CURRENT_LIST_DIR}/../../include/H5pubconf.h" _hdf5_actual_features)
if(NOT _hdf5_actual_features MATCHES "#[ \t]*define[ \t]+H5_HAVE_PARALLEL[ \t]+1")
  message(FATAL_ERROR "The packaged HDF5 feature header does not expose parallel support")
endif()
set(HDF5_IS_PARALLEL TRUE)
set(HDF5_PROVIDES_PARALLEL TRUE)
set(HDF5_ENABLE_PARALLEL TRUE)
set(HDF5_C_FOUND TRUE)
set(HDF5_LIBRARIES hdf5-static)
set(HDF5_C_LIBRARIES hdf5-static)
set(HDF5_HL_LIBRARIES hdf5_hl-static)
unset(_hdf5_actual_features)
