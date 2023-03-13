install: install_submodules install_client install_buildbot install_master

install_submodules:
	@echo "Installing submodules..."
	make -C submodules branchlog

install_client:
	@echo "Installing client..."
	make -C branchclient

install_buildbot:
	@echo "Installing buildbot..."
	make -C branchbuildbot

install_master:
	@echo "Installing master..."
	make -C branchmaster
