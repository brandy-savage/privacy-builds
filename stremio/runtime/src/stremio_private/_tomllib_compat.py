"""Small TOML reader for the companion's deliberately limited config format.

This is used only on Python versions older than 3.11.  It supports the value
types present in config.example.toml: strings, numbers, booleans, arrays,
inline tables, and ordinary section headers.
"""

from __future__ import annotations

import ast
import re
from typing import Any


_INTEGER = re.compile(r"^[+-]?[0-9][0-9_]*$")
_FLOAT = re.compile(
    r"^[+-]?(?:[0-9][0-9_]*\.[0-9_]+|[0-9][0-9_]*[eE][+-]?[0-9_]+)$"
)


def _strip_comment(line: str) -> str:
    quote = ""
    escaped = False
    for index, char in enumerate(line):
        if quote:
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                quote = ""
            escaped = False
        elif char in {'"', "'"}:
            quote = char
        elif char == "#":
            return line[:index]
    return line


def _split_top_level(value: str) -> list[str]:
    parts: list[str] = []
    start = 0
    square = curly = 0
    quote = ""
    escaped = False
    for index, char in enumerate(value):
        if quote:
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                quote = ""
            escaped = False
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "[":
            square += 1
        elif char == "]":
            square -= 1
        elif char == "{":
            curly += 1
        elif char == "}":
            curly -= 1
        elif char == "," and square == 0 and curly == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    tail = value[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_value(value: str) -> Any:
    value = value.strip()
    if not value:
        raise ValueError("empty TOML value")
    if value[0] in {'"', "'"}:
        parsed = ast.literal_eval(value)
        if not isinstance(parsed, str):
            raise ValueError("invalid TOML string")
        return parsed
    if value == "true":
        return True
    if value == "false":
        return False
    if _INTEGER.fullmatch(value):
        return int(value.replace("_", ""))
    if _FLOAT.fullmatch(value):
        return float(value.replace("_", ""))
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [_parse_value(part) for part in _split_top_level(inner)]
    if value.startswith("{") and value.endswith("}"):
        result: dict[str, Any] = {}
        inner = value[1:-1].strip()
        for part in _split_top_level(inner):
            key, separator, raw = part.partition("=")
            if not separator or not key.strip():
                raise ValueError("invalid TOML inline table")
            result[key.strip()] = _parse_value(raw)
        return result
    raise ValueError(f"unsupported TOML value: {value!r}")


def _is_complete(value: str) -> bool:
    square = curly = 0
    quote = ""
    escaped = False
    for char in value:
        if quote:
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                quote = ""
            escaped = False
        elif char in {'"', "'"}:
            quote = char
        elif char == "[":
            square += 1
        elif char == "]":
            square -= 1
        elif char == "{":
            curly += 1
        elif char == "}":
            curly -= 1
    return not quote and square == 0 and curly == 0


def loads(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current = root
    lines = iter(enumerate(text.splitlines(), start=1))
    for line_number, source in lines:
        line = _strip_comment(source).strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = root
            for segment in line[1:-1].split("."):
                name = segment.strip()
                if not name:
                    raise ValueError(f"invalid TOML section on line {line_number}")
                current = current.setdefault(name, {})
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"invalid TOML assignment on line {line_number}")
        while not _is_complete(value):
            try:
                _, continuation = next(lines)
            except StopIteration as exc:
                raise ValueError(f"unterminated TOML value on line {line_number}") from exc
            value += "\n" + _strip_comment(continuation).strip()
        current[key.strip()] = _parse_value(value)
    return root
