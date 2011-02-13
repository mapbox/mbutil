build:
	clang++ mbutil.cpp -o mbutil -lboost_program_options-mt -lboost_system-mt -lboost_filesystem-mt  -lsqlite3 -I include
	./mbutil
