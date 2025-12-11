import streamlit as st
import uuid

class KeyBuilder:
    """Genera keys únicas basadas en usuario + sesión + widget."""
    
    def __init__(self):
        # Usuario autenticado
        user = st.session_state.get("auth", {}).get("username", "anon")
        session = st.session_state.get("auth", {}).get("session_id", "")

        # Prefijo único y estable por usuario + sesión
        self.prefix = f"{user}_{session}"

        # Evita inconsistencias si session_id aún no existe
        if not session:
            self.prefix = f"{user}_{uuid.uuid4().hex[:6]}"

    def key(self, name: str) -> str:
        """Devuelve una key única para un widget del formulario."""
        return f"{self.prefix}_{name}"
