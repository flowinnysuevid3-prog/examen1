-- Ejecutar en Supabase SQL Editor
-- Guarda los resultados de cada examen presentado

CREATE TABLE IF NOT EXISTS resultado_examen (
    id              SERIAL PRIMARY KEY,
    nombre_archivo  TEXT NOT NULL,
    alumno_nombre   TEXT,
    alumno_email    TEXT,
    alumno_grupo    TEXT,
    proyecto_nombre TEXT,
    tipo_examen     TEXT NOT NULL
        CHECK(tipo_examen IN ('opcion_multiple','respuesta_multiple','completar_codigo','combinado')),
    total_preguntas INTEGER NOT NULL,
    correctas       INTEGER NOT NULL,
    calificacion    INTEGER NOT NULL,   -- 0-100
    fecha           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices útiles para reportes
CREATE INDEX IF NOT EXISTS idx_res_email    ON resultado_examen(alumno_email);
CREATE INDEX IF NOT EXISTS idx_res_fecha    ON resultado_examen(fecha);
CREATE INDEX IF NOT EXISTS idx_res_tipo     ON resultado_examen(tipo_examen);
CREATE INDEX IF NOT EXISTS idx_res_calif    ON resultado_examen(calificacion);
