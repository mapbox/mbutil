#include <iostream>
#include <boost/program_options.hpp>
#include <boost/filesystem.hpp>
#include <boost/filesystem/fstream.hpp>
#include <boost/format.hpp>
#include "include/sqlite3.h"
#include "include/sqlite_types.hpp"

void disk_to_mbtiles(std::string input_filename, std::string output_filename)
{
    namespace fs = boost::filesystem;
    for (boost::filesystem::recursive_directory_iterator end,
        dir(input_filename); 
        dir != end; ++dir ) {
        if (fs::is_regular_file(*dir)) {
            std::cout << *dir << std::endl;                                    
        }
    }
}

void mbtiles_to_disk(std::string input_filename, std::string output_filename)
{
    namespace fs = boost::filesystem;
    sqlite_connection* dataset_ = new sqlite_connection(input_filename);

    std::ostringstream s;
    s << "SELECT zoom_level, tile_column, tile_row FROM tiles;";
    sqlite_resultset* rs (dataset_->execute_query (s.str()));

    while (rs->is_valid() && rs->step_next())
    {
        double z = rs->column_double(0);
        double x = rs->column_double(1);
        double y = rs->column_double(2);
        int size;
        const char* data = (const char *) rs->column_blob(3, size);
        fs::create_directories(str(boost::format("%s/%d/%d") %
            output_filename % z % x));
        fs::ofstream file(str(boost::format("%s/%d/%d/%d.png") %
            output_filename % z % x % y));
        file << data;
        file.close();
    }
}

int main(int ac, char** av)
{
    namespace po = boost::program_options;
    namespace fs = boost::filesystem;
    po::options_description desc("Allowed options");
    desc.add_options()
        ("input", po::value<std::string>(), "input file")
        ("output", po::value<std::string>(), "output file")
        ("help", "produce help message");
        

    po::variables_map vm;
    po::store(po::command_line_parser(ac, av).
            options(desc).run(), vm);

    po::notify(vm);

    if (vm.count("input") && vm.count("output"))
    {
        std::string input_filename = vm["input"].as<std::string>();
        std::string output_filename = vm["output"].as<std::string>();

        if (fs::is_regular_file(input_filename))
        {
            mbtiles_to_disk(input_filename, output_filename);
        }
        else if (fs::is_directory(input_filename))
        {
            disk_to_mbtiles(input_filename, output_filename);
        }
    }

    if (vm.count("help"))
    {
        std::cout << desc << "\n";
        return 1;
    }
    return 0;
}
