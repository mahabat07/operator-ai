import uuid
from typing import Generic, TypeVar

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class WorkspaceScopedRepository(Generic[ModelT]):


    def __init__(self, model: type[ModelT], db: AsyncSession):
        self.model = model
        self.db = db

    async def list(self, workspace_id: uuid.UUID, *, limit: int = 50, offset: int = 0, **filters) -> list[ModelT]:
        stmt = select(self.model).where(self.model.workspace_id == workspace_id)
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        stmt = stmt.order_by(self.model.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, workspace_id: uuid.UUID, **filters) -> int:
        stmt = select(func.count()).select_from(self.model).where(self.model.workspace_id == workspace_id)
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get(self, workspace_id: uuid.UUID, obj_id: uuid.UUID) -> ModelT:
        stmt = select(self.model).where(self.model.workspace_id == workspace_id, self.model.id == obj_id)
        obj = (await self.db.execute(stmt)).scalar_one_or_none()
        if obj is None:
            raise HTTPException(status_code=404, detail=f"{self.model.__name__} not found")
        return obj

    async def create(self, workspace_id: uuid.UUID, **fields) -> ModelT:
        obj = self.model(workspace_id=workspace_id, **fields)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, workspace_id: uuid.UUID, obj_id: uuid.UUID, **fields) -> ModelT:
        obj = await self.get(workspace_id, obj_id)
        for key, value in fields.items():
            if value is not None or key in fields:
                setattr(obj, key, value)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, workspace_id: uuid.UUID, obj_id: uuid.UUID) -> None:
        obj = await self.get(workspace_id, obj_id)
        await self.db.delete(obj)
        await self.db.commit()
