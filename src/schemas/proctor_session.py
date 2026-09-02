from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProctorSessionClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(gt=0)

    test_id: int = Field(gt=0)

    schedule_id: int = Field(gt=0)

    proctor_session_id: UUID

    iss: str = Field(min_length=1)

    aud: str = Field(min_length=1)

    iat: int = Field(gt=0)

    exp: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_times(self):
        if self.exp <= self.iat:
            raise ValueError("exp must be greater than iat")

        return self
