install:
	@echo "Creating branch-directory"
	mkdir /usr/share/branch/
	@echo "Copying files.."
	cp src/* /usr/share/branch
	cp branch /usr/bin/branch

