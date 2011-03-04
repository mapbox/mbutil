CMAKE_MINIMUM_REQUIRED(VERSION 2.6)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")

PROJECT(mbutil)

ADD_DEFINITIONS(-g -O2 -Wall -W -Werror -lsqlite3)
ADD_EXECUTABLE(mbutil mbutil.cpp)

FIND_PACKAGE(Boost REQUIRED COMPONENTS system program_options filesystem regex)

link_directories(
    ${Boost_LIBRARY_DIRS}
    )
include_directories(
    ${Boost_INCLUDE_DIRS}
    include)

target_link_libraries (
    mbutil
    ${Boost_LIBRARIES}
    )
