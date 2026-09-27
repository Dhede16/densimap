import os
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score
import pandas as pd
import numpy as np

app = FastAPI(title="DensiMap Clustering API", version="1.0.0")

LUAS_WILAYAH = {
    'Palaran': 221.29,
    'Samarinda Seberang': 12.49,
    'Samarinda Ulu': 22.12,
    'Samarinda Ilir': 17.18,
    'Samarinda Utara': 229.52,
    'Sungai Kunjang': 43.04,
    'Sambutan': 100.95,
    'Sungai Pinang': 34.16,
    'Samarinda Kota': 11.12,
    'Loa Janan Ilir': 26.13
}

class KecamatanInput(BaseModel):
    id: int
    nama: str
    jumlah_penduduk: int
    luas_km2: float
    jumlah_rumah: int

class ReclusterRequest(BaseModel):
    year: int
    data: List[KecamatanInput]

class ClusterResult(BaseModel):
    id: int
    nama: str
    cluster_label: str
    kepadatan_penduduk: float
    kepadatan_rumah: float
    rata_rata_penghuni: float

class ReclusterResponse(BaseModel):
    success: bool
    clusters: List[ClusterResult]
    metrics: Dict[str, Any]
    error: Optional[str] = None


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['kepadatan_penduduk'] = df['jumlah_penduduk'] / df['luas_km2']
    df['kepadatan_rumah'] = df['jumlah_rumah'] / df['luas_km2']
    df['rata_rata_penghuni'] = df['jumlah_penduduk'] / df['jumlah_rumah']
    return df


def find_optimal_k_hierarchical(X_scaled: np.ndarray, max_k: int = 5) -> tuple:
    best_k = 3
    best_score = -1
    scores = {}
    for k in range(2, max_k + 1):
        hierarchical = AgglomerativeClustering(n_clusters=k, metric='euclidean', linkage='ward')
        labels = hierarchical.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        scores[k] = round(score, 4)
        if score > best_score:
            best_score = score
            best_k = k
    return best_k, scores


def perform_clustering(df: pd.DataFrame) -> tuple:
    features = ['kepadatan_penduduk', 'kepadatan_rumah', 'rata_rata_penghuni']
    X = df[features].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    optimal_k, h_scores = find_optimal_k_hierarchical(X_scaled, max_k=5)
    n_clusters = 3

    hierarchical = AgglomerativeClustering(n_clusters=n_clusters, metric='euclidean', linkage='ward')
    h_labels = hierarchical.fit_predict(X_scaled)
    h_silhouette = silhouette_score(X_scaled, h_labels)
    h_db = davies_bouldin_score(X_scaled, h_labels)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
    km_labels = kmeans.fit_predict(X_scaled)
    km_silhouette = silhouette_score(X_scaled, km_labels)
    km_db = davies_bouldin_score(X_scaled, km_labels)

    df['raw_cluster'] = km_labels
    cluster_densities = df.groupby('raw_cluster')['kepadatan_penduduk'].mean().sort_values()
    cluster_order = list(cluster_densities.index)
    label_map = {
        cluster_order[0]: 'Rendah',
        cluster_order[1]: 'Sedang',
        cluster_order[2]: 'Tinggi'
    }
    df['cluster_label'] = df['raw_cluster'].map(label_map)

    metrics = {
        'hierarchical': {
            'silhouette': round(h_silhouette, 4),
            'davies_bouldin': round(h_db, 4),
            'optimal_k_suggestion': optimal_k,
            'silhouette_by_k': {str(k): round(v, 4) for k, v in h_scores.items()}
        },
        'kmeans': {
            'silhouette': round(km_silhouette, 4),
            'davies_bouldin': round(km_db, 4),
            'inertia': round(kmeans.inertia_, 4)
        },
        'features_used': features
    }

    return df, metrics


@app.post("/api/recluster", response_model=ReclusterResponse)
async def recluster(request: ReclusterRequest):
    try:
        if not request.data:
            raise HTTPException(status_code=400, detail="No data provided")

        input_data = []
        for item in request.data:
            if item.nama not in LUAS_WILAYAH:
                raise HTTPException(status_code=400, detail=f"Unknown kecamatan: {item.nama}")
            if item.luas_km2 <= 0:
                raise HTTPException(status_code=400, detail=f"Invalid area for {item.nama}: luas_km2 must be > 0")
            if item.jumlah_penduduk < 0:
                raise HTTPException(status_code=400, detail=f"Invalid population for {item.nama}: must be >= 0")
            if item.jumlah_rumah <= 0:
                raise HTTPException(status_code=400, detail=f"Invalid house count for {item.nama}: must be > 0")

            input_data.append({
                'id': item.id,
                'nama': item.nama,
                'tahun': request.year,
                'jumlah_penduduk': item.jumlah_penduduk,
                'luas_km2': item.luas_km2,
                'jumlah_rumah': item.jumlah_rumah,
            })

        df = pd.DataFrame(input_data)
        df = engineer_features(df)
        df, metrics = perform_clustering(df)

        clusters = []
        for _, row in df.iterrows():
            clusters.append(ClusterResult(
                id=int(row['id']),
                nama=row['nama'],
                cluster_label=row['cluster_label'],
                kepadatan_penduduk=round(row['kepadatan_penduduk'], 2),
                kepadatan_rumah=round(row['kepadatan_rumah'], 2),
                rata_rata_penghuni=round(row['rata_rata_penghuni'], 2)
            ))

        return ReclusterResponse(
            success=True,
            clusters=clusters,
            metrics=metrics
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "densimap-clustering-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)