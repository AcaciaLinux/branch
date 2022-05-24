install:
	@echo "Install dependencies with py-pip"
	@-python3 -m pip install requests pysftp
	@echo "Creating branch-directory"
	@-mkdir -v /usr/share/branch/
	@echo "Copying files.."
	@-cp -rv src/* /usr/share/branch
	@-cp -v branch /usr/bin/branch

install-pkg:
	@echo "Installing to pkg"
	@-mkdir -vp $(DESTDIR)/usr/share/branch
	@-mkdir -vp $(DESTDIR)/usr/bin/
	@echo "Copying files"
	@-cp -rv src/* $(DESTDIR)/usr/share/branch
	@-cp -v branch $(DESTDIR)/usr/bin/branch
