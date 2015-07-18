import re


def bold(string):
    return '**' + string + '**'


def italics(string):
    return '*' + string + '*'


def exponentiate(string):
    return '^(' + string + ')'


def quote(string):
    return "> " + string.replace("\n", "\n> ")


def escape(string):
    return re.sub(r"([\\\[\]\-(){}+_!.#`^>*])", r"\\\1", string)


def link(text, link):
    return "[" + text + "](" + link + ")"
