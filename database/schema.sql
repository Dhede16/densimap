-- DensiMap Schema for Supabase (PostgreSQL + PostGIS)
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS public.kecamatan (
    id SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    tahun INTEGER NOT NULL DEFAULT 2024,
    jumlah_penduduk INTEGER NOT NULL,
    luas_km2 NUMERIC(8, 2) NOT NULL,
    jumlah_rumah INTEGER NOT NULL,
    kepadatan_penduduk NUMERIC(10, 2) NOT NULL,
    kepadatan_rumah NUMERIC(10, 2) NOT NULL,
    rata_rata_penghuni NUMERIC(6, 2) NOT NULL,
    geometry JSONB NOT NULL,
    cluster_label VARCHAR(20) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(nama, tahun)
);

ALTER TABLE public.kecamatan ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read-only access" 
ON public.kecamatan 
FOR SELECT 
TO anon 
USING (true);
