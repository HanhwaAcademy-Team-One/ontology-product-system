import importlib
import inspect
import pkgutil

import pytest
import yaml

import ontoproduct.agents
from ontoproduct.agents.base import BaseAgent
from ontoproduct.services.settings import (
    CONFIG_PATH,
    LLM_AGENTS,
    Settings,
    SettingsError,
)

REAL = {"AGENT_MODE": "real", "LLM_PROVIDER": "openai"}


@pytest.fixture
def load(tmp_path):
    """Load settings from an explicit config file so team defaults cannot leak in."""

    def load(environ, config=""):
        path = tmp_path / "llm.yaml"
        path.write_text(config, encoding="utf-8")
        return Settings.from_environment(environ, config_path=path)

    return load


def test_default_is_mock_mode_without_llm_settings(load):
    settings = load({})
    assert settings.mode == "mock"
    assert settings.provider is None
    assert settings.models == {}


def test_mock_mode_ignores_incomplete_llm_settings(load):
    assert load({"AGENT_MODE": "mock", "LLM_MODEL": "m"}).mode == "mock"


def test_llm_agents_are_the_agents_that_accept_an_llm_service():
    agents = [
        cls
        for module in pkgutil.iter_modules(ontoproduct.agents.__path__)
        for cls in vars(
            importlib.import_module(f"ontoproduct.agents.{module.name}")
        ).values()
        if inspect.isclass(cls) and issubclass(cls, BaseAgent) and cls is not BaseAgent
    ]
    accepting = {
        cls.name
        for cls in agents
        if "llm_service" in inspect.signature(cls.__init__).parameters
    }
    assert set(LLM_AGENTS) == accepting == {"extraction", "ontology"}


def test_real_mode_shares_default_model_across_llm_agents(load):
    settings = load({**REAL, "LLM_MODEL": "base-model"})
    assert settings.mode == "real"
    assert settings.provider == "openai"
    assert settings.models == {"extraction": "base-model", "ontology": "base-model"}
    assert settings.model_for("extraction") == "base-model"


def test_real_mode_per_agent_model_overrides_default(load):
    settings = load({**REAL, "LLM_MODEL": "base-model", "LLM_MODEL_ONTOLOGY": "small"})
    assert settings.models == {"extraction": "base-model", "ontology": "small"}


def test_real_mode_per_agent_models_without_default(load):
    settings = load({**REAL, "LLM_MODEL_EXTRACTION": "a", "LLM_MODEL_ONTOLOGY": "b"})
    assert settings.models == {"extraction": "a", "ontology": "b"}


def test_config_file_supplies_team_defaults(load):
    config = """
provider: openai
models:
  default: file-model
  ontology: file-small
timeout_seconds: 30
max_retries: 1
"""
    settings = load({"AGENT_MODE": "real"}, config)
    assert settings.provider == "openai"
    assert settings.models == {"extraction": "file-model", "ontology": "file-small"}
    assert (settings.timeout_seconds, settings.max_retries) == (30.0, 1)


def test_environment_overrides_config_file(load):
    config = """
provider: file-provider
models:
  default: file-model
  ontology: file-small
timeout_seconds: 30
max_retries: 1
"""
    settings = load(
        {
            "AGENT_MODE": "real",
            "LLM_PROVIDER": "env-provider",
            "LLM_MODEL": "env-model",
            "LLM_TIMEOUT_SECONDS": "15",
            "LLM_MAX_RETRIES": "0",
        },
        config,
    )
    assert settings.provider == "env-provider"
    # An environment default replaces every file model, including per-agent ones.
    assert settings.models == {"extraction": "env-model", "ontology": "env-model"}
    assert (settings.timeout_seconds, settings.max_retries) == (15.0, 0)
    settings = load({"AGENT_MODE": "real", "LLM_MODEL_EXTRACTION": "env-x"}, config)
    assert settings.models == {"extraction": "env-x", "ontology": "file-small"}


@pytest.mark.parametrize(
    "environ, message",
    [
        ({"AGENT_MODE": "demo"}, "AGENT_MODE"),
        ({"AGENT_MODE": "real", "LLM_MODEL": "m"}, "LLM_PROVIDER"),
        (REAL, "LLM_MODEL_EXTRACTION"),
        ({**REAL, "LLM_MODEL_EXTRACTION": "m"}, "LLM_MODEL_ONTOLOGY"),
        ({**REAL, "LLM_MODEL": "m", "LLM_MODEL_PARSER": "m"}, "LLM_MODEL_PARSER"),
        ({**REAL, "LLM_MODEL": "m", "LLM_TIMEOUT_SECONDS": "0"}, "LLM_TIMEOUT_SECONDS"),
        ({**REAL, "LLM_MODEL": "m", "LLM_TIMEOUT_SECONDS": "x"}, "LLM_TIMEOUT_SECONDS"),
        ({**REAL, "LLM_MODEL": "m", "LLM_MAX_RETRIES": "-1"}, "LLM_MAX_RETRIES"),
    ],
)
def test_invalid_environment_raises_clear_errors(load, environ, message):
    with pytest.raises(SettingsError, match=message):
        load(environ)


@pytest.mark.parametrize(
    "config, message",
    [
        ("- not a mapping", "mapping"),
        ("api_key: sk-secret", "api_key"),
        ("models:\n  parser: m", "parser"),
        ("models: m", "models"),
        ("timeout_seconds: 0", "timeout_seconds"),
        ("max_retries: 1.5", "max_retries"),
        ("provider: 3", "provider"),
    ],
)
def test_invalid_config_file_raises_clear_errors(load, config, message):
    with pytest.raises(SettingsError, match=message):
        load(REAL, config)


def test_timeout_and_retry_defaults(load):
    settings = load({**REAL, "LLM_MODEL": "m"})
    assert (settings.timeout_seconds, settings.max_retries) == (60.0, 2)


def test_unknown_agent_model_is_rejected(load):
    with pytest.raises(SettingsError, match="parser"):
        load({**REAL, "LLM_MODEL": "m"}).model_for("parser")


def test_settings_never_hold_api_keys(load):
    settings = load(
        {
            **REAL,
            "LLM_MODEL": "m",
            "OPENAI_API_KEY": "sk-secret",
            "LLM_API_KEY": "sk-secret",
        }
    )
    assert "sk-secret" not in repr(settings)


def test_shipped_config_is_valid_and_holds_no_secrets():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert set(config) <= {"provider", "models", "timeout_seconds", "max_retries"}
    # Real mode reads and validates the shipped file (str path accepted too).
    settings = Settings.from_environment(
        {**REAL, "LLM_MODEL": "m"}, config_path=str(CONFIG_PATH)
    )
    assert settings.models == {"extraction": "m", "ontology": "m"}
    assert Settings.from_environment({}).mode == "mock"


def test_shipped_config_values_are_what_real_mode_uses():
    # Expectations come from llm.yaml itself, so changing a model edits one file.
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    models = config["models"]
    settings = Settings.from_environment({"AGENT_MODE": "real"})
    assert settings.provider == config["provider"]
    assert settings.models == {
        agent: models.get(agent) or models["default"] for agent in LLM_AGENTS
    }
    assert settings.timeout_seconds == config["timeout_seconds"]
    assert settings.max_retries == config["max_retries"]
