SECTOR%(sector_index)i_CPP = \
	%(sector_cpp_files)s
SECTOR_CPP += $(SECTOR%(sector_index)i_CPP)

$(SECTOR%(sector_index)i_CPP) $(patsubst %%.cpp,%%.hpp,$(filter src/%%,$(SECTOR%(sector_index)i_CPP))) : codegen/sector%(sector_index)i.done ;
