
def condo_short_name(name):
    """
    Takes a Condo's full legal name and shortens it to a nickname
    """
    words = name.split(" ")
    initials = ".".join(word[0] for index, word in enumerate(words) if index < len(words) - 1)
    return initials + ". {}".format(words[-1])
