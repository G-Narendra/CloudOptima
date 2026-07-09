"""CloudOptima - Application Configuration."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # NVIDIA NIMs API
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "mistralai/mistral-small-4-119b-2603"

    # Per-agent model overrides
    architect_model: Optional[str] = None
    cost_model: Optional[str] = None
    security_model: Optional[str] = None
    compliance_model: Optional[str] = None
    judge_model: Optional[str] = None

    # Azure (optional - for live pricing API)
    azure_subscription_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None

    # App
    app_name: str = "CloudOptima"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    # Demo mode: when True, uses mock data instead of live API calls
    demo_mode: bool = True

    # Sentry error tracking
    # Get your DSN from https://sentry.io/settings/projects/<project>/keys/
    sentry_dsn: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def get_agent_model(self, agent_type: str) -> str:
        """Get the model for a specific agent, falling back to the default."""
        override_map = {
            "architect": self.architect_model,
            "cost": self.cost_model,
            "security": self.security_model,
            "compliance": self.compliance_model,
            "judge": self.judge_model,
        }
        return override_map.get(agent_type) or self.nvidia_model


settings = Settings()
