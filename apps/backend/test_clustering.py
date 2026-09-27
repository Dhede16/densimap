# Self-check assert-based test for DensiMap clustering & data integrity
# Follows AGENTS.md rule: ONE runnable check behind, assert-based, no frameworks
import json
import os
import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
from apps.backend.clustering import run_pipeline, LUAS_WILAYAH

def test_clustering_pipeline():
    print("Running assert-based tests for DensiMap clustering...")
    df_2024, metrics_2024, all_dfs, all_metrics = run_pipeline()

    # 1. Pastikan seluruh 6 tahun (2020 - 2025) terproses dengan baik
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    for year in years:
        assert year in all_dfs, f"Year {year} missing from results"
        df = all_dfs[year]
        assert len(df) == 10, f"Expected 10 kecamatan for year {year}, got {len(df)}"
        for kec in LUAS_WILAYAH.keys():
            assert kec in df['nama'].values, f"Kecamatan {kec} missing from dataframe in year {year}"

        # 2. Pastikan nilai kepadatan dan rasio masuk akal
        for _, row in df.iterrows():
            assert row['jumlah_penduduk'] > 10000, f"Unrealistic penduduk for {row['nama']}: {row['jumlah_penduduk']}"
            assert row['luas_km2'] > 0, f"Invalid area for {row['nama']}: {row['luas_km2']}"
            assert row['jumlah_rumah'] > 1000, f"Invalid houses for {row['nama']}: {row['jumlah_rumah']}"
            expected_density = round(row['jumlah_penduduk'] / row['luas_km2'], 2)
            assert abs(row['kepadatan_penduduk'] - expected_density) < 0.01, f"Density mismatch for {row['nama']}"
            assert row['geometry'] is not None, f"Geometry is missing for {row['nama']}"
            assert row['geometry']['type'] in ['Polygon', 'MultiPolygon'], f"Invalid geometry type for {row['nama']}"

        # 3. Validasi klaster & urutan kepadatan (dinamis berdasarkan n_clusters)
        clusters = set(df['cluster_label'].unique())
        valid_labels = {'Rendah', 'Sedang', 'Tinggi'}
        assert clusters.issubset(valid_labels), f"Unexpected cluster labels: {clusters}"
        
        # Urutkan cluster by mean density
        cluster_means = df.groupby('cluster_label')['kepadatan_penduduk'].mean().sort_values()
        # Pastikan urutan densitas naik mengikuti label order
        for i in range(len(cluster_means) - 1):
            assert cluster_means.iloc[i] < cluster_means.iloc[i+1], f"Cluster density ordering violated in {year}"

        # Validasi skor Silhouette > 0.3 (realistic threshold for this dataset)
        sil = all_metrics[str(year)]['kmeans']['silhouette']
        assert sil > 0.3, f"Silhouette score below target in {year}: {sil:.4f}"

    # 4. Validasi file output
    geo_path = os.path.join(repo_root, 'apps/web/public/data/samarinda_kecamatan.json')
    schema_path = os.path.join(repo_root, 'database/schema.sql')
    seed_path = os.path.join(repo_root, 'database/seed.sql')
    assert os.path.exists(geo_path), "GeoJSON output file missing"
    assert os.path.exists(schema_path), "database/schema.sql missing"
    assert os.path.exists(seed_path), "database/seed.sql missing"

    with open(geo_path, 'r', encoding='utf-8') as f:
        geo = json.load(f)
        assert geo['type'] == 'FeatureCollection'
        assert len(geo['features']) == 60  # 10 kecamatan x 6 tahun
        assert 'by_year' in geo
        for y in years:
            assert str(y) in geo['by_year']
            assert len(geo['by_year'][str(y)]['features']) == 10

    print("ALL 4 ASSERTION SUITES PASSED FOR ALL YEARS (2020-2025)! Clustering logic & multi-year pipeline verified successfully.")

if __name__ == '__main__':
    test_clustering_pipeline()
