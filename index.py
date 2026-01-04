import geopandas as gpd
import numpy as np
import pandas as pd
from rasterstats import zonal_stats
import rasterio
from rasterio.enums import Resampling
import glob
import warnings
import argparse
import os
import re

warnings.filterwarnings("ignore", category=RuntimeWarning)


# =========================
# CONFIGURAÇÕES
# =========================
SHAPEFILE = "municipios/BR_Municipios_2024.shp"
RASTER_GLOB = "raster_brasil/wc2.1_30s_tavg_*.tif"
OUTPUT = "temperatura_media_por_municipio.csv"

# Limites plausíveis em °C (após aplicar escala)
MIN_TEMP_C = -20.0
MAX_TEMP_C = 50.0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calcula estatísticas zonais de temperatura (WorldClim) por município."
    )
    parser.add_argument(
        "--mes",
        type=int,
        choices=range(1, 13),
        help="Processa apenas um mês (1-12) para teste (ex.: --mes 1).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Imprime diagnósticos (nodata/min/max/contagem de válidos) para ajudar a depurar NaNs.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        help="Para teste: processa apenas os N primeiros municípios (ex.: --limite 50).",
    )
    parser.add_argument(
        "--escala",
        type=float,
        choices=(1.0, 0.1),
        help="Força a escala para converter o raster em °C: 1.0 (já em °C) ou 0.1 (raster em °C*10).",
    )
    return parser.parse_args()


def _detect_scale_from_array(data: np.ndarray, nodata: float | None) -> float:
    # Heurística simples: se os valores máximos passam de ~80, normalmente é °C*10.
    if nodata is None:
        valid = np.isfinite(data)
    else:
        valid = np.isfinite(data) & (data != float(nodata))
    if not np.any(valid):
        return 1.0
    vmax = float(np.max(data[valid]))
    return 0.1 if vmax > 80.0 else 1.0


def _pick_raster_for_month(rasters: list[str], month: int) -> list[str]:
    # Preferência: arquivo contendo tavg_{MM} no nome.
    mm = f"{month:02d}"
    for path in rasters:
        if f"tavg_{mm}" in os.path.basename(path):
            return [path]

    # Fallback: tenta encontrar sufixo _MM.tif
    suffix = f"_{mm}.tif"
    for path in rasters:
        if path.lower().endswith(suffix):
            return [path]

    # Último fallback: assume ordem (1..12) na lista.
    if 1 <= month <= len(rasters):
        return [rasters[month - 1]]

    raise RuntimeError(f"Não encontrei raster para o mês {month:02d}.")

# =========================
# 1. MUNICÍPIOS
# =========================
args = _parse_args()

municipios = gpd.read_file(SHAPEFILE).to_crs(epsg=4326)
print(f"Municípios carregados: {len(municipios)}")
invalid = ~municipios.is_valid
municipios.loc[invalid, "geometry"] = municipios.loc[invalid, "geometry"].buffer(0)
print("Municipios bounds:", municipios.total_bounds)
print(municipios.is_valid.value_counts())

if args.limite is not None:
    if args.limite <= 0:
        raise ValueError("--limite deve ser um inteiro positivo.")
    municipios = municipios.head(args.limite).copy()
    print(f"Modo teste: limitando para {len(municipios)} municípios")

# =========================
# 2. RASTERS
# =========================
rasters_all = sorted(glob.glob(RASTER_GLOB))
if len(rasters_all) == 0:
    raise RuntimeError(f"Nenhum raster encontrado com o padrão: {RASTER_GLOB}")

if args.mes is not None:
    rasters = _pick_raster_for_month(rasters_all, args.mes)
else:
    rasters = rasters_all
    if len(rasters) != 12:
        raise RuntimeError("Esperado 12 rasters (1 por mês). Use --mes N para testar só 1 mês.")

print(f"Rasters selecionados: {len(rasters)}")
if args.mes is not None:
    print(f"Modo teste: apenas mês {args.mes:02d}")

with rasterio.open(rasters[0]) as r:
    print("Raster CRS:", r.crs)
    print("Raster bounds:", r.bounds)


# =========================
# 3. ZONAL STATS (SEM OVERFLOW)
# =========================
stats_mensais = []
scale_to_c = args.escala

for raster in rasters:
    print(f"Processando {raster}...")

    with rasterio.open(raster) as src:
        data = src.read(1, out_dtype="float32", resampling=Resampling.nearest)

        if scale_to_c is None:
            scale_to_c = _detect_scale_from_array(data, src.nodata)
            if args.debug:
                print(f"  debug: escala escolhida para °C = {scale_to_c}")

        if args.debug:
            nodata = src.nodata
            if nodata is None:
                valid = np.isfinite(data)
            else:
                valid = np.isfinite(data) & (data != float(nodata))
            valid_count = int(valid.sum())
            total = int(data.size)
            if valid_count > 0:
                vmin = float(np.min(data[valid]))
                vmax = float(np.max(data[valid]))
            else:
                vmin, vmax = np.nan, np.nan

            print(f"  debug: dtype={data.dtype}, nodata={nodata}, valid_pixels={valid_count}/{total}, min={vmin}, max={vmax}")

        # Usa array + affine diretamente (evita problemas com /vsimem/ e mantém float32)
        zs = zonal_stats(
            municipios,
            data,
            affine=src.transform,
            nodata=src.nodata,
            stats="mean",
        )

        print(f"  calculando {len(zs)} municipios...")

    linha = []
    for z in zs:
        v = z["mean"]

        if v is None:
            linha.append(np.nan)
            continue

        v_c = float(v) * float(scale_to_c)

        if v_c < MIN_TEMP_C or v_c > MAX_TEMP_C:
            linha.append(np.nan)
        else:
            linha.append(v_c)

    stats_mensais.append(linha)

# =========================
# 4. MÉDIA ANUAL
# =========================
stats_mensais = np.array(stats_mensais, dtype=np.float64)

temp_media_anual = np.nanmean(stats_mensais, axis=0)
temp_media_anual = temp_media_anual  # já está em °C

if args.mes is not None:
    print("⚠️  Aviso: com --mes, a coluna 'temp_media_anual' representa apenas esse mês (não a média anual).")

# =========================
# 5. DATAFRAME
# =========================
df = pd.DataFrame({
    "codigo_ibge": municipios["CD_MUN"],
    "municipio": municipios["NM_MUN"],
    "estado": municipios["SIGLA_UF"],
    "temp_media_anual": temp_media_anual
})

# =========================
# 6. SALVAR
# =========================
df.to_csv(OUTPUT, index=False)

print("===================================")
print("Arquivo gerado:", OUTPUT)
print(df["temp_media_anual"].describe())
print("Municípios sem dado:", df["temp_media_anual"].isna().sum())
