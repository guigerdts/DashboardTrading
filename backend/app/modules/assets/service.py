"""Asset service — business rule enforcement for asset operations.

BR-16: (symbol, market_id) uniqueness enforced at service level via
``get_by_symbol_market()`` check before create/update.
"""

import logging

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.db.unit_of_work import UnitOfWork
from app.models.asset import Asset
from app.models.base import _utcnow
from app.modules.assets.schemas import AssetCreate, AssetFilters, AssetUpdate


class AssetService:
    """Service layer for asset operations — all BR enforcement lives here."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(self, dto: AssetCreate) -> Asset:
        """Create a new asset.

        BR-16: Rejects duplicate ``(symbol, market_id)`` with ``ConflictError`` (409).
        Validates that ``market_id`` references an existing market (422 otherwise).
        """
        # BR-16: check (symbol, market_id) uniqueness
        existing = await self.uow.assets.get_by_symbol_market(dto.symbol, dto.market_id)
        if existing:
            raise ConflictError(
                f"Asset with symbol '{dto.symbol}' and market_id {dto.market_id} already exists"
            )

        # Validate market exists
        market = await self.uow.markets.get(dto.market_id)
        if market is None:
            raise BusinessRuleError(
                f"Market with id {dto.market_id} does not exist",
                field="market_id",
            )

        asset = Asset(
            symbol=dto.symbol,
            name=dto.name,
            market_id=dto.market_id,
        )
        await self.uow.assets.add(asset)
        self.logger.info(
            "Created asset id=%d symbol=%s market_id=%d",
            asset.id,
            asset.symbol,
            asset.market_id,
        )
        return asset

    async def get(self, id: int) -> Asset:
        """Retrieve an asset by ID.

        Raises ``NotFoundError`` (404) if the asset does not exist.
        """
        asset = await self.uow.assets.get(id)
        if asset is None:
            raise NotFoundError(f"Asset with id {id} not found")
        return asset

    async def list(self, filters: AssetFilters) -> tuple[list[Asset], int]:
        """List assets with filters and pagination.

        Delegates to ``AssetRepository.list()`` with schema fields.
        """
        return await self.uow.assets.list(
            symbol=filters.symbol,
            market_id=filters.market_id,
            search=filters.search,
            is_active=filters.is_active,
            page=filters.page,
            page_size=filters.page_size,
        )

    async def update(self, id: int, dto: AssetUpdate) -> Asset:
        """Update an existing asset.

        BR-16: Re-checks ``(symbol, market_id)`` uniqueness if either field changes.
        Re-validates market existence if ``market_id`` changes.
        """
        asset = await self.get(id)
        update_data = dto.model_dump(exclude_unset=True)

        # Re-validate BR-16 if symbol or market_id changed
        if "symbol" in update_data or "market_id" in update_data:
            new_symbol = update_data.get("symbol", asset.symbol)
            new_market_id = update_data.get("market_id", asset.market_id)
            existing = await self.uow.assets.get_by_symbol_market(
                new_symbol,
                new_market_id,
            )
            if existing and existing.id != id:
                raise ConflictError(
                    f"Asset with symbol '{new_symbol}' and market_id {new_market_id} already exists"
                )

        # Re-validate market exists if market_id changed
        if "market_id" in update_data:
            market = await self.uow.markets.get(update_data["market_id"])
            if market is None:
                raise BusinessRuleError(
                    f"Market with id {update_data['market_id']} does not exist",
                    field="market_id",
                )

        for field, value in update_data.items():
            setattr(asset, field, value)

        asset.updated_at = _utcnow()
        self.logger.info("Updated asset id=%d fields=%s", id, set(update_data.keys()))
        return asset

    async def soft_delete(self, id: int) -> None:
        """BR-29: Soft-delete an asset by setting ``is_active=0``."""
        asset = await self.get(id)
        asset.is_active = 0
        asset.updated_at = _utcnow()
        self.logger.info("Soft-deleted asset id=%d", id)
