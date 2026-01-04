import pandas as pd
import numpy as np
import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gera estatísticas a partir do CSV de temperatura média por município."
    )
    parser.add_argument(
        "--csv",
        default="temperatura_media_por_municipio.csv",
        help="Caminho do CSV de entrada",
    )
    parser.add_argument(
        "--outdir",
        default="stats_out",
        help="Diretório para salvar resultados (CSVs)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    df = pd.read_csv(args.csv)

    # Garantias básicas
    df = df.dropna(subset=["temp_media_anual"])
    df["temp_media_anual"] = df["temp_media_anual"].astype(float)

    print("===================================")
    print("Estatísticas gerais (Brasil)")
    print(df["temp_media_anual"].describe())

    # =========================
    # TOP 10 MAIS QUENTES
    # =========================
    top_quentes = (
        df.sort_values("temp_media_anual", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    print("\nTop 10 cidades mais quentes")
    print(top_quentes[["municipio", "estado", "temp_media_anual"]])

    top_quentes.to_csv(
        os.path.join(args.outdir, "top_10_cidades_mais_quentes.csv"),
        index=False,
    )

    # =========================
    # TOP 10 MAIS FRIAS
    # =========================
    top_frias = (
        df.sort_values("temp_media_anual", ascending=True)
        .head(10)
        .reset_index(drop=True)
    )

    print("\nTop 10 cidades mais frias")
    print(top_frias[["municipio", "estado", "temp_media_anual"]])

    top_frias.to_csv(
        os.path.join(args.outdir, "top_10_cidades_mais_frias.csv"),
        index=False,
    )

    # =========================
    # MÉDIA POR ESTADO
    # =========================
    media_estado = (
        df.groupby("estado", as_index=False)["temp_media_anual"]
        .mean()
        .sort_values("temp_media_anual", ascending=False)
    )
    media_estado = media_estado.reset_index(drop=True)

    print("\nTemperatura média por estado")
    print(media_estado)

    media_estado.to_csv(
        os.path.join(args.outdir, "media_temperatura_por_estado.csv"),
        index=False,
    )

    # =========================
    # DISTRIBUIÇÃO POR FAIXAS
    # =========================
    bins = [-50, 15, 18, 21, 24, 27, 50]
    labels = [
        "< 15°C",
        "15–18°C",
        "18–21°C",
        "21–24°C",
        "24–27°C",
        "> 27°C",
    ]

    df["faixa_temperatura"] = pd.cut(
        df["temp_media_anual"],
        bins=bins,
        labels=labels,
        include_lowest=True,
    )

    dist = (
        df["faixa_temperatura"]
        .value_counts()
        .sort_index()
        .reset_index()
        .rename(columns={"index": "faixa", "faixa_temperatura": "quantidade"})
    )

    print("\nDistribuição de municípios por faixa de temperatura")
    print(dist)

    dist.to_csv(
        os.path.join(args.outdir, "distribuicao_faixa_temperatura.csv"),
        index=False,
    )

    # =========================
    # OUTLIERS (IQR)
    # =========================
    q1 = df["temp_media_anual"].quantile(0.25)
    q3 = df["temp_media_anual"].quantile(0.75)
    iqr = q3 - q1

    lim_inf = q1 - 1.5 * iqr
    lim_sup = q3 + 1.5 * iqr

    outliers = df[
        (df["temp_media_anual"] < lim_inf)
        | (df["temp_media_anual"] > lim_sup)
    ].sort_values("temp_media_anual")

    print("\nOutliers de temperatura (IQR)")
    print(outliers[["municipio", "estado", "temp_media_anual"]])

    outliers.to_csv(
        os.path.join(args.outdir, "outliers_temperatura.csv"),
        index=False,
    )

    print("\n===================================")
    print("Arquivos gerados em:", args.outdir)


if __name__ == "__main__":
    main()
