CMAKE_MINIMUM_REQUIRED(VERSION 2.6)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")

PROJECT(mbutil)

ADD_DEFINITIONS(-g -O2 -Wall -W -Werror -lsqlite3)
SET(CMAKE_EXE_LINKER_FLAGS "-undefined dynamic_lookup")
ADD_EXECUTABLE(mbutil mbutil.cpp)

FIND_PACKAGE(Boost REQUIRED COMPONENTS system program_options filesystem regex)
FIND_PACKAGE(Sqlite3 REQUIRED)

link_directories(
    ${Boost_LIBRARY_DIRS}
    ${SQLITE_LIBRARIES}
    )
include_directories(
    ${Boost_INCLUDE_DIRS}
    include)

target_link_libraries (
    mbutil
    ${SQLITE_LIBRARIES}
    ${Boost_LIBRARIES}
    )
