"""
db.py — Conexión a Supabase (PostgreSQL) para guardar resultados.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_conexion():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    return psycopg2.connect(url, cursor_factory=RealDictCursor)


def guardar_resultado(
    nombre_archivo: str,
    alumno: dict,
    proyecto_nombre: str,
    tipo_examen: str,
    total: int,
    correctas: int,
    calificacion: int,
    matricula: str = None,
) -> bool:
    conn = None
    try:
        conn = get_conexion()
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO resultado_examen
                    (nombre_archivo, alumno_nombre, alumno_email,
                     alumno_grupo, proyecto_nombre, tipo_examen,
                     total_preguntas, correctas, calificacion, matricula)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                nombre_archivo,
                alumno.get("Nombre", "") + " " + alumno.get("Primer Apellido", ""),
                alumno.get("Email", ""),
                alumno.get("Grupo", ""),
                proyecto_nombre,
                tipo_examen,
                total,
                correctas,
                calificacion,
                matricula,
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[db] Error al guardar resultado: {e}")
        return False
    finally:
        if conn: conn.close()


def ultimos_resultados(limite: int = 50) -> list[dict]:
    conn = None
    try:
        conn = get_conexion()
        if conn is None:
            return []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nombre_archivo, alumno_nombre, alumno_email,
                       alumno_grupo, proyecto_nombre, tipo_examen,
                       total_preguntas, correctas, calificacion,
                       fecha AT TIME ZONE 'America/Mexico_City' AS fecha
                FROM resultado_examen
                ORDER BY fecha DESC
                LIMIT %s
            """, (limite,))
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[db] Error al leer resultados: {e}")
        return []
    finally:
        if conn: conn.close()