branchlog:
	@echo "Installing required python dependencies.."
	cd branchlog && python3 setup.py bdist_wheel && python3 -m pip install dist/branchlog-1.0-py3-none-any.whl --force-reinstall
	cd branchcommons && python3 setup.py bdist_wheel && python3 -m pip install dist/branchcommons-1.0-py3-none-any.whl --force-reinstall
	cd branchweb && python3 setup.py bdist_wheel && python3 -m pip install dist/branchweb-1.0-py3-none-any.whl --force-reinstall
	cd pyleaf && python3 setup.py bdist_wheel && python3 -m pip install dist/pyleaf-1.0-py3-none-any.whl --force-reinstall
