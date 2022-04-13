def build():
    if not("package.bpb" in os.listdir(os.getcwd())):
        print("This package does not contain a package build file (package.bpb). Aborting.")
        exit(-1)

    print("package.bpb file found!")

