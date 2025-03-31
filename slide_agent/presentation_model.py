from pydantic import BaseModel, Field
from dataclasses import dataclass
from typing import List, Union, Literal, Optional

class ImageData(BaseModel):
    image_url: str
    caption: str
    width: int
    height: int

@dataclass
class Content:
    title: str
    content: str
    images: List[ImageData]
    language: str

class BulletPoints(BaseModel):
    subject: str
    points: List[str]

class Description(BaseModel):
    text: str

class Slide(BaseModel):
    title: str = Field(description="title of slide")
    body_text: Union[BulletPoints | Description]
    reference: str | None = Field(description="Reference link of figures, cite, etc", default=None)
    layout: Literal["cover", "table content", "only text", "text, image 25%", "text and image equal, 50%-50%",
    "image, text 25%", "only image", "text and 4 images", "text and 2 images", "graph", "video", "closing"]
    image_urls: Optional[List[str]]
    page: int

class Presentation(BaseModel):
    title: str
    slides: List[Slide]