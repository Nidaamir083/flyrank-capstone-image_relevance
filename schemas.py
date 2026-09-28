from pydantic import BaseModel, Field

class ImageTags(BaseModel):
    subject: str
    category: str
    attributes: list[str]
    caption: str
    confidence: float = Field(ge=0, le=1)