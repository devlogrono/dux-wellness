
import streamlit as st
import modules.app_config.config as config

from modules.i18n.i18n import t

config.init_config()

from modules.ui.ui_components import selection_header
from modules.reports.ui_grupal import group_dashboard, metricas_grupal, build_calculation_window
from modules.db.db_records import get_records_db
from modules.db.db_players import load_players_db
from modules.db.db_competitions import load_competitions_db
from modules.reports.wellness_processing import (prepare_players, prepare_wellness_dataset)

st.header(t("Análisis :red[grupal]"), divider="red")

# Load reference data
jug_df = load_players_db()
comp_df = load_competitions_db()
#wellness_df = get_records_db()

#df, jugadora, tipo, turno, start, end = selection_header(jug_df, comp_df, wellness_df, modo="reporte_grupal")

# Raw data
wellness_df = get_records_db()

# Preparar players
jug_df = prepare_players(jug_df)

# Preparar dataset wellness
wellness_df_prepared = prepare_wellness_dataset(wellness_df, jug_df)

# Filtros UI
df_visual, jugadora, tipo, turno, start, end = selection_header(
    jug_df, comp_df, wellness_df_prepared, modo="reporte_grupal"
)

df_calculo = build_calculation_window(wellness_df_prepared, start=start, end=end, lookback_days=56)

metricas_grupal(df_calculo, jugadora, turno, start, end)
#st.dataframe(df, hide_index=True)
group_dashboard(df_visual, df_calculo,start,end)
