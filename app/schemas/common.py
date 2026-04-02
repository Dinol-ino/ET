from typing import Any, Literal

from pydantic import BaseModel


class APIResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    message: str = "ok"
    data: Any = None
