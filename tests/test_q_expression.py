from __future__ import annotations

from dataclasses import dataclass

import pytest

from pocket_option.q_expression import (
    And,
    Field,
    Not,
    Or,
    PythonQEvaluator,
    Q,
)


@dataclass
class Deal:
    uid: int
    asset: str
    closed: bool
    profit: float | None


@pytest.fixture
def evaluator() -> PythonQEvaluator:
    return PythonQEvaluator()


@pytest.fixture
def deal() -> Deal:
    return Deal(
        uid=123,
        asset="EURUSD",
        closed=False,
        profit=150.0,
    )


class TestQ:
    def test_field(self) -> None:
        query = Q.field("uid", "eq", 123)

        assert query == Field("uid", "eq", 123)

    def test_and(self) -> None:
        left = Q.field("uid", "eq", 123)
        right = Q.field("closed", "eq", False)

        assert left & right == And(left, right)

    def test_or(self) -> None:
        left = Q.field("uid", "eq", 123)
        right = Q.field("closed", "eq", False)

        assert left | right == Or(left, right)

    def test_not(self) -> None:
        expression = Q.field("closed", "eq", True)

        assert ~expression == Not(expression)

    def test_expressions_are_hashable(self) -> None:
        query = Q.field("uid", "eq", 123) & Q.field("closed", "eq", False)

        assert hash(query) == hash(query)

    def test_expressions_are_immutable(self) -> None:
        query = Q.field("uid", "eq", 123)

        with pytest.raises(AttributeError):
            query.name = "foo"  # type: ignore[attr-defined]


class TestPythonQEvaluator:
    @pytest.mark.parametrize(
        ("op", "value", "expected"),
        [
            ("eq", 123, True),
            ("eq", 456, False),
            ("neq", 456, True),
            ("neq", 123, False),
            ("gt", 100, True),
            ("gt", 123, False),
            ("gte", 123, True),
            ("gte", 124, False),
            ("lt", 200, True),
            ("lt", 123, False),
            ("lte", 123, True),
            ("lte", 122, False),
            ("isnull", False, True),
            ("isnull", True, False),
        ],
    )
    def test_field_operators(
        self,
        evaluator: PythonQEvaluator,
        deal: Deal,
        op: str,
        value: object,
        expected: bool,
    ) -> None:
        query = Q.field("uid", op, value)  # type: ignore[arg-type]

        assert evaluator.evaluate(query, deal) is expected

    @pytest.mark.parametrize(
        ("op", "value", "expected"),
        [
            ("eq", 150.0, True),
            ("eq", 100.0, False),
            ("neq", 100.0, True),
            ("neq", 150.0, False),
            ("gt", 100.0, True),
            ("gt", 150.0, False),
            ("gte", 150.0, True),
            ("gte", 151.0, False),
            ("lt", 200.0, True),
            ("lt", 150.0, False),
            ("lte", 150.0, True),
            ("lte", 149.0, False),
        ],
    )
    def test_numeric_operators(
        self,
        evaluator: PythonQEvaluator,
        deal: Deal,
        op: str,
        value: object,
        expected: bool,
    ) -> None:
        query = Q.field("profit", op, value)  # type: ignore[arg-type]

        assert evaluator.evaluate(query, deal) is expected

    def test_isnull_with_none(
        self,
        evaluator: PythonQEvaluator,
    ) -> None:
        deal = Deal(
            uid=123,
            asset="EURUSD",
            closed=False,
            profit=None,
        )

        assert evaluator.evaluate(
            Q.field("profit", "isnull", True),
            deal,
        )

        assert not evaluator.evaluate(
            Q.field("profit", "isnull", False),
            deal,
        )

    def test_isnull_with_non_none(
        self,
        evaluator: PythonQEvaluator,
        deal: Deal,
    ) -> None:
        assert evaluator.evaluate(
            Q.field("profit", "isnull", False),
            deal,
        )

        assert not evaluator.evaluate(
            Q.field("profit", "isnull", True),
            deal,
        )

    def test_and_true(self, evaluator: PythonQEvaluator, deal: Deal) -> None:
        query = Q.field("uid", "eq", 123) & Q.field("closed", "eq", False)

        assert evaluator.evaluate(query, deal)

    def test_and_false(self, evaluator: PythonQEvaluator, deal: Deal) -> None:
        query = Q.field("uid", "eq", 123) & Q.field("closed", "eq", True)

        assert not evaluator.evaluate(query, deal)

    def test_or_true(self, evaluator: PythonQEvaluator, deal: Deal) -> None:
        query = Q.field("uid", "eq", 999) | Q.field("closed", "eq", False)

        assert evaluator.evaluate(query, deal)

    def test_or_false(self, evaluator: PythonQEvaluator, deal: Deal) -> None:
        query = Q.field("uid", "eq", 999) | Q.field("closed", "eq", True)

        assert not evaluator.evaluate(query, deal)

    def test_not(self, evaluator: PythonQEvaluator, deal: Deal) -> None:
        query = ~Q.field("closed", "eq", True)

        assert evaluator.evaluate(query, deal)

    def test_nested_expression(
        self,
        evaluator: PythonQEvaluator,
        deal: Deal,
    ) -> None:
        query = Q.field("asset", "eq", "EURUSD") & (Q.field("closed", "eq", False) | Q.field("profit", "gt", 1000))

        assert evaluator.evaluate(query, deal)

    def test_complex_expression(
        self,
        evaluator: PythonQEvaluator,
        deal: Deal,
    ) -> None:
        query = ~(Q.field("uid", "eq", 999) | Q.field("asset", "eq", "BTCUSD")) & Q.field("profit", "gte", 100)

        assert evaluator.evaluate(query, deal)

    def test_missing_attribute_raises(
        self,
        evaluator: PythonQEvaluator,
        deal: Deal,
    ) -> None:
        query = Q.field("does_not_exist", "eq", 123)

        with pytest.raises(AttributeError):
            evaluator.evaluate(query, deal)

    def test_unsupported_query_raises(
        self,
        evaluator: PythonQEvaluator,
        deal: Deal,
    ) -> None:
        class UnknownQ(Q):
            pass

        query = UnknownQ()

        with pytest.raises(TypeError):
            evaluator.evaluate(query, deal)

    def test_and_short_circuits(
        self,
        evaluator: PythonQEvaluator,
        deal: Deal,
    ) -> None:
        query = Q.field("uid", "eq", 999) & Q.field("does_not_exist", "eq", 123)

        assert not evaluator.evaluate(query, deal)

    def test_or_short_circuits(
        self,
        evaluator: PythonQEvaluator,
        deal: Deal,
    ) -> None:
        query = Q.field("uid", "eq", 123) | Q.field("does_not_exist", "eq", 123)

        assert evaluator.evaluate(query, deal)

    def test_operator_precedence(self) -> None:
        left = Q.field("uid", "eq", 123)
        middle = Q.field("closed", "eq", False)
        right = Q.field("profit", "gt", 100)

        query = left & middle | right

        assert query == Or(
            And(left, middle),
            right,
        )
