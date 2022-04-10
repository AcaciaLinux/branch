install:
	@echo "Creating branch-directory"
	@-mkdir -v /usr/share/branch/
	@echo "Copying files.."
	@-cp -v src/* /usr/share/branch
	@-cp -v branch /usr/bin/branch

