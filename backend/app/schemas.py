from pydantic import BaseModel, Field
from datetime import datetime as dt_datetime
from typing import List, Optional

class HCPBase(BaseModel):
    name: str
    specialty: str
    email: Optional[str] = None
    phone: Optional[str] = None
    clinic_address: Optional[str] = None

class HCPCreate(HCPBase):
    pass

class HCPResponse(HCPBase):
    id: int

    class Config:
        from_attributes = True

class MaterialBase(BaseModel):
    name: str
    type: str  # "Material" or "Sample"
    description: Optional[str] = None

class MaterialCreate(MaterialBase):
    pass

class MaterialResponse(MaterialBase):
    id: int

    class Config:
        from_attributes = True

class InteractionCreate(BaseModel):
    hcp_id: int
    type: str  # "Meeting", "Call", "Email", "Conference", etc.
    datetime: dt_datetime
    attendees: List[str] = []
    topics: Optional[str] = None
    sentiment: str  # "Positive", "Neutral", "Negative"
    outcomes: Optional[str] = None
    follow_ups: Optional[str] = None
    shared_material_ids: List[int] = []
    distributed_sample_ids: List[int] = []

class InteractionUpdate(BaseModel):
    hcp_id: Optional[int] = None
    type: Optional[str] = None
    datetime: Optional[dt_datetime] = None
    attendees: Optional[List[str]] = None
    topics: Optional[str] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_ups: Optional[str] = None
    shared_material_ids: Optional[List[int]] = None
    distributed_sample_ids: Optional[List[int]] = None

class InteractionResponse(BaseModel):
    id: int
    hcp_id: int
    hcp: HCPResponse
    type: str
    datetime: dt_datetime
    attendees: List[str] = []
    topics: Optional[str] = None
    sentiment: str
    outcomes: Optional[str] = None
    follow_ups: Optional[str] = None
    shared_materials: List[MaterialResponse] = []
    distributed_samples: List[MaterialResponse] = []

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    current_form_state: Optional[dict] = None

class ChatResponse(BaseModel):
    reply: str
    parsed_form_data: Optional[dict] = None  # extracted details to update the React state
    tool_calls: List[str] = []
    suggested_follow_ups: List[str] = []
