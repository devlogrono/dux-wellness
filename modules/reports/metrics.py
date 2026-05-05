from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from typing import Optional
import streamlit as st 

@dataclass
class RPEFilters:
    jugadores: Optional[list[str]] = None
    turnos: Optional[list[str]] = None
    start: Optional[date] = None
    end: Optional[date] = None

def _prepare_checkout_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deja preparado el dataset para métricas de carga:
    - solo registros checkout
    - tipo normalizado
    - ua y minutos_sesion numéricos
    - fecha_sesion como date
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    # -------------------------
    # Normalizar tipo
    # -------------------------
    if "tipo" in out.columns:
        out["tipo"] = out["tipo"].astype(str).str.strip().str.lower()
        out = out[out["tipo"] == "checkout"]
    # -------------------------
    # Asegurar UA numérica
    # -------------------------
    if "ua" in out.columns:
        out["ua"] = pd.to_numeric(out["ua"], errors="coerce")
    else:
        out["ua"] = np.nan
    # -------------------------
    # Asegurar minutos numéricos
    # -------------------------
    if "minutos_sesion" in out.columns:
        out["minutos_sesion"] = pd.to_numeric(out["minutos_sesion"], errors="coerce")
    else:
        out["minutos_sesion"] = 0
    # -------------------------
    # Asegurar fecha_sesion
    # -------------------------
    if "fecha_sesion" in out.columns:
        out["fecha_sesion"] = pd.to_datetime(out["fecha_sesion"], errors="coerce").dt.date
    else:
        out["fecha_sesion"] = pd.NaT
    # -------------------------
    # Limpiar filas inválidas
    # -------------------------
    out = out.dropna(subset=["fecha_sesion", "ua"]).copy()

    return out

