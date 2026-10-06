import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Route = Literal["local_llm", "retrieve", "clarify", "configuration"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=4000)
    max_tokens: int = Field(default=192, ge=16, le=512)

    @field_validator("question")
    @classmethod
    def trim_question(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be blank")
        return value


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selected_route: Literal["local_llm", "retrieve", "clarify"]
    probabilities: dict[str, float]
    confidence: float = Field(ge=0, le=1)
    needs_context: float = Field(ge=0, le=1)
    relevance: dict[str, float] = Field(default_factory=dict)
    model: str
    input_tokens: int = Field(default=0, ge=0)
    duration_ms: float = Field(default=0, ge=0)
    source: Literal["jev", "demo", "rules", "local_qwen"] = "jev"

    @model_validator(mode="after")
    def valid_distribution(self):
        if set(self.probabilities) != {"local_llm", "retrieve", "clarify"}:
            raise ValueError("Unexpected routing options")
        values = list(self.probabilities.values())
        if any(not math.isfinite(p) or not 0 <= p <= 1 for p in values):
            raise ValueError("Invalid route probability")
        if not math.isclose(sum(values), 1, abs_tol=0.01):
            raise ValueError("Route probabilities do not sum to one")
        if self.probabilities[self.selected_route] < max(values) - 0.001:
            raise ValueError("Selected route is not the highest probability")
        if any(not math.isfinite(s) or not 0 <= s <= 2 for s in self.relevance.values()):
            raise ValueError("Invalid relevance score")
        return self
