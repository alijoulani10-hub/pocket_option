from __future__ import annotations

import typing
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Q:
    @classmethod
    def field(
        cls,
        name: str,
        op: typing.Literal["eq", "neq", "gt", "gte", "lt", "lte", "isnull"],
        value: typing.Any,
    ) -> Field:
        return Field(name, op, value)

    def __and__(self, other: Q) -> Q:
        return And(self, other)

    def __or__(self, other: Q) -> Q:
        return Or(self, other)

    def __invert__(self) -> Q:
        return Not(self)


@dataclass(frozen=True, slots=True)
class Field(Q):
    name: str
    op: typing.Literal[
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "isnull",
    ]
    value: typing.Any


@dataclass(frozen=True, slots=True)
class And(Q):
    left: Q
    right: Q


@dataclass(frozen=True, slots=True)
class Or(Q):
    left: Q
    right: Q


@dataclass(frozen=True, slots=True)
class Not(Q):
    expression: Q


class QEvaluator(typing.Protocol):
    async def evaluate(self, query: Q, obj: typing.Any) -> bool: ...


class QTranslator(typing.Protocol):
    async def translate(self, query: Q) -> bool: ...


class PythonQEvaluator:
    def evaluate(self, query: Q, obj: typing.Any) -> bool:  # noqa: PLR0911
        match query:
            case Field(name, op, value):
                actual = getattr(obj, name)

                match op:
                    case "eq":
                        return actual == value
                    case "neq":
                        return actual != value
                    case "gt":
                        return actual > value
                    case "gte":
                        return actual >= value
                    case "lt":
                        return actual < value
                    case "lte":
                        return actual <= value
                    case "isnull":
                        return (actual is None) == value

            case And(left, right):
                return self.evaluate(left, obj) and self.evaluate(right, obj)

            case Or(left, right):
                return self.evaluate(left, obj) or self.evaluate(right, obj)

            case Not(expression):
                return not self.evaluate(expression, obj)

        raise TypeError(query)
