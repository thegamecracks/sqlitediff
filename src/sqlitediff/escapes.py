import re
import textwrap

UNQUOTED_IDENTIFIER = re.compile(r"[a-z_]\w*", re.IGNORECASE)


def sql_identifier(s: str, *, as_needed: bool = False) -> str:
    if as_needed and UNQUOTED_IDENTIFIER.match(s):
        return s
    s = s.replace('"', '""')
    return f'"{s}"'


def sql_comment(s: str) -> str:
    return textwrap.indent(s, "-- ")
