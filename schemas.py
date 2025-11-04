"""
Database Schemas for Compass Remodeling CMS

Each Pydantic model maps to a MongoDB collection (lowercased class name).
These schemas power validation and the auto-generated admin viewer.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Adminuser(BaseModel):
    email: str = Field(..., description="Admin email")
    password_hash: str = Field(..., description="BCrypt password hash")
    name: Optional[str] = Field(None, description="Display name")
    role: str = Field("admin", description="Role name")
    active: bool = Field(True, description="Active status")


class Service(BaseModel):
    title: str = Field(..., description="Service title")
    description: str = Field(..., description="Service description")
    image_url: Optional[str] = Field(None, description="Cover image URL")
    featured: bool = Field(False, description="Whether to feature on home page")
    order: int = Field(0, description="Sort order")


class Galleryitem(BaseModel):
    title: str = Field(..., description="Project title")
    image_url: str = Field(..., description="Image URL")
    category: Optional[str] = Field(None, description="Category or tag")
    before_image_url: Optional[str] = Field(None, description="Before image URL for slider")
    after_image_url: Optional[str] = Field(None, description="After image URL for slider")
    order: int = Field(0, description="Sort order")


class Testimonial(BaseModel):
    client_name: str = Field(..., description="Client name")
    description: Optional[str] = Field(None, description="Short description or summary")
    video_url: Optional[str] = Field(None, description="Video URL (YouTube, Vimeo, or MP4)")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    order: int = Field(0, description="Sort order")


class Message(BaseModel):
    name: str = Field(..., description="Sender name")
    email: str = Field(..., description="Sender email")
    phone: Optional[str] = Field(None, description="Phone number")
    message: str = Field(..., description="Message body")
    read: bool = Field(False, description="Read status")


class Mediaasset(BaseModel):
    url: str = Field(..., description="Public URL to the uploaded asset")
    type: str = Field(..., description="mime type")
    width: Optional[int] = Field(None, description="Image width if applicable")
    height: Optional[int] = Field(None, description="Image height if applicable")
    size: Optional[int] = Field(None, description="File size in bytes")
    alt: Optional[str] = Field(None, description="Alt text/caption")
