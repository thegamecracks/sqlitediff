import textwrap


def sql_comment(s: str) -> str:
    return textwrap.indent(s, "-- ")
