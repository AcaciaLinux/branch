all:
	cp -r ../../branchmaster ./branch/
	cp -r ../../submodules/branchlog ./branch/
	cp -r ../../submodules/branchcommons ./branch/
	
	docker-compose build 
	
	rm -rf ./branch/branchmaster
	rm -rf ./branch/branchlog
	rm -rf ./branch/branchcommons