def _daily_loads(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la carga diaria y devuelve una serie continua por días.
    Los días sin sesión se rellenan con 0.
    """
    if df.empty:
        return pd.DataFrame(columns=["fecha_sesion", "ua_total", "minutos_total"])

    out = df.copy()

    if "ua" not in out.columns:
        out["ua"] = 0
    if "minutos_sesion" not in out.columns:
        out["minutos_sesion"] = 0

    daily = (
        out.groupby("fecha_sesion", as_index=False)[["ua", "minutos_sesion"]]
        .sum(min_count=1)
        .rename(columns={"ua": "ua_total", "minutos_sesion": "minutos_total"})
        .sort_values("fecha_sesion")
    )

    daily["fecha_sesion"] = pd.to_datetime(daily["fecha_sesion"], errors="coerce")

    daily = (
        daily.set_index("fecha_sesion")
        .asfreq("D")
        .fillna({"ua_total": 0, "minutos_total": 0})
        .reset_index()
    )

    daily["fecha_sesion"] = daily["fecha_sesion"].dt.date

    return daily

#NOSEUSA
def _current_week_range(end_day: date) -> tuple[date, date]:
    # Monday to Sunday containing end_day
    weekday = end_day.weekday()  # Monday=0
    start = end_day - timedelta(days=weekday)
    end = start + timedelta(days=6)
    return start, end

def _month_range(end_day: date) -> tuple[date, date]:
    start = end_day.replace(day=1)
    if start.month == 12:
        next_month_start = start.replace(year=start.year + 1, month=1, day=1)
    else:
        next_month_start = start.replace(month=start.month + 1, day=1)
    end = next_month_start - timedelta(days=1)
    return start, end

#NOSEUSA
def _chronic_load(daily: pd.DataFrame, end_day: date, days: int) -> float:
    """
    Calcula carga crónica como media diaria de UA
    en una ventana de 'days' días naturales.
    La serie diaria ya incluye días sin sesión como 0.
    """
    start = end_day - timedelta(days=days - 1)

    window = daily[
        (daily["fecha_sesion"] >= start) &
        (daily["fecha_sesion"] <= end_day)
    ].copy()

    return float(window["ua_total"].mean()) if not window.empty else 0.0

def compute_rpe_metrics(df_raw: pd.DataFrame, flt: RPEFilters) -> dict:
    """
    Calcula métricas de carga interna a partir de registros checkout.

    Lógica:
    - carga_total_periodo / carga_media_periodo -> dependen del rango seleccionado
    - fatiga aguda -> siempre 7 días
    - fatiga crónica -> siempre 28 / 42 / 56 días
    - días sin carga dentro de cada ventana cuentan como 0
    """
    df = _prepare_checkout_df(df_raw)

    res: dict = {
        "ua_total_dia": 0.0,
        "minutos_sesion": 0.0,

        # dinámicas según rango seleccionado
        "carga_total_periodo": 0.0,
        "carga_media_periodo": 0.0,

        # compatibilidad
        "carga_semana": 0.0,
        "carga_mes": 0.0,
        "carga_media_semana": 0.0,
        "carga_media_mes": 0.0,

        "monotonia_semana": None,
        "variabilidad_semana": 0.0,
        "fatiga_aguda": 0.0,
        "fatiga_aguda_7d_media": 0.0,
        "fatiga_cronica_28d": 0.0,
        "fatiga_cronica_42d": 0.0,
        "fatiga_cronica_56d": 0.0,
        "estado_forma_28d": None,
        "estado_forma_42d": None,
        "estado_forma_56d": None,
        "acwr_28d": None,
        "acwr_42d": None,
        "acwr_56d": None,
        "daily_table": pd.DataFrame(),
    }

    if df.empty:
        return res

    daily = _daily_loads(df)
    if daily.empty:
        return res

    daily_dt = daily.copy()
    daily_dt["fecha_sesion"] = pd.to_datetime(daily_dt["fecha_sesion"], errors="coerce")
    daily_dt = daily_dt.dropna(subset=["fecha_sesion"]).sort_values("fecha_sesion")

    if daily_dt.empty:
        return res

    res["daily_table"] = daily.copy()

    # =========================
    # Fechas de referencia
    # =========================
    end_day = flt.end or daily_dt["fecha_sesion"].dt.date.max()
    start_periodo = flt.start or daily_dt["fecha_sesion"].dt.date.min()
    end_periodo = flt.end or daily_dt["fecha_sesion"].dt.date.max()

    # =========================
    # Auxiliar: ventana general con ceros
    # =========================
    def _build_window(start_day: date, end_day_window: date) -> pd.DataFrame:
        idx = pd.date_range(
            start=pd.to_datetime(start_day),
            end=pd.to_datetime(end_day_window),
            freq="D"
        )

        window = (
            daily_dt.set_index("fecha_sesion")[["ua_total", "minutos_total"]]
            .reindex(idx, fill_value=0)
            .rename_axis("fecha_sesion")
            .reset_index()
        )

        window["fecha_sesion"] = window["fecha_sesion"].dt.date
        return window

    # =========================
    # Periodo seleccionado (dinámico)
    # =========================
    daily_period = _build_window(start_periodo, end_periodo)
    res["carga_total_periodo"] = float(daily_period["ua_total"].sum())
    res["carga_media_periodo"] = float(daily_period["ua_total"].mean()) if not daily_period.empty else 0.0

    # =========================
    # Ventana 7 días fija
    # =========================
    daily_last7 = _build_window(end_day - timedelta(days=6), end_day)

    semana_sum = float(daily_last7["ua_total"].sum())
    semana_mean = float(daily_last7["ua_total"].mean())
    semana_std = float(daily_last7["ua_total"].std(ddof=0)) if len(daily_last7) > 1 else 0.0

    res["carga_semana"] = semana_sum
    res["carga_media_semana"] = semana_mean
    res["monotonia_semana"] = float(semana_mean / semana_std) if semana_std > 0 else None
    res["variabilidad_semana"] = semana_std

    # =========================
    # Métrica diaria exacta del end_day
    # =========================
    day_row = daily_last7[daily_last7["fecha_sesion"] == end_day]
    res["ua_total_dia"] = float(day_row["ua_total"].iloc[0]) if not day_row.empty else 0.0
    res["minutos_sesion"] = float(day_row["minutos_total"].iloc[0]) if not day_row.empty else 0.0

    # =========================
    # Métricas mensuales visibles
    # =========================
    m_start, m_end = _month_range(end_day)
    daily_month = _build_window(m_start, m_end)

    res["carga_mes"] = float(daily_month["ua_total"].sum()) if not daily_month.empty else 0.0
    res["carga_media_mes"] = float(daily_month["ua_total"].mean()) if not daily_month.empty else 0.0

    # =========================
    # Fatiga aguda 7d
    # =========================
    fatiga_aguda_total = float(daily_last7["ua_total"].sum())
    fatiga_aguda_media = float(daily_last7["ua_total"].mean())

    res["fatiga_aguda"] = fatiga_aguda_total
    res["fatiga_aguda_7d_media"] = fatiga_aguda_media

    # =========================
    # Fatiga crónica con ventanas fijas
    # =========================
    daily_28 = _build_window(end_day - timedelta(days=27), end_day)
    daily_42 = _build_window(end_day - timedelta(days=41), end_day)
    daily_56 = _build_window(end_day - timedelta(days=55), end_day)

    res["fatiga_cronica_28d"] = float(daily_28["ua_total"].mean())
    res["fatiga_cronica_42d"] = float(daily_42["ua_total"].mean())
    res["fatiga_cronica_56d"] = float(daily_56["ua_total"].mean())

    # =========================
    # Estado de forma
    # =========================
    res["estado_forma_28d"] = res["fatiga_cronica_28d"] - fatiga_aguda_media
    res["estado_forma_42d"] = res["fatiga_cronica_42d"] - fatiga_aguda_media
    res["estado_forma_56d"] = res["fatiga_cronica_56d"] - fatiga_aguda_media

    # =========================
    # ACWR
    # =========================
    res["acwr_28d"] = (
        fatiga_aguda_media / res["fatiga_cronica_28d"]
        if res["fatiga_cronica_28d"] > 0 else None
    )
    res["acwr_42d"] = (
        fatiga_aguda_media / res["fatiga_cronica_42d"]
        if res["fatiga_cronica_42d"] > 0 else None
    )
    res["acwr_56d"] = (
        fatiga_aguda_media / res["fatiga_cronica_56d"]
        if res["fatiga_cronica_56d"] > 0 else None
    )

    return res

# def compute_rpe_timeseries(
#     df: pd.DataFrame,
#     ventana_aguda: int = 7,
#     ventana_cronica: int = 42,
# ) -> pd.DataFrame:
#     """
#     Genera un DataFrame diario continuo con estados de carga interna:
#     - UA diaria
#     - Fatiga aguda (media móvil, UA/día)
#     - Fatiga crónica (media móvil, UA/día)
#     - Recuperación (crónica - aguda)
#     - ACWR

#     Todas las métricas están en UA/día y son graficables.
#     """

#     if df is None or df.empty:
#         return pd.DataFrame()

#     df = df.copy()

#     # -------------------------
#     # Asegurar fecha
#     # -------------------------
#     df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce")
#     df = df.dropna(subset=["fecha_sesion"])

#     # -------------------------
#     # UA diaria (suma por día)
#     # -------------------------
#     daily = (
#         df.groupby("fecha_sesion", as_index=False)["ua"]
#         .sum()
#         .rename(columns={"ua": "ua_diaria"})
#         .set_index("fecha_sesion")
#         .asfreq("D")
#     )

#     # Días sin sesión = 0 UA
#     daily["ua_diaria"] = daily["ua_diaria"].fillna(0)

#     # -------------------------
#     # Fatiga aguda (7d)
#     # -------------------------
#     daily["fatiga_aguda_7d"] = (
#         daily["ua_diaria"]
#         .rolling(window=ventana_aguda, min_periods=1)
#         .mean()
#     )

#     # -------------------------
#     # Fatiga crónica (Xd)
#     # -------------------------
#     daily[f"fatiga_cronica_{ventana_cronica}d"] = (
#         daily["ua_diaria"]
#         .rolling(window=ventana_cronica, min_periods=1)
#         .mean()
#     )

#     # -------------------------
#     # Recuperación (Xd)
#     # -------------------------
#     daily[f"recuperacion_{ventana_cronica}d"] = (
#         daily[f"fatiga_cronica_{ventana_cronica}d"]
#         - daily["fatiga_aguda_7d"]
#     )

#     # -------------------------
#     # ACWR (Xd)
#     # -------------------------
#     daily[f"acwr_{ventana_cronica}d"] = (
#         daily["fatiga_aguda_7d"]
#         / daily[f"fatiga_cronica_{ventana_cronica}d"]
#     )

#     columnas_numericas = daily.select_dtypes(include="number").columns
#     daily[columnas_numericas] = daily[columnas_numericas].round(2)

#     return daily.reset_index()

def _ema(series: pd.Series, tau: int) -> pd.Series:
    """
    Exponential Moving Average equivalente al Excel (modelo Banister).
    tau = constante de tiempo (7, 28, 42, 56…)
    """
    alpha = 1 - np.exp(-1 / tau)
    return series.ewm(alpha=alpha, adjust=False).mean()


def compute_rpe_timeseries(
    df: pd.DataFrame,
    ventana_aguda: int = 7,
    ventana_cronica: int = 42,
) -> pd.DataFrame:
    """
    Genera un DataFrame diario continuo con estados de carga interna.
    Incluye SMA y EMA.
    """

    df = _prepare_checkout_df(df)

    if df is None or df.empty:
        return pd.DataFrame()

    daily = _daily_loads(df).copy()

    if daily.empty:
        return pd.DataFrame()

    daily["fecha_sesion"] = pd.to_datetime(daily["fecha_sesion"], errors="coerce")
    daily = daily.dropna(subset=["fecha_sesion"]).sort_values("fecha_sesion")

    daily = daily.rename(columns={"ua_total": "ua_diaria"})

    # SMA
    daily[f"fatiga_aguda_{ventana_aguda}d_sma"] = (
        daily["ua_diaria"]
        .rolling(window=ventana_aguda, min_periods=1)
        .mean()
    )

    daily[f"fatiga_cronica_{ventana_cronica}d_sma"] = (
        daily["ua_diaria"]
        .rolling(window=ventana_cronica, min_periods=1)
        .mean()
    )

    daily[f"estado_forma_{ventana_cronica}d_sma"] = (
        daily[f"fatiga_cronica_{ventana_cronica}d_sma"]
        - daily[f"fatiga_aguda_{ventana_aguda}d_sma"]
    )

    daily[f"acwr_{ventana_cronica}d_sma"] = (
        daily[f"fatiga_aguda_{ventana_aguda}d_sma"]
        / daily[f"fatiga_cronica_{ventana_cronica}d_sma"]
    )

    # EMA
    daily[f"fatiga_aguda_{ventana_aguda}d_ema"] = _ema(
        daily["ua_diaria"],
        ventana_aguda
    )

    daily[f"fatiga_cronica_{ventana_cronica}d_ema"] = _ema(
        daily["ua_diaria"],
        ventana_cronica
    )

    daily[f"estado_forma_{ventana_cronica}d_ema"] = (
        daily[f"fatiga_cronica_{ventana_cronica}d_ema"]
        - daily[f"fatiga_aguda_{ventana_aguda}d_ema"]
    )

    daily[f"acwr_{ventana_cronica}d_ema"] = (
        daily[f"fatiga_aguda_{ventana_aguda}d_ema"]
        / daily[f"fatiga_cronica_{ventana_cronica}d_ema"]
    )

    num_cols = daily.select_dtypes(include="number").columns
    daily[num_cols] = daily[num_cols].round(2)

    return daily.reset_index(drop=True)


def compute_cambio_carga(df_states: pd.DataFrame) -> float | None:
    """
    Calcula el % de cambio de carga:
    últimos 3 días vs 3 días anteriores.
    """

    if df_states is None or df_states.empty:
        return None

    df = df_states.copy().sort_values("fecha_sesion")

    if len(df) < 6:
        return None

    last3 = df["ua_diaria"].tail(3).mean()
    prev3 = df["ua_diaria"].tail(6).head(3).mean()

    if prev3 == 0:
        return None

    cambio = (last3 / prev3) - 1
    return cambio


def compute_dias_riesgo(df_states: pd.DataFrame, ventana: int = 14) -> int:
    """
    Cuenta cuántos días ACWR > 1.5 en la ventana reciente.
    """

    if df_states is None or df_states.empty:
        return 0

    df = df_states.copy().sort_values("fecha_sesion")

    col = "acwr_42d_sma"  # usa SMA para estabilidad

    if col not in df.columns:
        return 0

    recent = df.tail(ventana)

    dias = (recent[col] > 1.5).sum()
    return int(dias)

