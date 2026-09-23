# DensiMap Samarinda

DensiMap Samarinda adalah aplikasi pemetaan kepadatan penduduk pada 10 kecamatan di Kota Samarinda. Aplikasi ini menggabungkan data jumlah penduduk, jumlah rumah, luas wilayah, dan batas geografis kecamatan untuk menampilkan tingkat kepadatan dalam bentuk peta interaktif.

Data dapat dibaca dari Supabase. Jika Supabase belum dikonfigurasi atau tidak dapat diakses, frontend menggunakan data GeoJSON lokal sebagai fallback.

## Fitur Utama

- Peta interaktif Samarinda menggunakan Leaflet dan GeoJSON.
- Pewarnaan wilayah berdasarkan klaster `Rendah`, `Sedang`, dan `Tinggi`.
- Pencarian kecamatan dan fokus peta ke wilayah yang dipilih.
- Popup berisi jumlah penduduk, luas wilayah, jumlah rumah, dan kepadatan.
- Filter klaster melalui legend.
- Tabel ringkasan seluruh kecamatan.
- Pilihan data tahunan dari 2020 sampai 2025.
- Dukungan Mapbox Light sebagai basemap, dengan CartoDB Positron sebagai fallback.

## Peran Machine Learning

Pipeline machine learning berada di `apps/backend/clustering.py`. Prosesnya berjalan untuk setiap tahun dengan langkah berikut:

1. Membaca data jumlah penduduk dan jumlah rumah.
2. Menghitung kepadatan penduduk dengan rumus:

	 `kepadatan_penduduk = jumlah_penduduk / luas_km2`

3. Menggunakan dua fitur, yaitu `kepadatan_penduduk` dan `luas_km2`.
4. Menstandardisasi fitur menggunakan `StandardScaler`.
5. Menjalankan Hierarchical Clustering dan K-Means dengan 3 klaster.
6. Mengubah nomor klaster menjadi label yang mudah dipahami: `Rendah`, `Sedang`, dan `Tinggi`.
7. Menyimpan hasil ke GeoJSON dan seed SQL untuk digunakan oleh aplikasi web.

### 1. Hierarchical Clustering

Project menggunakan `AgglomerativeClustering` dengan metode `Ward`. Algoritma ini menggabungkan wilayah yang memiliki karakteristik paling mirip secara bertahap sampai terbentuk 3 kelompok.

Perannya dalam pipeline saat ini adalah sebagai algoritma pembanding dan evaluasi. Label yang dihasilkan Hierarchical Clustering belum digunakan sebagai label akhir pada peta.

### 2. K-Means

Project menggunakan `KMeans` dengan `k=3`. Algoritma ini membagi data ke tiga kelompok berdasarkan kedekatan terhadap pusat klaster.

K-Means adalah algoritma yang menentukan label akhir yang digunakan aplikasi. Nomor klaster dari K-Means diurutkan berdasarkan rata-rata kepadatan penduduk, kemudian dipetakan menjadi:

- Kepadatan terendah: `Rendah`
- Kepadatan menengah: `Sedang`
- Kepadatan tertinggi: `Tinggi`

## Apakah Keduanya Saling Berkesinambungan?

Ya, keduanya berada dalam alur pemrosesan yang sama dan menggunakan data serta fitur yang sama. Keduanya juga dijalankan pada setiap tahun untuk membandingkan hasil pengelompokan.

Namun, secara teknis implementasi saat ini belum merupakan hybrid clustering penuh. Hubungannya adalah:

```text
Data mentah
	-> Hitung kepadatan
	-> Standardisasi fitur
	-> Hierarchical Clustering (pembanding dan evaluasi)
	-> K-Means (menentukan label akhir)
	-> GeoJSON / database
	-> Peta interaktif
```

Dengan demikian, istilah yang paling akurat untuk implementasi sekarang adalah **K-Means dengan evaluasi/pembanding Hierarchical Clustering**, bukan kombinasi hasil kedua algoritma dalam satu keputusan akhir. Jika ingin menyebutnya "Hybrid Hierarchical Clustering & K-Means", perlu ditambahkan aturan penggabungan hasil, misalnya voting, pemilihan model berdasarkan skor, atau menjadikan hasil Hierarchical Clustering sebagai inisialisasi K-Means.

## Evaluasi Clustering

Pipeline menghitung metrik evaluasi berikut:

- **Silhouette Score**: mengukur seberapa baik suatu wilayah berada di klasternya dibandingkan klaster lain.
- **Davies-Bouldin Index**: mengukur kemiripan antar-klaster; nilai yang lebih kecil biasanya lebih baik.

Saat ini Silhouette Score yang dikembalikan dan digunakan oleh pengujian berasal dari hasil K-Means. Hasil Hierarchical Clustering juga dihitung untuk pembanding, tetapi nilainya belum dikembalikan atau ditampilkan pada frontend.

## Struktur Project

```text
apps/
	backend/
		clustering.py       # Pipeline pengolahan data dan clustering
		test_clustering.py  # Pengujian pipeline
		database/           # Schema dan seed database
	web/
		src/App.vue         # Antarmuka peta interaktif
		src/services/       # Akses Supabase dan fallback GeoJSON
		public/data/        # Data GeoJSON lokal
data/                   # Data input dan batas wilayah
database/               # Schema dan seed SQL utama
```

## Menjalankan Frontend

Prasyarat: Node.js sesuai versi pada `apps/web/package.json`.

```bash
cd apps/web
npm install
npm run dev
```

Untuk membuat build production:

```bash
npm run build
```

### Environment Variable Frontend

Buat file `.env` di dalam `apps/web` jika ingin menggunakan layanan eksternal:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_MAPBOX_TOKEN=your-mapbox-token
```

Tanpa kredensial Supabase, aplikasi tetap dapat membaca `public/data/samarinda_kecamatan.json`. Tanpa token Mapbox, aplikasi menggunakan CartoDB Positron.

## Menjalankan Pipeline Backend

Pipeline membutuhkan Python dengan library `pandas`, `numpy`, `scikit-learn`, dan pembaca file Excel seperti `openpyxl`.

```bash
python apps/backend/clustering.py
```

Pipeline membaca data Excel dari folder `data`, memproses tahun 2020-2025, lalu menghasilkan data GeoJSON serta file SQL.

Setelah proses clustering selesai, pipeline juga otomatis melakukan upsert 60 baris hasil (10 kecamatan x 6 tahun) ke Supabase. Buat file `apps/backend/.env` berdasarkan `apps/backend/.env.example` dan isi `SUPABASE_URL` serta `SUPABASE_SERVICE_ROLE_KEY`. Jangan gunakan atau commit service role key di frontend.

Schema tabel tetap perlu dijalankan satu kali di Supabase SQL Editor menggunakan `database/schema.sql`. Setelah itu, `seed.sql` tidak perlu dijalankan manual lagi. File tersebut tetap dibuat sebagai backup SQL.

Pengujian pipeline:

```bash
python apps/backend/test_clustering.py
```

## Teknologi

- Vue 3 dan Vite
- Leaflet
- Supabase
- Python
- Pandas dan NumPy
- Scikit-learn
- GeoJSON
