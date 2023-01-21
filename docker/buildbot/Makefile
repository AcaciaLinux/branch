all:
	cp -r ../../branchbuildbot ./branch/
	cp -r ../../submodules/branchlog ./branch/
	cp -r ../../submodules/branchcommons ./branch/
	cp -r ../../submodules/pyleaf ./branch/
	docker build -t buildbot ./branch/
	rm -rf ./branch/branchbuildbot
	rm -rf ./branch/branchlog
	rm -rf ./branch/branchcommons
	rm -rf ./branch/pyleaf

