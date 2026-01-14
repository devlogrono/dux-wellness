import pandas as pd
import json

from modules.db.db_client import query
from modules.db.db_catalogs import load_catalog_list_db

def get_wellness_pre_lesion(
    id_jugadora: str | None = None,
    dias_previos: int = 14,
    as_df: bool = True,
):
    """
    Obtiene registros de wellness previos a lesiones ACTIVAS u OBSERVACION.

    - Usa fecha_lesion como punto de corte
    - Ventana configurable (default: 14 días)
    - Puede devolver datos de todas las jugadoras o de una específica
    """

    # ----------------------------
    # Catálogo zonas anatómicas
    # ----------------------------
    zonas_df = load_catalog_list_db("zonas_anatomicas", as_df=True)
    map_zonas = dict(zip(zonas_df["id"], zonas_df["nombre"]))

    # ----------------------------
    # Filtro opcional por jugadora
    # ----------------------------
    jugadora_filter = ""
    params = {"dias": dias_previos}

    if id_jugadora:
        jugadora_filter = "AND l.id_jugadora = %(id_jugadora)s"
        params["id_jugadora"] = id_jugadora

    # ----------------------------
    # Query CORREGIDA
    # ----------------------------
    sql = f"""
        SELECT
            l.id_lesion,
            l.id_jugadora,
            l.fecha_lesion,
            l.estado_lesion,
            l.tipo_lesion_id,
            l.segmento_id,
            l.zona_cuerpo_id,
            l.zona_especifica_id,
            l.lateralidad,
            l.es_recidiva,

            w.id AS id_wellness,
            w.fecha_sesion,
            w.tipo,
            w.turno,
            w.recuperacion,
            w.fatiga AS energia,
            w.sueno,
            w.stress,
            w.dolor,
            w.id_zona_segmento_dolor,
            w.zonas_anatomicas_dolor,
            w.lateralidad_dolor,
            w.minutos_sesion,
            w.rpe,
            w.ua,
            w.periodizacion_tactica,
            w.observacion

        FROM lesiones l
        INNER JOIN wellness w
            ON w.id_jugadora = l.id_jugadora
           AND w.fecha_sesion BETWEEN
               DATE_SUB(l.fecha_lesion, INTERVAL %(dias)s DAY)
               AND l.fecha_lesion
           AND w.estatus_id <= 2

        WHERE l.deleted_at IS NULL
          AND l.estado_lesion IN ('ACTIVO', 'OBSERVACION')
          {jugadora_filter}

        ORDER BY l.id_jugadora, l.fecha_lesion, w.fecha_sesion;
    """

    rows = query(sql, params)

    if not rows:
        return pd.DataFrame() if as_df else []

    df = pd.DataFrame(rows)

    # ----------------------------
    # Procesar JSON zonas dolor
    # ----------------------------
    df["zonas_anatomicas_dolor"] = df["zonas_anatomicas_dolor"].apply(
        lambda x: json.loads(x)
        if isinstance(x, str) and x.strip().startswith("[")
        else []
    )

    df["zonas_anatomicas_dolor_nombre"] = df["zonas_anatomicas_dolor"].apply(
        lambda ids: [map_zonas.get(i, f"ID {i}") for i in ids]
    )

    # ----------------------------
    # Normalizar fechas
    # ----------------------------
    df["fecha_sesion"] = pd.to_datetime(df["fecha_sesion"], errors="coerce").dt.date
    df["fecha_lesion"] = pd.to_datetime(df["fecha_lesion"], errors="coerce").dt.date

    return df if as_df else df.to_dict("records")
