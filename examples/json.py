import orjson

from pocket_option.generated_client import PocketOptionClient
from pocket_option.middlewares import FixTypesMiddleware, MakeJsonOnMiddleware
from pocket_option.types import JsonValue


class OrJsonFunctions:
    def dumps(
        self,
        value: JsonValue,
        *,
        separators: tuple[str, str] | None = None,  # noqa: ARG002
    ) -> str:
        return orjson.dumps(value).decode("utf-8")

    def loads(self, value: str | bytes) -> JsonValue:
        return orjson.loads(value)


client = PocketOptionClient(
    logger=True,
    middlewares=[MakeJsonOnMiddleware(json=OrJsonFunctions()), FixTypesMiddleware()],
    json=OrJsonFunctions(),
    filter_events_log=["updateStream"],
)
