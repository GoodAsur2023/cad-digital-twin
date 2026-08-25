# External Data
include(ExternalData)
# Putting in the same URL to ensure bad connections retry a few times
set(ExternalData_URL_TEMPLATES "https://data.kitware.com/api/v1/file/hashsum/%(algo)/%(hash)/download"
                               "https://data.kitware.com/api/v1/file/hashsum/%(algo)/%(hash)/download"
                               "https://data.kitware.com/api/v1/file/hashsum/%(algo)/%(hash)/download")

message(STATUS "Looking for zip shas")
file(GLOB_RECURSE _VERIFICATION_SHA RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} "*.sha512")

foreach(_SHA_FILE ${_VERIFICATION_SHA})
  string(REGEX MATCH "^(.*)\\.[^.]*$" dummy ${_SHA_FILE})
  set(SHA_FILE_WITHOUT_EXT ${CMAKE_MATCH_1})
  list(APPEND _VERIFICATION_ZIP ${SHA_FILE_WITHOUT_EXT})
endforeach()

foreach(_ZIP_FILE ${_VERIFICATION_ZIP})
  #message(STATUS "Zip ${_ZIP_FILE}")
  ExternalData_Add_Test(ExternalData
    NAME ${_ZIP_FILE}
    COMMAND 
    DATA{${_ZIP_FILE}}
  )
endforeach()
ExternalData_Add_Target(ExternalData)
set(ExternalData_LINK_CONTENT SHA512)
set(ExternalData_TIMEOUT_ABSOLUTE 300)
set(ExternalData_TIMEOUT_INACTIVITY 150)

set(INC_DOWNLOAD)
if(PULSE_DOWNLOAD_BASELINES)
  set(INC_DOWNLOAD ALL)
else()
  set_target_properties(ExternalData PROPERTIES EXCLUDE_FROM_ALL 1 EXCLUDE_FROM_DEFAULT_BUILD 1)
endif()

add_custom_target(UpdateVerification ${INC_DOWNLOAD})
add_dependencies(UpdateVerification ExternalData)
add_custom_command(TARGET UpdateVerification POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory   ${CMAKE_INSTALL_PREFIX}/bin/verification)
foreach(_ZIP_FILE ${_VERIFICATION_ZIP})
add_custom_command(TARGET UpdateVerification POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo "Unzipping ${_ZIP_FILE} "
    COMMAND ${CMAKE_COMMAND} -E tar xzf ${CMAKE_BINARY_DIR}/data/${_ZIP_FILE} 
            WORKING_DIRECTORY ${CMAKE_INSTALL_PREFIX}/bin/verification)
endforeach()

set_target_properties (ExternalData PROPERTIES FOLDER ${PROJECT_NAME})
set_target_properties (UpdateVerification PROPERTIES FOLDER ${PROJECT_NAME})
