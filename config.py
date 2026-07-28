"""
config.py
=========

Configuration management for HireSense AI.
Handles loading environment variables from .env file and LangSmith integration.
"""

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

DEFAULT_OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_OPENROUTER_EVALUATION_MODEL = DEFAULT_OPENROUTER_MODEL

# Global flags to prevent repeated initialization
# Using a dict to maintain state across module reloads
_init_state = {
    "env_loaded": False,
    "langsmith_initialized": False,
    "langsmith_status": None,
}


def load_env_file():
    """
    Load environment variables from .env file.
    This function should be called at the very start of the application.
    Only runs once per session.
    """
    # Prevent repeated loading
    if _init_state["env_loaded"]:
        return True

    # Only load a project-local file. Loading a generic home-directory .env can
    # accidentally import credentials that belong to an unrelated application.
    possible_paths = [Path(__file__).resolve().parent / ".env"]

    env_file = None
    for path in possible_paths:
        if path.is_file():
            env_file = path
            break

    if env_file is None:
        # Hosted deployments normally provide environment variables without a
        # local .env file, so absence is not an error.
        _init_state["env_loaded"] = True
        return False

    try:
        parsed = dotenv_values(env_file)
        load_dotenv(dotenv_path=env_file, override=False)
    except Exception as e:
        print(f"Environment file could not be loaded: {e.__class__.__name__}")
        _init_state["env_loaded"] = True
        return False

    variable_count = sum(1 for key, value in parsed.items() if key and value is not None)
    print(
        f"Environment loaded from project .env "
        f"({variable_count} variables; values omitted)"
    )

    _init_state["env_loaded"] = True
    return True


def get_openrouter_api_key():
    """Get the OpenRouter API key from environment."""
    return os.environ.get("OPENROUTER_API_KEY")


def _model_setting(name: str, default: str) -> str:
    """Return a clean OpenRouter model slug with a safe project default."""
    value = str(os.environ.get(name, "")).strip()
    return value or default


def get_openrouter_model() -> str:
    """Return the model used for interactive and supporting AI features."""
    return _model_setting("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)


def get_openrouter_evaluation_model() -> str:
    """Return the transcript evaluator model."""
    return _model_setting(
        "OPENROUTER_EVALUATION_MODEL",
        get_openrouter_model() or DEFAULT_OPENROUTER_EVALUATION_MODEL,
    )


def get_langsmith_api_key():
    """Get the LangSmith API key from environment."""
    return os.environ.get("LANGCHAIN_API_KEY")


def developer_controls_enabled() -> bool:
    """Return whether explicit simulation controls should be shown."""
    return os.environ.get("HIRESENSE_DEVELOPER_MODE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def is_langsmith_enabled():
    """Check if LangSmith tracing is enabled and properly configured."""
    api_key = get_langsmith_api_key()
    tracing_enabled = os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"

    if not api_key or api_key == "your_langsmith_api_key_here":
        return False

    return tracing_enabled


def setup_langsmith():
    """
    Setup LangSmith tracing if configured.
    Returns a status dict with configuration details.
    Only runs once per session.
    """
    # Return cached status if already initialized
    if (
        _init_state["langsmith_initialized"]
        and _init_state["langsmith_status"] is not None
    ):
        return _init_state["langsmith_status"]

    status = {"enabled": False, "project": None, "endpoint": None, "message": ""}

    api_key = get_langsmith_api_key()

    # Check if API key is set and not placeholder
    if not api_key:
        status["message"] = "LangSmith API key not set (optional)"
        _init_state["langsmith_initialized"] = True
        _init_state["langsmith_status"] = status
        return status

    if api_key == "your_langsmith_api_key_here":
        status["message"] = "LangSmith API key is placeholder - update .env to enable"
        _init_state["langsmith_initialized"] = True
        _init_state["langsmith_status"] = status
        return status

    # Tracing is opt-in because prompts can contain resume and interview data.
    tracing_enabled = os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
    if not tracing_enabled:
        status["message"] = "LangSmith tracing is disabled"
        _init_state["langsmith_initialized"] = True
        _init_state["langsmith_status"] = status
        return status

    # Set default project if not set
    project = os.environ.get("LANGCHAIN_PROJECT", "HireSense_AI")
    if not os.environ.get("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = project

    # Set default endpoint if not set
    endpoint = os.environ.get("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    if not os.environ.get("LANGCHAIN_ENDPOINT"):
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    status["enabled"] = True
    status["project"] = project
    status["endpoint"] = endpoint
    status["message"] = f"LangSmith tracing enabled for project: {project}"

    # Only print once
    if not _init_state["langsmith_initialized"]:
        print(f"🔍 {status['message']}")

    _init_state["langsmith_initialized"] = True
    _init_state["langsmith_status"] = status

    return status


def disable_langsmith():
    """
    Disable LangSmith tracing to prevent API errors.
    Call this if you don't have a valid LangSmith API key.
    """
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    if _init_state["langsmith_status"]:
        _init_state["langsmith_status"]["enabled"] = False
        _init_state["langsmith_status"]["message"] = "LangSmith tracing disabled"


def validate_config():
    """Validate that required configuration is present."""
    api_key = get_openrouter_api_key()

    if not api_key:
        return False, "OPENROUTER_API_KEY is not set. Please add it to your .env file."

    if api_key == "your_openrouter_api_key_here":
        return (
            False,
            "OPENROUTER_API_KEY is still set to the placeholder value. Please update your .env file with your actual API key.",
        )

    return True, "Configuration is valid."


def get_config_status():
    """
    Get a comprehensive status of all configuration.
    Returns a dict with status of each component.
    """
    openrouter_key = get_openrouter_api_key()
    langsmith_status = setup_langsmith()

    return {
        "openrouter": {
            "configured": bool(
                openrouter_key and openrouter_key != "your_openrouter_api_key_here"
            ),
            "model": get_openrouter_model(),
            "evaluation_model": get_openrouter_evaluation_model(),
        },
        "langsmith": langsmith_status,
        "environment": {
            "OPENROUTER_API_KEY": "✅ Set" if openrouter_key else "❌ Missing",
            "LANGCHAIN_API_KEY": "✅ Set" if get_langsmith_api_key() else "⚪ Optional",
            "LANGCHAIN_TRACING_V2": os.environ.get("LANGCHAIN_TRACING_V2", "false"),
            "LANGCHAIN_PROJECT": os.environ.get("LANGCHAIN_PROJECT", "Not set"),
        },
    }


# Load environment variables when this module is imported (only once)
load_env_file()

# Setup LangSmith if configured (only once)
setup_langsmith()
