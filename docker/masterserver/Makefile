all:
	cp -r ../../branchmaster ./branch/
	cp -r ../../submodules/branchlog ./branch/
	cp -r ../../submodules/branchcommons ./branch/
	docker build -t masterserver ./branch/
	rm -rf ./branch/branchmaster
	rm -rf ./branch/branchlog
	rm -rf ./branch/branchcommons

