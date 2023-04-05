import blog

POSITIVE_ANSWERS = [ "", "y", "yes" ]

def ask_choice(question: str) -> bool:
    """
    Ask the user whether to proceed or not

    :param question: Question string
    """
    blog.warn(f"{question} (y/N)")
    user_resp = input()
    if(user_resp in POSITIVE_ANSWERS):
        return True

    return False
