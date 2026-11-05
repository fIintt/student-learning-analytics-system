from typing import Annotated
from pydantic import BaseModel, Field, StrictInt, field_validator


class TeacherGroupsUpdate(BaseModel):
    group_ids: list[Annotated[StrictInt, Field(gt=0)]]

    @field_validator("group_ids")
    @classmethod
    def unique_groups(cls, values):
        return sorted(set(values))
