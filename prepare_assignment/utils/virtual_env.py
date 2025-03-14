import os


def is_virtualenv_active() -> bool:
    """Check if a virtual environment is active (including Poetry environments)."""
    # Check if the VIRTUAL_ENV environment variable is set, which indicates a virtualenv is active
    return os.getenv("VIRTUAL_ENV") is not None


def get_virtualenv_name() -> str:
    """Get the name of the active virtual environment (works with Poetry as well)."""
    virtualenv_path = os.getenv("VIRTUAL_ENV")
    if virtualenv_path:
        return os.path.basename(virtualenv_path)  # Get the name from the virtualenv path
    return "None (not active)"
