"""Checks shared by the statement tests: every statement must be one complete SQL statement"""

# Keywords a statement of this package may start with
_LEADING_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "CREATE", "DROP", "RENAME", "ALTER")


def statements_of(statements_class: type) -> dict[str, str]:
    """
    Collects every statement a statements class defines, the elements of a sequence included.

    :param statements_class: One of the Statements* classes
    :return: Statement text keyed by attribute name, "NAME[i]" for the i-th element of a tuple
    """
    collected: dict[str, str] = {}
    for name, value in vars(statements_class).items():
        if name.startswith("_"):
            continue
        if isinstance(value, tuple):
            for i, element in enumerate(value):
                collected["{0}[{1}]".format(name, i)] = element
        else:
            collected[name] = value
    return collected


def assert_complete_statement(name: str, text: str):
    """
    Asserts that *text* is a single, syntactically closed statement.

    QuestDB runs one statement per query, so a fragment (an open parenthesis, a clause without a
    leading keyword) fails at runtime only, on the first symbol it is used for.

    :param name: Attribute name, shown when the assertion fails
    :param text: Statement text, {placeholders} still in it
    """
    assert text.lstrip().upper().startswith(_LEADING_KEYWORDS), "{0} is a fragment: {1}".format(name, text)
    depth = 0
    for char in text.replace("{{", "").replace("}}", ""):
        depth += {"(": 1, ")": -1}.get(char, 0)
        assert depth >= 0, "{0} closes a parenthesis it never opened".format(name)
    assert depth == 0, "{0} leaves a parenthesis open".format(name)
    assert text.rstrip(";").count(";") == 0, "{0} holds more than one statement".format(name)
