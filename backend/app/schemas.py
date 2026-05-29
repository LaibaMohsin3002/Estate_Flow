from pydantic import BaseModel, ConfigDict, Field


class MaintenanceCreate(BaseModel):
    property_id: str | None = None
    unit: str
    property_name: str
    original_issue: str
    latitude: float | None = None
    longitude: float | None = None


class MaintenanceApprove(BaseModel):
    approved: bool = True


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    whatsapp_phone: str | None = None
    property_id: str | None = None
    unit_id: str | None = None
    area: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    specialties: list[str] | None = None


class VendorRateBody(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None
    request_id: str | None = None


class VendorReplyWebhookBody(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    message: str = ""
    from_: str = Field(..., alias="from")
    ticket_id: str | None = None
    request_id: str | None = None


class CalendarConnectRequest(BaseModel):
    code: str
    calendar_id: str = "primary"


class MaintenanceFeedback(BaseModel):
    confirmed_resolved: bool
    comment: str | None = None


class InspectionCreate(BaseModel):
    property_id: str | None = None
    property_name: str
    unit: str = "Common"
    inspection_type: str
    items: list[dict] = Field(default_factory=list)
    notes: dict = Field(default_factory=dict)


class PropertyCreate(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    total_units: int = 0
    latitude: float | None = None
    longitude: float | None = None
    unit_numbers: list[str] = Field(default_factory=list)


class UnitCreate(BaseModel):
    unit_number: str
    floor: int | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None


class VendorCreate(BaseModel):
    name: str
    specialty: str
    phone: str | None = None
    email: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    area: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    property_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)
