# This Makefile implements common tasks needed by developers
# A list of implemented rules can be obtained by the command "make help"

# timeout (in seconds) for all test cases
TIMEOUT=600

# get the pySecDec version number
PYSECDECVERSION=$(shell python -c 'import pySecDec; print(pySecDec.__version__)')

# Auto detect nvcc
ifeq ($(CXX), nvcc)
SECDEC_WITH_CUDA = 1
endif


.DEFAULT_GOAL=check
.PHONY .SILENT : help
help :
	echo
	echo "    Implemented targets:"
	echo
	echo "    check        use nosetests to test with python 2.7 and 3,"
	echo "                 run doctest using Sphinx, run the tests of the"
	echo "                 SecDecUtil package, and run all examples with"
	echo "                 python 2 and 3"
	echo "    checkX       use nosetests to test with python 2.7 or 3,"
	echo "                 where X is one of {2,3}"
	echo "    active-check use nosetests to run only tests marked as"
	echo "                 \"active\" using nosetests-2.7 and nosetests3"
	echo "    fast-check   use nosetests to run only quick tests"
	echo "                 using nosetests-2.7 and nosetests3"
	echo "    util-check   run the tests of the SecDecUtil package"
	echo "    doctest      run doctest using Sphinx"
	echo "    dist         create a tarball to be distributed"
	echo "    thin-dist    create a tarball excluding the documentation"
	echo "                 and the examples"
	echo "    clean        delete compiled and temporary files"
	echo "    coverage     produce and show a code coverage report"
	echo "    doc          run \"doc-html\" and \"doc-pdf\""
	echo "    doc-html     build the html documentation using sphinx"
	echo "    doc-pdf      build the pdf documentation using sphinx"
	echo "    help         show this message"
	echo "    high-level   run the high level tests"
	echo "    show-todos   show todo marks in the source code"
	echo

