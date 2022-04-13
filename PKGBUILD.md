# PKGBUILD format
'branch' Package build file format

# Steps:
1. cwd, directory with .bpb file is [root]
2. create package_directory (normal branch_init: leafpkg and data dir)
3. create build_directory
4. fetch and extract [sources] to build_directory
5. run [build script]
6. done

# Branch Package Build - .bpb File format
```txt
name=package_name
version=package_version
source=src_link
dependencies=[a][b][c]
build={
	mkdir build
	
	cmake -mit-700-options --enable-monn=1 --target=monn_64

	make -j $(nproc)
	
	make install $PACKAGE_DATA_DIR



}

```

# Additional features?
1. Create repository for package builds
2. fetch package builds
3. ???
