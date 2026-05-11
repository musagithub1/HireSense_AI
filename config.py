"""
config.py
=========

Configuration management for HireSense AI.
Handles loading environment variables from .env file and LangSmith integration.
"""

import os
from pathlib import Path

# Global flags to prevent repeated initialization
# Using a dict to maintain state across module reloads
_init_state = {
    'env_loaded': False,
    'langsmith_initialized': False,
    'langsmith_status': None
}


def load_env_file():
    """
    Load environment variables from .env file.
    This function should be called at the very start of the application.
    Only runs once per session.
    """
    # Prevent repeated loading
    if _init_state['env_loaded']:
        return True
    
    # Find the .env file - check current directory and parent directories
    possible_paths = [
        Path(__file__).parent / ".env",  # Same directory as this file
        Path.cwd() / ".env",  # Current working directory
        Path.home() / ".env",  # Home directory
    ]
    
    env_file = None
    for path in possible_paths:
        if path.exists():
            env_file = path
            break
    
    if env_file is None:
        print("⚠️ No .env file found. Please create one from .env.example")
        print("   Looking in:", [str(p) for p in possible_paths])
        _init_state['env_loaded'] = True  # Mark as loaded to prevent repeated warnings
        return False
    
    print(f"📁 Loading environment from: {env_file}")
    
    # Parse and load the .env file
    loaded_vars = []
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    # Only set if not already in environment (don't override)
                    if key and value and key not in os.environ:
                        os.environ[key] = value
                        loaded_vars.append(key)
    
    except Exception as e:
        print(f"❌ Error loading .env file: {e}")
        _init_state['env_loaded'] = True
        return False
    
    if loaded_vars:
        print(f"✅ Loaded {len(loaded_vars)} environment variables: {', '.join(loaded_vars)}")
    
    _init_state['env_loaded'] = True
    return True


def get_openrouter_api_key():
    """Get the OpenRouter API key from environment."""
    return os.environ.get("OPENROUTER_API_KEY")


def get_langsmith_api_key():
    """Get the LangSmith API key from environment."""
    return os.environ.get("LANGCHAIN_API_KEY")


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
    if _init_state['langsmith_initialized'] and _init_state['langsmith_status'] is not None:
        return _init_state['langsmith_status']
    
    status = {
        "enabled": False,
        "project": None,
        "endpoint": None,
        "message": ""
    }
    
    api_key = get_langsmith_api_key()
    
    # Check if API key is set and not placeholder
    if not api_key:
        status["message"] = "LangSmith API key not set (optional)"
        _init_state['langsmith_initialized'] = True
        _init_state['langsmith_status'] = status
        return status
    
    if api_key == "your_langsmith_api_key_here":
        status["message"] = "LangSmith API key is placeholder - update .env to enable"
        _init_state['langsmith_initialized'] = True
        _init_state['langsmith_status'] = status
        return status
    
    # Check if tracing is enabled
    tracing_enabled = os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
    if not tracing_enabled:
        # Enable it automatically if API key is set
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    
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
    if not _init_state['langsmith_initialized']:
        print(f"🔍 {status['message']}")
    
    _init_state['langsmith_initialized'] = True
    _init_state['langsmith_status'] = status
    
    return status


def disable_langsmith():
    """
    Disable LangSmith tracing to prevent API errors.
    Call this if you don't have a valid LangSmith API key.
    """
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    if _init_state['langsmith_status']:
        _init_state['langsmith_status']["enabled"] = False
        _init_state['langsmith_status']["message"] = "LangSmith tracing disabled"


def validate_config():
    """Validate that required configuration is present."""
    api_key = get_openrouter_api_key()
    
    if not api_key:
        return False, "OPENROUTER_API_KEY is not set. Please add it to your .env file."
    
    if api_key == "your_openrouter_api_key_here":
        return False, "OPENROUTER_API_KEY is still set to the placeholder value. Please update your .env file with your actual API key."
    
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
            "configured": bool(openrouter_key and openrouter_key != "your_openrouter_api_key_here"),
            "key_preview": f"{openrouter_key[:10]}..." if openrouter_key and len(openrouter_key) > 10 else "Not set"
        },
        "langsmith": langsmith_status,
        "environment": {
            "OPENROUTER_API_KEY": "✅ Set" if openrouter_key else "❌ Missing",
            "LANGCHAIN_API_KEY": "✅ Set" if get_langsmith_api_key() else "⚪ Optional",
            "LANGCHAIN_TRACING_V2": os.environ.get("LANGCHAIN_TRACING_V2", "false"),
            "LANGCHAIN_PROJECT": os.environ.get("LANGCHAIN_PROJECT", "Not set"),
        }
    }


# Load environment variables when this module is imported (only once)
load_env_file()

# Setup LangSmith if configured (only once)
setup_langsmith()
