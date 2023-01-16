install:
	@echo "Installing dependencies.."
	make -C submodules branchlog
	@echo "Installing client, buildbot, master.."
	make -C branchbuildbot
	make -C branchclient
	make -C branchmaster