.PHONY : clean
clean:
	# remove build doc
	$(MAKE) -C ./doc clean

	# clean high level tests
	$(MAKE) -C ./high_level_tests clean

	# remove cpp doctests
	$(MAKE) -C ./doc/source/cpp_doctest clean

	# clean util
	if [ -f util/Makefile ] ; then $(MAKE) -C ./util clean ; fi

	# remove .pyc files created by python 2.7
	rm -f ./*.pyc
	find -P . -name '*.pyc' -delete

	# remove .pyc files created by python 3
	rm -rf ./__pycache__
	find -P . -name __pycache__ -delete

	# remove backup files
	find -P . -name '*~' -delete

	# remove Mac .DS_store files
	find -P . -name '.DS_Store' -delete

	# remove files created by coverage
	rm -f .coverage
	rm -rf coverage

	# remove egg-info
	rm -rf pySecDec.egg-info

	# remove build/ und dist/
	rm -rf build/ dist/

	# remove tarball and the directory it is created from
	rm -rf pySecDec-$(PYSECDECVERSION)/ pySecDec-$(PYSECDECVERSION).tar.gz

	# remove the SecDecUtil tarball
	rm -f util/secdecutil-*.tar.gz

.PHONY : check
check : check2 check3 doctest util-check

.PHONY : check2
check2 :
	@ # run tests
	nosetests-2.7 --processes=-1 --process-timeout=$(TIMEOUT)

.PHONY : check3
check3 :
	@ # run tests
	nosetests3 --processes=-1 --process-timeout=$(TIMEOUT)

.PHONY : active-check
active-check :
	nosetests-2.7 -a 'active' --processes=-1 --process-timeout=$(TIMEOUT)
	nosetests3    -a 'active' --processes=-1 --process-timeout=$(TIMEOUT)

.PHONY : fast-check
fast-check :
	nosetests-2.7 -a '!slow' --processes=-1 --process-timeout=$(TIMEOUT)
	nosetests3    -a '!slow' --processes=-1 --process-timeout=$(TIMEOUT)

.PHONY : util-check
util-check :
	export SECDEC_WITH_CUDA=$(SECDEC_WITH_CUDA) && \
	cd util && \
	if [ -f Makefile ] ; \
	then \
		$(MAKE) check ; \
	else \
		autoreconf -i && \
		./configure --prefix=`pwd` && \
		$(MAKE) check ; \
	fi

.PHONY : doc
doc : doc-html doc-pdf

.PHONY : doc-html
doc-html :
	$(MAKE) -C doc html

.PHONY : doc-pdf
doc-pdf :
	$(MAKE) -C doc latexpdf

.PHONY : doctest
doctest :
	$(MAKE) -C doc doctest

.PHONY : high-level
high-level :
	# '$(MAKE) -C high_level_tests summarize' forwards the error if an example fails
	# 'exit 1' forwards the error out of the shell's for loop
	export DIRNAME=high_level_tests ; \
	for PYTHON in python2 python3 ; do \
		PYTHON=$$PYTHON $(MAKE) -C $$DIRNAME && $(MAKE) -C $$DIRNAME summarize || exit 1 \
	; \
	done

.PHONY : dist
# clean first to avoid having `.pyc` files in the dist
thin-dist : clean
	# create pySecDec dist
	python setup.py sdist

	# create SecDecUtil dist
	cd util && \
	if [ -f Makefile ] ; \
	then \
		$(MAKE) dist ; \
	else \
		autoreconf -i && \
		./configure --prefix=`pwd` && \
		$(MAKE) dist ; \
	fi

	# create dist directory tree
	mkdir pySecDec-$(PYSECDECVERSION)/
	cp dist_template/* pySecDec-$(PYSECDECVERSION)/
	cp dist/*.tar.gz pySecDec-$(PYSECDECVERSION)/
	cp util/*.tar.gz pySecDec-$(PYSECDECVERSION)/

	# copy the changelog
	cp ChangeLog pySecDec-$(PYSECDECVERSION)

	# create tarball
	tar -czf pySecDec-$(PYSECDECVERSION).tar.gz pySecDec-$(PYSECDECVERSION)/

# clean first to avoid having `.pyc` files in the dist
dist : clean
	# create pySecDec dist
	python setup.py sdist

	# create SecDecUtil dist
	cd util && \
	if [ -f Makefile ] ; \
	then \
		$(MAKE) dist ; \
	else \
		autoreconf -i && \
		./configure --prefix=`pwd` && \
		$(MAKE) dist ; \
	fi

	# create dist directory tree
	mkdir pySecDec-$(PYSECDECVERSION)/
	cp dist_template/* pySecDec-$(PYSECDECVERSION)/
	cp dist/*.tar.gz pySecDec-$(PYSECDECVERSION)/
	cp util/*.tar.gz pySecDec-$(PYSECDECVERSION)/

	# build and copy the documentation
	$(MAKE) doc
	mkdir pySecDec-$(PYSECDECVERSION)/doc
	cp doc/build/latex/pySecDec.pdf pySecDec-$(PYSECDECVERSION)/doc
	cp -r doc/build/html pySecDec-$(PYSECDECVERSION)/doc

	# copy the examples
	cp -r examples pySecDec-$(PYSECDECVERSION)/examples

	# copy the changelog
	cp ChangeLog pySecDec-$(PYSECDECVERSION)

	# create tarball
	tar -czf pySecDec-$(PYSECDECVERSION).tar.gz pySecDec-$(PYSECDECVERSION)/

.SILENT .PHONY : show-todos
grep_cmd  = grep -riG [^"au""sphinx.ext."]todo --color=auto --exclude=Makefile --exclude-dir=.git --exclude=catch.hpp
begin_red = "\033[0;31m"
end_red   = "\033[0m"
show-todos :
	# suppress errors here
	# note that no todo found is considered as error
	$(grep_cmd) . ; \
	echo ; 	echo ; \
	echo -e $(begin_red)"*******************************************************************"$(end_red) ; \
	echo -e $(begin_red)"* The following files and directories are NOT searched for TODOs: *"$(end_red) ; \
	echo -e $(begin_red)"* o makefiles                                                     *"$(end_red) ; \
	echo -e $(begin_red)"* o files named 'catch.hpp'                                       *"$(end_red) ; \
	echo -e $(begin_red)"* o .git directories                                              *"$(end_red) ; \
	echo -e $(begin_red)"*******************************************************************"$(end_red) ; \
	echo

.PHONY : coverage
coverage :
	rm -rf coverage
	nosetests --with-coverage --cover-package=pySecDec --cover-html --cover-html-dir=coverage
	xdg-open coverage/index.html
