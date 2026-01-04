import geopandas as gpd
import rasterio
from rasterio.mask import mask
import glob
import os

# Configurações
BRASIL_SHP = "brasil/brasil.shp"
INPUT_RASTERS = "raster/wc2.1_30s_tavg_*.tif"
OUTPUT_DIR = "raster_brasil"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Carregar Brasil
brasil = gpd.read_file(BRASIL_SHP)

rasters = glob.glob(INPUT_RASTERS)

for raster_path in rasters:
    print(f"Recortando {raster_path}...")

    with rasterio.open(raster_path) as src:
        # Garantir CRS compatível
        brasil = brasil.to_crs(src.crs)

        out_image, out_transform = mask(
            src,
            brasil.geometry,
            crop=True
        )

        out_meta = src.meta.copy()
        out_meta.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })

        nome = os.path.basename(raster_path)
        out_path = os.path.join(OUTPUT_DIR, nome)

        with rasterio.open(out_path, "w", **out_meta) as dest:
            dest.write(out_image)

print("Recorte concluído")
