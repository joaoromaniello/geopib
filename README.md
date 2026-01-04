# geopib

Script para calcular a **temperatura média** por município do Brasil a partir de rasters (ex.: WorldClim `tavg`) usando **zonal statistics**.

## Estrutura esperada do projeto

- `municipios/BR_Municipios_2024.shp` (e arquivos auxiliares `.dbf/.shx/.prj/.cpg`)
- `raster_brasil/wc2.1_30s_tavg_*.tif` (12 arquivos, 1 por mês)
- Saída gerada: `temperatura_media_por_municipio.csv`

## Dependências

Você precisa de Python 3 e destes pacotes:

- `geopandas`
- `rasterio`
- `rasterstats`
- `numpy`
- `pandas`

### Instalação (pip) via `requirements.txt`

```bash
pip install -r requirements.txt
```

### Instalação rápida (pip)

Se você não tiver um `requirements.txt`, uma forma simples é:

```bash
pip install geopandas rasterio rasterstats numpy pandas
```

Observação: em Windows, `geopandas/rasterio` podem exigir wheels adequados. Se o `pip` reclamar de GDAL/GEOS/PROJ, use um ambiente conda (recomendado):

```bash
conda create -n geopib python=3.11 -y
conda activate geopib
conda install -c conda-forge geopandas rasterio rasterstats numpy pandas -y
```

## Como rodar

### Rodar o cálculo completo (12 meses)

```bash
python index.py
```

- O script espera **12 rasters** no padrão `raster_brasil/wc2.1_30s_tavg_*.tif`.
- Gera `temperatura_media_por_municipio.csv`.

### Rodar apenas 1 mês (para teste)

```bash
python index.py --mes 1
```

- `--mes` vai de `1` a `12`.
- Importante: nesse modo, a coluna `temp_media_anual` **representa apenas aquele mês** (não é média anual).

### Rodar mais rápido (processando poucos municípios)

Útil para testar fluxo/escala sem esperar calcular os 5573 municípios:

```bash
python index.py --mes 1 --limite 50
```

### Debug (diagnóstico de raster e escala)

```bash
python index.py --mes 1 --limite 50 --debug
```

O `--debug` imprime:
- `nodata`
- contagem de pixels válidos
- `min/max` do raster
- escala escolhida

## Escala (°C vs °C*10)

Rasters de temperatura podem vir em:
- **°C** (valores típicos 10–35)
- **°C*10** (valores típicos 100–350)

O script tenta **detectar automaticamente**:
- Se o `max` do raster for `> 80`, assume **°C*10** e aplica escala `0.1`.
- Caso contrário, assume **°C** e aplica escala `1.0`.

Se você quiser forçar a escala manualmente:

- Raster já em °C:

```bash
python index.py --escala 1.0
```

- Raster em °C*10:

```bash
python index.py --escala 0.1
```

## Saída (CSV)

Arquivo: `temperatura_media_por_municipio.csv`

Colunas:
- `codigo_ibge`: código do município
- `municipio`: nome
- `estado`: UF
- `temp_media_anual`: média anual em °C (ou média do mês, se usar `--mes`)

## Estatísticas com `stats.py`

Depois de gerar o CSV com o `index.py`, você pode rodar o `stats.py` para imprimir estatísticas e gerar alguns CSVs auxiliares (top 10 mais quentes/frias, média por estado, distribuição por faixas, outliers).

### Uso básico

```bash
python stats.py
```

Por padrão ele lê `temperatura_media_por_municipio.csv` e salva os resultados em `stats_out/`.

### Escolher CSV de entrada e pasta de saída

```bash
python stats.py --csv temperatura_media_por_municipio.csv --outdir stats_out
```

Arquivos gerados (dentro de `--outdir`):
- `top_10_cidades_mais_quentes.csv`
- `top_10_cidades_mais_frias.csv`
- `media_temperatura_por_estado.csv`
- `distribuicao_faixa_temperatura.csv`
- `outliers_temperatura.csv`

## Solução de problemas

### CSV sai com tudo `NaN`

Isso normalmente indica que:
- o raster está todo `nodata` na área de interesse,
- ou a máscara/`nodata` está sendo interpretada de forma errada,
- ou os polígonos não estão sobrepondo o raster.

Faça um teste com debug:

```bash
python index.py --mes 1 --limite 50 --debug
```

Verifique principalmente:
- `Raster CRS` vs CRS dos municípios (o script reprojeta municípios para `EPSG:4326`)
- `Raster bounds` vs `Municipios bounds`
- `nodata` e `valid_pixels`

### Valores muito baixos (ex.: ~2–3°C)

Isso costuma ser sintoma de escala aplicada errada (dividindo por 10 quando o raster já está em °C). Use `--debug` para ver `min/max` e a escala escolhida, ou force `--escala 1.0`.

