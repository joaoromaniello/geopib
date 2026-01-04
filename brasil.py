import geopandas as gpd

# Carregar municípios
municipios = gpd.read_file("municipios/BR_Municipios_2024.shp")

# Corrigir geometrias inválidas
municipios["geometry"] = municipios["geometry"].buffer(0)

# Dissolver tudo em um único polígono (Brasil)
brasil = municipios.dissolve()

# Garantir CRS
brasil = brasil.to_crs(epsg=4326)

# Salvar
brasil.to_file("brasil.shp")

print("Arquivo brasil.shp gerado")
