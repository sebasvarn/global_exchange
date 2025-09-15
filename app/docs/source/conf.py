# docs/source/conf.py

from pathlib import Path
import os
import sys
import importlib
import django
from django.conf import settings
from datetime import datetime

# Configuración principal del proyecto
DJANGO_PROJECT_PACKAGE = "global_exchange"

# Documento raíz y tipos de archivos fuente
root_doc = "index"
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

# Agrega el directorio raíz del proyecto al path
app_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(app_dir))

# Inicializa Django con la configuración de desarrollo
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{DJANGO_PROJECT_PACKAGE}.settings.dev")
django.setup()

# Metadatos del proyecto
project = DJANGO_PROJECT_PACKAGE
author = "Grupo 10"
language = "es"
copyright = f"{datetime.now().year}, {author}"

# Extensiones de Sphinx utilizadas
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "autoapi.extension",
    "sphinxcontrib.mermaid",
]

# Configuración de tema y rutas de archivos estáticos
html_theme = "sphinx_rtd_theme"
templates_path = ["_templates"]
html_static_path = [""]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**/__pycache__/**"]

# Extensiones extra para MyST
myst_enable_extensions = ["linkify", "deflist", "tasklist"]

# Mapeo para documentación externa (intersphinx)
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": ("https://docs.djangoproject.com/en/stable/", None),
}

# Opciones de autodoc/autosummary
autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    # Si necesitas ver miembros privados y dunder, descomenta:
    # "private-members": True,
    # "special-members": "__init__,__call__",
    # "inherited-members": True,
}

# Helpers para descubrimiento de módulos locales
def _is_local_module(mod_path: str) -> bool:
    try:
        p = Path(mod_path).resolve()
        return str(p).startswith(str(app_dir)) and "site-packages" not in str(p)
    except Exception:
        return False

def _import_any_prefix(dotted: str):
    """
    Importa el módulo más largo posible desde un string con puntos.
    Ejemplo: "usuarios.apps.UsuariosConfig" -> "usuarios"
    """
    parts = dotted.split(".")
    while parts:
        name = ".".join(parts)
        try:
            return importlib.import_module(name)
        except Exception:
            parts.pop()
    return None

# Descubrimiento de directorios para AutoAPI
autoapi_dirs_set = set()

# Agrega el paquete raíz del proyecto si es local
try:
    pkg = importlib.import_module(DJANGO_PROJECT_PACKAGE)
    if getattr(pkg, "__file__", None) and _is_local_module(pkg.__file__):
        autoapi_dirs_set.add(str(Path(pkg.__file__).resolve().parent))
except Exception:
    pass

# Agrega todas las apps locales en INSTALLED_APPS
for app in settings.INSTALLED_APPS:
    if app.startswith(("django.", "rest_framework", "drf_", "sphinx", "autoapi", "myst_parser")):
        continue
    mod = _import_any_prefix(app)
    if mod and getattr(mod, "__file__", None) and _is_local_module(mod.__file__):
        autoapi_dirs_set.add(str(Path(mod.__file__).resolve().parent))

autoapi_dirs = sorted(autoapi_dirs_set)

# Fallback: si no se encontró nada, apunta al paquete raíz o al repo completo
if not autoapi_dirs:
    fallback = (app_dir / DJANGO_PROJECT_PACKAGE)
    if fallback.exists():
        autoapi_dirs = [str(fallback)]
    else:
        autoapi_dirs = [str(app_dir)]

# Opciones de AutoAPI
autoapi_type = "python"
autoapi_add_toctree_entry = True
autoapi_keep_files = False
autoapi_options = [
    "members",
    "undoc-members",
    "private-members",
    "special-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]
autoapi_ignore = [
    "*/migrations/*",
    "*/tests/*",
    "*/__pycache__/*",
    "manage.py",
    "docs/*",
    "venv/*",
    ".venv/*",
]

# Log de los directorios escaneados por AutoAPI
print("[AutoAPI] Escaneando directorios:", *autoapi_dirs, sep="\n - ")
