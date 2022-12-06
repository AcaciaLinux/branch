def assert_instance_of(a, b):
    if(a is b):
        return True
    else:
        print("Assertion failure. Test failed.")
        exit(-1)

def assert_not_instance_of():
    if(a is not b):
        return True
    else:
        print("Assertion failure. Test failed.")
        exit(-1)

def assert_equals():
    if(a == b):
        return True
    else:
        print("Assertion failure. Test failed.")
        exit(-1)


def assert_not_equals():
    if(a != b):
        return True
    else:
        print("Assertion failure. Test failed.")
        exit(-1)
