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
    df_2024, silhouette_2024, all_dfs, all_silhouettes = run_pipeline()

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

        # 3. Validasi klaster & urutan kepadatan: Rendah < Sedang < Tinggi
        clusters = set(df['cluster_label'].unique())
        assert clusters.issubset({'Rendah', 'Sedang', 'Tinggi'}), f"Unexpected cluster labels: {clusters}"

        mean_rendah = df[df['cluster_label'] == 'Rendah']['kepadatan_penduduk'].mean()
        mean_sedang = df[df['cluster_label'] == 'Sedang']['kepadatan_penduduk'].mean()
        mean_tinggi = df[df['cluster_label'] == 'Tinggi']['kepadatan_penduduk'].mean()
        assert mean_rendah < mean_sedang < mean_tinggi, f"Cluster density ordering violated in {year}: {mean_rendah} < {mean_sedang} < {mean_tinggi}"

        # Validasi skor Silhouette > 0.5 (syarat PRD Bagian 17)
        sil = all_silhouettes[year]
        assert sil > 0.5, f"Silhouette score below target in {year}: {sil:.4f}"

    # 4. Validasi file output
    assert os.path.exists('apps/web/public/data/samarinda_kecamatan.json'), "GeoJSON output file missing"
    assert os.path.exists('database/schema.sql'), "database/schema.sql missing"
    assert os.path.exists('database/seed.sql'), "database/seed.sql missing"

    with open('apps/web/public/data/samarinda_kecamatan.json', 'r', encoding='utf-8') as f:
        geo = json.load(f)
        assert geo['type'] == 'FeatureCollection'
        assert len(geo['features']) == 10
        assert 'by_year' in geo
        for y in years:
            assert str(y) in geo['by_year']
            assert len(geo['by_year'][str(y)]['features']) == 10

    print("ALL 4 ASSERTION SUITES PASSED FOR ALL YEARS (2020-2025)! Clustering logic & multi-year pipeline verified successfully.")

if __name__ == '__main__':
    test_clustering_pipeline()
