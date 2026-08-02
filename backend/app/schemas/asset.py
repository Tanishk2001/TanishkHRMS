from datetime import date, datetime

from pydantic import BaseModel


class AssetCreate(BaseModel):
    asset_tag: str
    category: str
    name: str
    serial_number: str | None = None
    purchase_date: date | None = None
    warranty_expiry: date | None = None


class AssetOut(BaseModel):
    id: int
    asset_tag: str
    category: str
    name: str
    serial_number: str | None
    status: str
    purchase_date: date | None
    warranty_expiry: date | None

    class Config:
        from_attributes = True


class AssetWithHolder(AssetOut):
    current_holder_name: str | None = None


class IssueAssetRequest(BaseModel):
    employee_id: int
    condition_on_issue: str = "GOOD"
    notes: str | None = None


class ReturnAssetRequest(BaseModel):
    condition_on_return: str = "GOOD"
    notes: str | None = None


class AssetAssignmentOut(BaseModel):
    id: int
    asset_id: int
    employee_id: int
    employee_name: str
    issued_at: datetime
    returned_at: datetime | None
    condition_on_issue: str | None
    condition_on_return: str | None
    notes: str | None
