"""A tokenizer and reader for the s-expression syntax PDDL is written in.

PDDL is Lisp without the evaluation, so one small reader handles domains,
problems and plans alike. Written out rather than pulled from a PDDL library
because the point of this repository is what the model says, and a parser you
did not write is a layer between you and that.
"""

from __future__ import annotations

from dataclasses import dataclass

from pddl.errors import ParseError

Sexpr = str | list["Sexpr"]


@dataclass(frozen=True, slots=True)
class Token:
    text: str
    line: int


def tokenize(text: str) -> list[Token]:
    """Split into tokens, dropping comments and tracking line numbers.

    `;` starts a comment that runs to the end of the line — including inside
    the plan files, where the makespan is written as a trailing comment. Line
    numbers are carried on every token so a malformed domain reports where it
    broke rather than just that it did.
    """

    tokens: list[Token] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.split(";", 1)[0]
        for raw in line.replace("(", " ( ").replace(")", " ) ").split():
            tokens.append(Token(raw, line_number))
    return tokens


def parse(text: str) -> list[Sexpr]:
    """Read every top-level form in `text`."""
    tokens = tokenize(text)
    forms: list[Sexpr] = []
    position = 0
    while position < len(tokens):
        form, position = _read(tokens, position)
        forms.append(form)
    return forms


def parse_one(text: str) -> Sexpr:
    """Read exactly one top-level form, rejecting trailing junk.

    A domain file containing two `(define ...)` forms is a mistake worth
    catching: the second one would otherwise be silently ignored.
    """
    forms = parse(text)
    if len(forms) != 1:
        raise ParseError(f"expected exactly one top-level form, found {len(forms)}")
    return forms[0]


def _read(tokens: list[Token], position: int) -> tuple[Sexpr, int]:
    if position >= len(tokens):
        raise ParseError("unexpected end of input")

    token = tokens[position]
    if token.text == ")":
        raise ParseError(f"unexpected ')' on line {token.line}")
    if token.text != "(":
        # Symbols are case-insensitive in PDDL; normalising here means nothing
        # downstream has to remember that `ROVER0` and `rover0` are the same
        # object — a comparison that silently fails rather than raising.
        return token.text.lower(), position + 1

    items: list[Sexpr] = []
    position += 1
    while True:
        if position >= len(tokens):
            raise ParseError(f"unclosed '(' opened on line {token.line}")
        if tokens[position].text == ")":
            return items, position + 1
        item, position = _read(tokens, position)
        items.append(item)


def find(form: Sexpr, keyword: str) -> Sexpr | None:
    """Return the body of the first `(:keyword ...)` section of `form`."""
    if not isinstance(form, list):
        return None
    for item in form:
        if isinstance(item, list) and item and item[0] == keyword:
            return item
    return None


def head(form: Sexpr) -> str:
    """The symbol at the head of a form, for error messages."""
    if isinstance(form, str):
        return form
    if form and isinstance(form[0], str):
        return form[0]
    return "<list>"
