install:
	@echo "Installing client, buildbot, master.."
	make -C branchbuildbot
	make -C branchclient
	make -C branchmaster
