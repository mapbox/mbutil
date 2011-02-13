build:
	clang++ mbutil.cpp -o mbutil -lboost_program_options-mt
	./mbutil