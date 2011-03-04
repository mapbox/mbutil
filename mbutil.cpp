#include <boost/program_options.hpp>
#include <boost/filesystem.hpp>
#include <boost/filesystem/fstream.hpp>
#include <boost/format.hpp>
#include <boost/regex.hpp>
#include <boost/property_tree/json_parser.hpp>
#include <boost/foreach.hpp>
#include <iostream>
#include <sqlite3.h>
#include "include/sqlite_types.hpp"

void setup_mbtiles(std::string filename) {
    char* zErrMsg;
    namespace fs = boost::filesystem;
    sqlite3 *db;
    sqlite3_open(filename.c_str(), &db);
    sqlite3_exec(db, "create table tiles (zoom_level integer, tile_column "
    "integer, tile_row integer, tile_data blob); create table metadata "
    "(name text, value text); create unique index name on metadata (name);"
    "create unique index tile_index on tiles "
    "(zoom_level, tile_column, tile_row);",
    NULL, 0, &zErrMsg);
    sqlite3_close(db);
}

void add_metadata(sqlite3* db, std::string k, std::string v) {
    static sqlite3_stmt *insert_statement;
    std::string s = "INSERT INTO metadata (name, value) "
        " VALUES (?1, ?2);";
    sqlite3_prepare_v2(db, s.c_str(), -1, &insert_statement, 0);

    sqlite3_bind_text(insert_statement, 1, k.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(insert_statement, 2, v.c_str(), -1, SQLITE_STATIC);

    sqlite3_step(insert_statement);
    sqlite3_reset(insert_statement);
    sqlite3_clear_bindings(insert_statement);
}

void disk_to_mbtiles(std::string input_filename, std::string output_filename) {
    namespace fs = boost::filesystem;
    double fsize;
    sqlite3 *db;
    sqlite3_open(output_filename.c_str(), &db);
    static sqlite3_stmt *insert_statement;
    std::string s = "INSERT INTO tiles "
        "(zoom_level, tile_column, tile_row, tile_data) "
        " VALUES (?1, ?2, ?3, ?4);";

    sqlite3_prepare_v2(db, s.c_str(), -1, &insert_statement, 0);

    if (!fs::is_regular_file(output_filename)) {
        setup_mbtiles(output_filename);
    }

    std::string metadata_location = str(boost::format("%s/metadata.json") %
            input_filename);

    if (fs::is_regular_file(metadata_location)) {
        boost::property_tree::ptree pt;
        boost::property_tree::read_json(metadata_location, pt);
        std::set<std::string> metadata_entries;

        BOOST_FOREACH(boost::property_tree::ptree::value_type &v,
                pt.get_child("metadata"))
            add_metadata(db, v.first.data(), v.second.data());
        
    } else {
        std::cerr << "metadata.json not found\n";
    }

    // TODO(tmcw) weak regex.
    static const boost::regex e("(\\w+)\\/(\\d+)\\/(\\d+)\\/(\\d+)\\.png");
    for (boost::filesystem::recursive_directory_iterator end,
        dir(input_filename);
        dir != end; ++dir ) {
        if (fs::is_regular_file(*dir)) {
            boost::smatch what;
            if (boost::regex_match((*dir).string(),
                what,
                e,
                boost::match_any)) {
                fsize = fs::file_size(*dir);
                char* data = (char*) malloc(sizeof(char) * fsize);
                fs::ifstream f(*dir);
                while (!f.eof()) {
                    f >> data;
                }
                f.close();

                int z = atoi(what[1].str().c_str());
                int x = atoi(what[3].str().c_str());
                int y = atoi(what[4].str().c_str());

                sqlite3_bind_int(insert_statement, 1, z);
                sqlite3_bind_int(insert_statement, 2, x);
                sqlite3_bind_int(insert_statement, 3, y);
                sqlite3_bind_blob(insert_statement, 4, data,
                  fsize, SQLITE_TRANSIENT);
                sqlite3_step(insert_statement);
                sqlite3_reset(insert_statement);
                sqlite3_clear_bindings(insert_statement);
                free(data);
            } else {
                std::cout << "no match\n";
                std::cout << (*dir).string() << "\n";
            }
        }
    }
    sqlite3_finalize(insert_statement);
    sqlite3_close(db);
}

void mbtiles_to_disk(std::string input_filename, std::string output_filename) {
    namespace fs = boost::filesystem;
    sqlite_connection* dataset_ = new sqlite_connection(input_filename);

    std::ostringstream s;
    s << "SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles;";
    sqlite_resultset* rs(dataset_->execute_query(s.str()));

    while (rs->is_valid() && rs->step_next()) {
        double z = rs->column_double(0);
        double x = rs->column_double(1);
        double y = rs->column_double(2);
        int size;
        std::ostringstream data;
        std::string image_data;
        char* addr = (char*) rs->column_blob(3, size);
        memcpy(&image_data, addr, size);
        fs::create_directories(str(boost::format("%s/%d/%d") %
            output_filename % z % x));
        fs::ofstream file(str(boost::format("%s/%d/%d/%d.png") %
            output_filename % z % x % y));
        file << image_data;
        file.close();
    }

    std::string metadata_location = str(boost::format("%s/metadata.json") %
            output_filename);

    boost::property_tree::ptree pt;
    std::ostringstream mq;
    mq << "SELECT name, value FROM metadata;";
    sqlite_resultset* ms (dataset_->execute_query (mq.str()));
    while (ms->is_valid() && ms->step_next()) {
        std::string k = ms->column_text(0);
        std::string v = ms->column_text(1);
        pt.put(str(boost::format("metadata.%s") % k), v);
    }
    boost::property_tree::write_json(metadata_location, pt);
}

int main(int ac, char** av) {
    namespace po = boost::program_options;
    namespace fs = boost::filesystem;
    po::options_description desc("Allowed options");
    desc.add_options()
        ("input", po::value<std::string>(), "input file")
        ("output", po::value<std::string>(), "output file")
        ("m", po::value<std::string>(), "metadata")
        ("help", "produce help message");

    po::variables_map vm;
    po::store(po::command_line_parser(ac, av).
            options(desc).run(), vm);

    po::notify(vm);

    if (vm.count("input") && vm.count("output")) {
        std::string input_filename = vm["input"].as<std::string>();
        std::string output_filename = vm["output"].as<std::string>();

        if (fs::is_regular_file(input_filename)) {
            mbtiles_to_disk(input_filename, output_filename);
        } else if (fs::is_directory(input_filename)) {
            disk_to_mbtiles(input_filename, output_filename);
        }
    }

    if (vm.count("help")) {
        std::cout << desc << "\n";
        return 1;
    }
    return 0;
}
