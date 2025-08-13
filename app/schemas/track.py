from pydantic import BaseModel, Field

class TrackCreate(BaseModel):
    title: str | None = None

class TrackOut(BaseModel):
    id: int
    title: str | None
    status: str
    class Config:
        from_attributes = True