# Rumus & Formula DensiMap Clustering

---

## 1. Kepadatan Penduduk (Feature Engineering)

```python
kepadatan_penduduk = jumlah_penduduk / luas_km2
```

- **Unit**: jiwa/km²
- **Digunakan sebagai**: Feature utama clustering (`X[:, 0]`)

---

## 2. StandardScaler (Feature Scaling)

Untuk setiap fitur $j$ (kepadatan, luas):

$$
z_{ij} = \frac{x_{ij} - \mu_j}{\sigma_j}
$$

| Simbol | Arti |
|--------|------|
| $x_{ij}$ | Nilai asli fitur $j$ untuk kecamatan $i$ |
| $\mu_j$ | Mean fitur $j$ (rata-rata 10 kecamatan) |
| $\sigma_j$ | Std dev fitur $j$ |
| $z_{ij}$ | Nilai terskalakan (mean=0, std=1) |

**Kode**: `sklearn.preprocessing.StandardScaler().fit_transform(X)`

---

## 3. Euclidean Distance (Digunakan Ward & K-Means)

$$
d(\mathbf{z}_i, \mathbf{z}_k) = \sqrt{\sum_{j=1}^{2} (z_{ij} - z_{kj})^2}
$$

- 2 fitur → ruang 2D
- Digunakan oleh: Ward linkage (Hierarchical) & centroid distance (K-Means)

---

## 4. Ward Linkage (Hierarchical Clustering)

**Kriteria penggabungan**: Pilih pasangan klaster $(A, B)$ yang meminimalkan peningkatan **total within-cluster variance (SSE)**:

$$
\Delta(A, B) = \frac{|A| \cdot |B|}{|A| + |B|} \|\mathbf{c}_A - \mathbf{c}_B\|^2
$$

| Simbol | Arti |
|--------|------|
| $|A|, |B|$ | Jumlah anggota klaster A, B |
| $\mathbf{c}_A, \mathbf{c}_B$ | Centroid klaster A, B (mean vector) |
| $\|\cdot\|$ | Euclidean norm |

Algoritma: Mulai 10 klaster (1 per kecamatan) → iteratif gabung yang $\Delta$ minimal → berhenti saat tersisa 3 klaster.

---

## 5. K-Means Objective (Within-Cluster Sum of Squares)

$$
J = \sum_{k=1}^{3} \sum_{\mathbf{z}_i \in C_k} \|\mathbf{z}_i - \boldsymbol{\mu}_k\|^2
$$

| Simbol | Arti |
|--------|------|
| $C_k$ | Himpunan titik di klaster $k$ |
| $\boldsymbol{\mu}_k$ | Centroid klaster $k$ (mean of $C_k$) |
| $J$ | Total within-cluster variance (inertia) |

Algoritma (Lloyd):
1. Inisialisasi 3 centroid acak (`n_init=20` → pilih terbaik)
2. **Assign**: Setiap titik ke centroid terdekat
3. **Update**: Centroid = mean titik anggota
4. Ulang sampai konvergen (centroid tidak bergerak)

---

## 6. Silhouette Score (Evaluasi Kualitas Klaster)

Untuk satu titik $i$:

$$
a(i) = \text{mean distance ke sesama klaster} \\
b(i) = \text{mean distance ke klaster terdekat lain} \\
s(i) = \frac{b(i) - a(i)}{\max(a(i), b(i))} \in [-1, 1]
$$

**Overall Silhouette** = rata-rata $s(i)$ untuk semua 10 titik.

| $s(i)$ | Interpretasi |
|--------|--------------|
| $\approx 1$ | Jauh dari klaster lain, dekat ke miliknya |
| $\approx 0$ | Di boundary antar klaster |
| $< 0$ | Mungkin klaster salah |

**Kode**: `sklearn.metrics.silhouette_score(X_scaled, labels)`

---

## 7. Davies-Bouldin Index (Evaluasi K-Means Only)

$$
DB = \frac{1}{3} \sum_{k=1}^{3} \max_{l \neq k} \left( \frac{S_k + S_l}{d(\boldsymbol{\mu}_k, \boldsymbol{\mu}_l)} \right)
$$

| Simbol | Arti |
|--------|------|
| $S_k = \frac{1}{|C_k|} \sum_{\mathbf{z}_i \in C_k} \|\mathbf{z}_i - \boldsymbol{\mu}_k\|$ | Rata-rata jarak intra-klaster (scatter) |
| $d(\boldsymbol{\mu}_k, \boldsymbol{\mu}_l)$ | Jarak centroid antar klaster |

**Semakin kecil DB** → klaster compact & terpisah baik. Range: $[0, \infty)$.

**Kode**: `sklearn.metrics.davies_bouldin_score(X_scaled, km_labels)`

---

## 8. Delta (Validasi Kesepakatan Dua Algoritma)

$$
\Delta = | \text{Silhouette}_{\text{Hierarchical}} - \text{Silhouette}_{\text{K-Means}} |
$$

**Threshold project**:
- $\Delta < 0.05$ → **COCOK** (k=3 valid)
- $0.05 \le \Delta < 0.15$ → **WASPADA**
- $\Delta \ge 0.15$ → **TIDAK COCOK**

---

## 9. Label Mapping (K-Means Cluster → Business Label)

```python
cluster_densities = df.groupby('raw_cluster')['kepadatan_penduduk'].mean().sort_values()
cluster_order = list(cluster_densities.index)  # [id_terendah, id_sedang, id_tertinggi]

label_map = {
    cluster_order[0]: 'Rendah',
    cluster_order[1]: 'Sedang', 
    cluster_order[2]: 'Tinggi'
}
df['cluster_label'] = df['raw_cluster'].map(label_map)
```

- **Input**: Nomor klaster K-Means (0, 1, 2 acak)
- **Output**: Label terurut by mean density (domain-driven)

---

## 10. Ringkasan Parameter Project

| Parameter | Nilai | Lokasi |
|-----------|-------|--------|
| `n_clusters` | 3 | Hardcoded (domain: Rendah/Sedang/Tinggi) |
| Features | `['kepadatan_penduduk', 'luas_km2']` | `clustering.py:102` |
| Scaler | `StandardScaler()` | `clustering.py:104-105` |
| Hierarchical linkage | `'ward'` | `clustering.py:108` |
| K-Means `n_init` | 20 | `clustering.py:113` |
| K-Means `random_state` | 42 | `clustering.py:113` |
| Target Silhouette (PRD) | > 0.58 | `clustering.py:101` comment |
| Toleransi Delta | < 0.05 | `explain.md` |
| Toleransi DB Index | < 0.5 | `explain.md` |