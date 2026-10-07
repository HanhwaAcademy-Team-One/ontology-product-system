import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

MODES = ("mock", "real")
# Agents whose constructor accepts an LlmService. Extraction requires one;
# Ontology falls back to rule-based classification without it.
LLM_AGENTS = ("extraction", "ontology")
CONFIG_PATH = Path(__file__).parents[1] / "config" / "llm.yaml"
CONFIG_KEYS = {"provider", "models", "timeout_seconds", "max_retries"}


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    """Startup settings. API keys stay in the provider SDK's own environment."""

    mode: str = "mock"
    provider: str | None = None
    models: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 60.0
    max_retries: int = 2

    @classmethod
    def from_environment(cls, environ=None, *, config_path=CONFIG_PATH):
        """Read config-file defaults, then let environment variables override them."""
        env = os.environ if environ is None else environ
        mode = env.get("AGENT_MODE", "mock").strip().lower()
        if mode not in MODES:
            raise SettingsError(f"AGENT_MODE must be one of {MODES}, not {mode!r}")
        if mode == "mock":
            return cls()
        config_path = Path(config_path)
        file = _read_config(config_path)
        provider = env.get("LLM_PROVIDER", "").strip().lower() or file["provider"]
        if not provider:
            raise SettingsError("AGENT_MODE=real requires LLM_PROVIDER")
        unknown = sorted(
            key
            for key in env
            if key.startswith("LLM_MODEL_")
            and key.removeprefix("LLM_MODEL_").lower() not in LLM_AGENTS
        )
        if unknown:
            raise SettingsError(
                f"{', '.join(unknown)}: only {LLM_AGENTS} agents use an LLM model"
            )
        env_default = env.get("LLM_MODEL", "").strip()
        file_models = file["models"]
        models = {}
        for agent in LLM_AGENTS:
            name = f"LLM_MODEL_{agent.upper()}"
            # Environment always wins over the file: agent-specific, then shared.
            model = (
                env.get(name, "").strip()
                or env_default
                or file_models.get(agent)
                or file_models.get("default")
            )
            if not model:
                raise SettingsError(
                    f"AGENT_MODE=real requires LLM_MODEL or {name} "
                    f"(or models.default / models.{agent} in {config_path.name})"
                )
            models[agent] = model
        return cls(
            mode=mode,
            provider=provider,
            models=models,
            timeout_seconds=_env_number(
                env, "LLM_TIMEOUT_SECONDS", float, file["timeout_seconds"], 0
            ),
            max_retries=_env_number(
                env, "LLM_MAX_RETRIES", int, file["max_retries"], -1
            ),
        )

    def model_for(self, agent):
        if agent not in self.models:
            raise SettingsError(f"No LLM model is configured for agent {agent!r}")
        return self.models[agent]


def _read_config(path):
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SettingsError(f"{path.name} must be a mapping")
    if unknown := sorted(set(data) - CONFIG_KEYS):
        raise SettingsError(f"{path.name}: unsupported keys {unknown}")
    provider = data.get("provider")
    if provider is not None and not isinstance(provider, str):
        raise SettingsError(f"{path.name}: provider must be a string")
    models = data.get("models") or {}
    if not isinstance(models, dict):
        raise SettingsError(f"{path.name}: models must be a mapping")
    if unknown := sorted(set(models) - {"default", *LLM_AGENTS}):
        raise SettingsError(
            f"{path.name}: models {unknown} are not LLM agents {LLM_AGENTS}"
        )
    if any(m is not None and not isinstance(m, str) for m in models.values()):
        raise SettingsError(f"{path.name}: model names must be strings")
    return {
        "provider": (provider or "").strip().lower() or None,
        "models": {k: v.strip() for k, v in models.items() if v and v.strip()},
        "timeout_seconds": _file_number(data, "timeout_seconds", float, 60.0, 0),
        "max_retries": _file_number(data, "max_retries", int, 2, -1),
    }


def _file_number(data, name, kind, default, above):
    value = data.get(name, default)
    allowed = (int, float) if kind is float else (int,)
    if isinstance(value, bool) or not isinstance(value, allowed) or value <= above:
        raise SettingsError(f"{name} must be a {kind.__name__} above {above}")
    return kind(value)


def _env_number(env, name, kind, default, above):
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = kind(raw)
    except ValueError:
        raise SettingsError(f"{name} must be a {kind.__name__}, not {raw!r}") from None
    if value <= above:
        raise SettingsError(f"{name} must be greater than {above}, not {raw!r}")
    return value
