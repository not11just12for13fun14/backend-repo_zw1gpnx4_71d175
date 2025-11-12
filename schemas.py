"""
Database Schemas for Pedigree Organizer

Each Pydantic model corresponds to a MongoDB collection.
Class name lowercased is used as the collection name.
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class Dog(BaseModel):
    """
    Dogs collection schema
    Collection: "dog"
    """
    name: str = Field(..., description="Dog's registered name")
    op_id: Optional[int] = Field(None, description="APBT Online Pedigrees dog_id if available")
    sex: Optional[str] = Field(None, description="Male/Female/Unknown")
    color: Optional[str] = Field(None)
    birth_date: Optional[str] = Field(None, description="YYYY-MM-DD or unknown")
    sire_id: Optional[str] = Field(None, description="Mongo _id of sire (father)")
    dam_id: Optional[str] = Field(None, description="Mongo _id of dam (mother)")
    tags: List[str] = Field(default_factory=list)
    source_url: Optional[str] = Field(None, description="Original source URL if imported")
    notes: Optional[str] = Field(None)
