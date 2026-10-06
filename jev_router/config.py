import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    mode: str = "demo"
    typesafe_key: str = field(default="", repr=False)
    router_key: str = field(default="", repr=False)
    llm_key: str = field(default="", repr=False)
    typesafe_model: str = "jev-1.13.0"
    llm_model: str = "mlx-community/Qwen2.5-7B-Instruct-4bit"
    llm_url: str = "http://127.0.0.1:8000/v1"
    confidence_min: float = 0.65
    decision_timeout: float = 8
    request_timeout: float = 45

    def __post_init__(self):
        if self.mode not in {"demo", "live"}:
            raise ValueError("ROUTER_MODE must be demo or live")
        if not 0 <= self.confidence_min <= 1:
            raise ValueError("ROUTE_CONFIDENCE_MIN must be between 0 and 1")
        if self.mode == "live" and (not self.typesafe_key or not self.router_key):
            raise ValueError("Live mode requires TYPESAFE_API_KEY and ROUTER_API_KEY")

    @classmethod
    def from_env(cls):
        load_dotenv()
        # Prevent SDK debug logging of user inputs and responses.
        os.environ["TYPESAFE_LOG_LEVEL"] = "off"
        return cls(
            mode=os.getenv("ROUTER_MODE", "demo"),
            typesafe_key=os.getenv("TYPESAFE_API_KEY", ""),
            router_key=os.getenv("ROUTER_API_KEY", ""),
            llm_key=os.getenv("LLM_API_KEY", ""),
            typesafe_model=os.getenv("TYPESAFE_MODEL", "jev-1.13.0"),
            llm_model=os.getenv("LLM_MODEL", "mlx-community/Qwen2.5-7B-Instruct-4bit"),
            llm_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/"),
            confidence_min=float(os.getenv("ROUTE_CONFIDENCE_MIN", "0.65")),
        )
