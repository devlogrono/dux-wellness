import streamlit as st

def build_user_access_filter(
    table_alias: str | None = None,
    column: str = "usuario"
):
    """
    Construye el filtro SQL de acceso por usuario según el rol.

    developer → ve todo
    admin → ve todo excepto registros del developer
    otros → solo sus registros

    Retorna:
        sql_filter (str)
        params (tuple)
    """

    rol = st.session_state["auth"]["rol"].lower()
    username = st.session_state["auth"]["username"].lower()

    col = f"{table_alias}.{column}" if table_alias else column

    if rol == "developer":
        return "1=1", ()

    elif rol == "admin":
        return f"{col} != 'developer'", ()

    else:
        return f"{col} = %s", (username,)