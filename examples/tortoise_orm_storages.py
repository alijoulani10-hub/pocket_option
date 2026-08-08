import os
from collections.abc import Iterable
from uuid import UUID

from pydantic import typing
from tortoise import fields, models
from tortoise.expressions import Q

from pocket_option import q_expressions
from pocket_option.contrib.assets import AssetsStorage
from pocket_option.contrib.deals import DealsStorage
from pocket_option.contrib.default_init import default_init
from pocket_option.generated_client import PocketOptionClient
from pocket_option.models import Asset, AssetType, AuthorizationData, Command, Deal, UpdateAssetItem

client = PocketOptionClient(logger=True, filter_events_log=["updateStream"])


class DBAsset(models.Model):
    id = fields.IntField(pk=True)

    asset = fields.CharEnumField(Asset, max_length=64, unique=True)
    label = fields.CharField(max_length=255)
    type = fields.CharEnumField(AssetType, max_length=32)

    digits = fields.IntField()
    payout = fields.IntField()

    default_expiration = fields.IntField()
    min_expiration = fields.IntField()
    expiration_step = fields.IntField()

    is_otc = fields.BooleanField()
    otc_id = fields.IntField()
    real_id = fields.IntField()

    signals = fields.JSONField()
    exp_time = fields.BigIntField()
    active = fields.BooleanField()

    timeframes = fields.JSONField()

    scheduled_until = fields.BigIntField()
    min_quick_timeframe = fields.IntField()
    scheduled_at = fields.BigIntField()

    class Meta(models.Model.Meta):
        table = "assets"


class DBDeal(models.Model):
    id = fields.UUIDField(pk=True)

    command = fields.CharEnumField(Command, max_length=32)
    asset = fields.CharEnumField(Asset, max_length=64)

    uid = fields.BigIntField()
    amount = fields.FloatField()
    is_demo = fields.BooleanField()

    profit = fields.FloatField()
    percent_profit = fields.FloatField()
    percent_loss = fields.FloatField()

    open_time = fields.DatetimeField()
    close_time = fields.DatetimeField(null=True)

    open_timestamp = fields.FloatField()
    close_timestamp = fields.FloatField(null=True)

    refund_time = fields.DatetimeField(null=True)
    refund_timestamp = fields.BigIntField(null=True)

    open_price = fields.FloatField()
    close_price = fields.FloatField(null=True)

    copy_ticket = fields.CharField(max_length=255)
    open_ms = fields.BigIntField(null=True)
    close_ms = fields.BigIntField(null=True)

    option_type = fields.IntField(null=True)
    is_rollover = fields.BooleanField(null=True)
    is_copy_signal = fields.BooleanField()
    is_ai = fields.BooleanField(null=True)

    currency = fields.CharField(max_length=16)
    amount_usd = fields.FloatField(null=True)

    request_id = fields.BigIntField(null=True)

    class Meta(models.Model.Meta):
        table = "deals"


class TortoiseORMQTranslator:
    def translate(self, query: q_expressions.Q) -> Q:  # noqa: PLR0911
        match query:
            case q_expressions.Field(name, "eq", value):
                return Q(**{name: value})

            case q_expressions.Field(name, "neq", value):
                return Q(**{f"{name}__not": value})

            case q_expressions.Field(name, "gt", value):
                return Q(**{f"{name}__gt": value})

            case q_expressions.Field(name, "gte", value):
                return Q(**{f"{name}__gte": value})

            case q_expressions.Field(name, "lt", value):
                return Q(**{f"{name}__lt": value})

            case q_expressions.Field(name, "lte", value):
                return Q(**{f"{name}__lte": value})

            case q_expressions.Field(name, "isnull", value):
                return Q(**{f"{name}__isnull": value})

            case q_expressions.And(left, right):
                return self.translate(left) & self.translate(right)

            case q_expressions.Or(left, right):
                return self.translate(left) | self.translate(right)

            case q_expressions.Not(expression):
                return ~self.translate(expression)

            case _:
                raise TypeError(query)


class TortoiseORMAssetsStorage(AssetsStorage):
    def __init__(self, client: PocketOptionClient) -> None:
        super().__init__(client)
        self._translator = TortoiseORMQTranslator()

    async def get_assets(self) -> list[UpdateAssetItem]:
        return [UpdateAssetItem.model_validate(asset, from_attributes=True) async for asset in DBAsset.all()]

    async def get_asset(
        self,
        *,
        assset: Asset | None = None,
        asset_id: int | None = None,
    ) -> UpdateAssetItem | None:
        qs = Q(assset=assset) if assset is not None else Q(id=asset_id)
        result = await DBAsset.filter(qs).first()
        if result is None:
            return None
        return UpdateAssetItem.model_validate(result, from_attributes=True)

    async def search_assets(self, *, query: q_expressions.Q | None = None) -> list[UpdateAssetItem]:
        qs = self._translator.translate(query) if query is not None else Q()
        return [UpdateAssetItem.model_validate(asset, from_attributes=True) async for asset in DBAsset.filter(qs)]

    async def add_asset(self, item: UpdateAssetItem) -> None:
        await DBAsset.update_or_create(
            defaults=item.model_dump(),
            id=item.id,
        )

    async def add_assets_bulk(self, items: list[UpdateAssetItem]) -> None:
        await DBAsset.bulk_create(
            [DBAsset(**item.model_dump()) for item in items],
            update_fields=UpdateAssetItem.model_fields.keys() - {"id"},
            on_conflict={"id"},
        )


class TortoiseORMDealsStorage(DealsStorage):
    def __init__(self, client: PocketOptionClient) -> None:
        super().__init__(client)
        self._translator = TortoiseORMQTranslator()

    async def add_or_update_deal(self, deal: Deal) -> None:
        await DBDeal.update_or_create(
            defaults=deal.model_dump(),
            id=deal.id,
        )

    async def add_or_update_deals_bulk(self, deals: list[Deal]) -> None:
        await DBDeal.bulk_create(
            [DBDeal(**deal.model_dump()) for deal in deals],
            update_fields=Deal.model_fields.keys() - {"id"},
            on_conflict={"id"},
        )

    async def get_deal(self, *, deal_id: UUID | None = None, request_id: int | None = None) -> Deal | None:
        qs = Q(id=deal_id) if deal_id is not None else Q(request_id=request_id)
        result = await DBDeal.filter(qs).first()
        if result is None:
            return None
        return Deal.model_validate(
            result,
            from_attributes=True,
        )

    async def get_deals(self, *, query: q_expressions.Q, count: int | None = None) -> Iterable[Deal]:
        quertset = DBDeal.filter(self._translator.translate(query))
        if count is not None:
            quertset = quertset.limit(count)
        return [Deal.model_validate(deal, from_attributes=True) async for deal in quertset]


default_init(
    client,
    authorization=AuthorizationData.model_validate(
        {
            "session": os.environ["PO_SESSION"],
            "isDemo": 1,
            "uid": int(os.environ["PO_UID"]),
            "platform": 2,
            "isFastHistory": True,
            "isOptimized": True,
        },
    ),
    deals_storage_cls=TortoiseORMDealsStorage,
    assets_storage_cls=TortoiseORMAssetsStorage,
)
