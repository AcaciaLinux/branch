install:
	@echo "Installing branch.."
	cp src/main.py /usr/bin/branch.py
	cp branch /usr/bin/branch
	chmod +x /usr/bin/branch

remove:
	@echo "Removing branch.."
	rm /usr/bin/branch.py
	rm /usr/bin/branch
