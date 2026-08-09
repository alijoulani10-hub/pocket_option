from __future__ import annotations

import datetime
import json
from collections import deque
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import pytz

from pocket_option import utils
from pocket_option.constants import TIMESTAMP_OFFSET


class TestSetPrettyName:
    def test_sets_name_and_returns_same_object(self) -> None:
        item = SimpleNamespace()

        result = utils.set_pretty_name(item, "Pretty Name")

        assert result is item
        assert item.__pretty_name__ == "Pretty Name"


class TestGetFunctionFullName:
    def test_function(self) -> None:
        def example() -> None:
            pass

        assert (
            utils.get_function_full_name(example)
            == f"{__name__}.TestGetFunctionFullName.test_function.<locals>.example"
        )

    def test_class(self) -> None:
        class Example:
            pass

        assert utils.get_function_full_name(Example) == "Example.__init__"

    def test_object_with_pretty_name(self) -> None:
        class Example:
            __pretty_name__ = "Custom Name"

        item = Example()

        assert utils.get_function_full_name(item) == "Custom Name"  # type: ignore

    def test_function_without_module(self) -> None:
        fn = Mock()
        fn.__module__ = None  # type: ignore
        fn.__qualname__ = "example"

        assert utils.get_function_full_name(fn) == "example"


class TestGetJsonFunction:
    def test_loads_json(self) -> None:
        function = utils.get_json_function()

        assert function.loads('{"foo": 123}') == {"foo": 123}

    def test_loads_bytes(self) -> None:
        function = utils.get_json_function()

        assert function.loads(b'{"foo": 123}') == {"foo": 123}

    def test_dumps_json(self) -> None:
        function = utils.get_json_function()

        result = function.dumps({"foo": "bar"})

        assert json.loads(result) == {"foo": "bar"}

    def test_dumps_preserves_unicode(self) -> None:
        function = utils.get_json_function()

        result = function.dumps({"message": "Привет"})

        assert "Привет" in result

    def test_dumps_separators(self) -> None:
        function = utils.get_json_function()

        result = function.dumps(
            {"foo": "bar"},
            separators=(",", ":"),
        )

        assert result == '{"foo":"bar"}'


class TestAppendOrReplace:
    def test_appends_when_no_matching_item(self) -> None:
        array = [
            SimpleNamespace(id=1),
            SimpleNamespace(id=2),
        ]
        item = SimpleNamespace(id=3)

        result = utils.append_or_replace(
            array,
            item,
            ["id"],
        )

        assert result is array
        assert array == [
            SimpleNamespace(id=1),
            SimpleNamespace(id=2),
            item,
        ]

    def test_replaces_matching_item(self) -> None:
        first = SimpleNamespace(id=1, value="old")
        second = SimpleNamespace(id=2, value="other")
        replacement = SimpleNamespace(id=1, value="new")

        array = [first, second]

        result = utils.append_or_replace(
            array,
            replacement,
            ["id"],
        )

        assert result is array
        assert array == [replacement, second]

    def test_replaces_only_first_matching_item(self) -> None:
        first = SimpleNamespace(id=1, value="first")
        second = SimpleNamespace(id=1, value="second")
        replacement = SimpleNamespace(id=1, value="new")

        array = [first, second]

        utils.append_or_replace(
            array,
            replacement,
            ["id"],
        )

        assert array == [replacement, second]

    def test_matches_by_multiple_keys(self) -> None:
        first = SimpleNamespace(asset="EURUSD", uid=1, value="old")
        second = SimpleNamespace(asset="EURUSD", uid=2, value="other")
        replacement = SimpleNamespace(
            asset="EURUSD",
            uid=1,
            value="new",
        )

        array = [first, second]

        utils.append_or_replace(
            array,
            replacement,
            ["asset", "uid"],
        )

        assert array == [replacement, second]

    def test_does_not_replace_when_only_one_key_matches(self) -> None:
        first = SimpleNamespace(asset="EURUSD", uid=1)
        replacement = SimpleNamespace(asset="EURUSD", uid=2)

        array = [first]

        utils.append_or_replace(
            array,
            replacement,
            ["asset", "uid"],
        )

        assert array == [first, replacement]

    def test_works_with_deque(self) -> None:
        first = SimpleNamespace(id=1)
        replacement = SimpleNamespace(id=1)

        array = deque([first])

        result = utils.append_or_replace(
            array,
            replacement,
            ["id"],
        )

        assert result is array
        assert list(array) == [replacement]

    def test_appends_to_deque(self) -> None:
        array = deque([SimpleNamespace(id=1)])
        item = SimpleNamespace(id=2)

        result = utils.append_or_replace(
            array,
            item,
            ["id"],
        )

        assert result is array
        assert list(array) == [
            SimpleNamespace(id=1),
            item,
        ]

    def test_custom_key_getter(self) -> None:
        array = [
            {"id": 1, "value": "old"},
        ]
        item = {"id": 1, "value": "new"}

        result = utils.append_or_replace(
            array,
            item,
            ["id"],
            get_key_method=lambda obj, key: obj[key],
        )

        assert result == [item]

    def test_empty_key_list_replaces_first_item(self) -> None:
        first = SimpleNamespace(id=1)
        replacement = SimpleNamespace(id=2)

        array = [first]

        utils.append_or_replace(
            array,
            replacement,
            [],
        )

        assert array == [replacement]


class TestGetServerTime:
    def test_returns_current_time_with_offset(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(utils.time, "time", lambda: 1_000.0)

        assert utils.get_server_time() == 1_000.0 - TIMESTAMP_OFFSET


class TestFixTimestamp:
    def test_float(self) -> None:
        timestamp = 1_000.5

        result = utils.fix_timestamp(timestamp)

        assert result == timestamp + TIMESTAMP_OFFSET

    def test_datetime(self) -> None:
        timestamp = datetime.datetime(
            2026,
            1,
            1,
            12,
            0,
            0,
            tzinfo=pytz.UTC,
        )

        result = utils.fix_timestamp(timestamp)

        expected = datetime.datetime.fromtimestamp(
            timestamp.timestamp() + TIMESTAMP_OFFSET,
            tz=pytz.UTC,
        )

        assert result == expected
        assert result.tzinfo == pytz.UTC

    def test_naive_datetime(self) -> None:
        timestamp = datetime.datetime(2026, 1, 1, 12, 0, 0)  # noqa: DTZ001

        result = utils.fix_timestamp(timestamp)

        expected = datetime.datetime.fromtimestamp(
            timestamp.timestamp() + TIMESTAMP_OFFSET,
            tz=pytz.UTC,
        )

        assert result == expected

    @pytest.mark.parametrize(
        "value",
        [
            123,
            "123",
            None,
            object(),
        ],
    )
    def test_unsupported_type(self, value: object) -> None:
        with pytest.raises(
            TypeError,
            match=r"Unsupported type:",
        ):
            utils.fix_timestamp(value)  # type: ignore
