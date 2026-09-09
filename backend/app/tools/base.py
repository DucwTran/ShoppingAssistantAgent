from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel


@dataclass
class RegisteredTool:
    name: str
    description: str
    args_schema: type[BaseModel]
    func: Callable[..., Any]

    def run(self, **kwargs: Any) -> Any:
        validated = self.args_schema(**kwargs)
        return self.func(**validated.model_dump())
