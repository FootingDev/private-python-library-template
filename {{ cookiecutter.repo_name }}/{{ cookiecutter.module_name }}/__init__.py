from {{ cookiecutter.module_name }}.version import __version__

{% if cookiecutter._pr -%}
from .hello import say_hello

{% endif -%}
__all__ = ["__version__", {% if cookiecutter._pr %}"say_hello"{% endif %}]
