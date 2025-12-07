# src/components/cookie_manager/cookie_manager.py

import streamlit.components.v1 as components
from pathlib import Path

# Ruta a carpeta frontend
_frontend_dir = Path(__file__).parent / "frontend"
_dist_dir = Path(__file__).resolve().parent / "dist"

cookie_component = components.declare_component(
    "cookie_manager_component",
    path=str(_frontend_dir)  # SUPER IMPORTANTE
)

class CookieManager:

    def get(self, name: str, key=None): # Se agregó 'key'
        # Se agregan 'key' y 'default' para asegurar el comportamiento inicial y manejar duplicados.
        return cookie_component(
            action="get", 
            name=name,
            key=key,        # ¡IMPORTANTE! Se pasa la clave
            default=None    # Se establece el valor predeterminado, ya que la cookie puede ser None.
        )

    def set(self, name: str, value: str, days: int = 7, samesite="Lax", key=None): # Se agregó 'key'
        cookie_component(
            action="set",
            name=name,
            value=value,
            days=days,
            samesite=samesite,
            key=key         # ¡IMPORTANTE! Se pasa la clave
        )

    def delete(self, name: str, key=None): # Se agregó 'key'
        cookie_component(
            action="delete", 
            name=name,
            key=key         # ¡IMPORTANTE! Se pasa la clave
        )


