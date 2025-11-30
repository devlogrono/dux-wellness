
import streamlit as st
from src.db.db_catalogs import load_catalog_list_db
import src.app_config.config as config
config.init_config()

#from src.ui.ui_components import selection_header
from src.i18n.i18n import t
from src.auth_system.auth_core import init_app_state, validate_login
from src.auth_system.auth_ui import login_view, menu
from src.db.db_records import load_jugadoras_db, load_competiciones_db, load_ausencias_activas_db
from src.ui.absents_ui import absents_form, absents_summary

init_app_state()
validate_login()

if st.session_state["auth"]["rol"].lower() not in ["admin", "developer"]:
    st.switch_page("app.py")
    
# Authentication gate
if not st.session_state["auth"]["is_logged_in"]:
    login_view()
    st.stop()
menu()

st.header(t(":red[Ausencias]"), divider="red")

# Load reference data
jug_df = load_jugadoras_db()
comp_df = load_competiciones_db()
tipo_ausencia_df = load_catalog_list_db("tipo_ausencia", as_df=True)
ausencias_df = load_ausencias_activas_db()

tab1, tab2= st.tabs([ "Registrar Ausencia", "Reporte de Ausencias"])

with tab1:
    absents_form(comp_df, jug_df, tipo_ausencia_df, ausencias_df)
with tab2:
    absents_summary(ausencias_df)