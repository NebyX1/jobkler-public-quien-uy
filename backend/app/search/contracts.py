from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from typing_extensions import Annotated


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]
SearchText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
TermText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]


class AdvancedSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)]
    departmentId: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=80)] = None
    localityId: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=80)] = None
    locationScope: Literal["national"] | None = None
    limit: int = Field(default=10, ge=1, le=20)

    @field_validator("departmentId", "localityId")
    @classmethod
    def empty_ids_are_null(cls, value):
        return value or None

    @model_validator(mode="after")
    def validate_location_scope(self):
        if self.locationScope and (self.departmentId or self.localityId):
            raise ValueError("La búsqueda nacional no admite un filtro de ubicación.")
        return self


class SearchIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["ok", "ambiguous", "unsupported"]
    search_text: SearchText
    profession_text: ShortText | None
    action_text: ShortText | None
    object_text: ShortText | None
    location_text: ShortText | None
    related_terms: list[TermText] = Field(..., max_length=4)
    excluded_terms: list[TermText] = Field(..., max_length=4)
    related_services: list[TermText] = Field(default_factory=list, max_length=2)
    required_terms: list[TermText] = Field(default_factory=list, max_length=3)


class RelatedEvidenceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: list[Annotated[int, Field(strict=True, ge=1, le=5)]] = Field(max_length=3)


class RelatedServicePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    services: list[TermText] = Field(max_length=2)

    @field_validator("services", mode="before")
    @classmethod
    def cap_proposals(cls, value):
        # The local model can exceed maxItems. Each retained proposal still needs evidence.
        return value[:2] if isinstance(value, list) else value


class AdvancedSearchError(ValueError):
    pass
