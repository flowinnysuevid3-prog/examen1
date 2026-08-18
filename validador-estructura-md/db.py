"""
db.py — Conexión a Supabase (PostgreSQL) para guardar resultados.
Usa psycopg2 igual que Flowi, con la misma convención de get_conexion().
Si no hay DATABASE_URL configurada, las operaciones se omiten silenciosamente
(el examen funciona aunque no haya BD).
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
) -> bool:
    """
    Inserta un resultado en la tabla resultado_examen.
    Devuelve True si se guardó, False si no hay BD o hubo error.
    """
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
                     total_preguntas, correctas, calificacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[db] Error al guardar resultado: {e}")
        return False
    finally:
        if conn:
            conn.close()


def ultimos_resultados(limite: int = 20) -> list[dict]:
    """Devuelve los últimos N resultados para la página de historial."""
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
        if conn:
            conn.close()
