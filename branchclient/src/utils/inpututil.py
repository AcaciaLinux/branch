import blog

POSITIVE_ANSWERS = [ "", "y", "yes" ]

def ask_choice(question):
    blog.warn("{} (y/N)".format(question))
    
    user_resp = input()

    if(user_resp in POSITIVE_ANSWERS):
        return True
    else:
        return False

