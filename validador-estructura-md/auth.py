"""
auth.py — Registro e inicio de sesión por matrícula.
Prefijo válido: 172511 + 4 dígitos más = 10 caracteres total.
"""
import re
import psycopg2
from db import get_conexion

PREFIJO = "172511"
PATRON  = re.compile(r"^172511\d{4}$")


def matricula_valida(matricula: str) -> bool:
    return bool(PATRON.match(matricula.strip()))


def registrar(matricula: str, nombre: str) -> dict:
    """
    Registra un alumno nuevo.
    Devuelve {"ok": True} o {"ok": False, "error": "..."}
    """
    matricula = matricula.strip()
    nombre    = nombre.strip()

    if not matricula_valida(matricula):
        return {"ok": False, "error": f"La matrícula debe comenzar con {PREFIJO} y tener 10 dígitos."}
    if not nombre or len(nombre) < 2:
        return {"ok": False, "error": "Ingresa tu nombre completo."}

    conn = None
    try:
        conn = get_conexion()
        if conn is None:
            return {"ok": False, "error": "No hay conexión a la base de datos."}
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM alumno WHERE matricula = %s", (matricula,))
            if cur.fetchone():
                return {"ok": False, "error": "Esa matrícula ya está registrada. Inicia sesión."}
            cur.execute(
                "INSERT INTO alumno (matricula, nombre) VALUES (%s, %s)",
                (matricula, nombre)
            )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if conn: conn.close()


def login(matricula: str) -> dict:
    """
    Inicia sesión con matrícula.
    Devuelve {"ok": True, "alumno": {...}} o {"ok": False, "error": "..."}
    """
    matricula = matricula.strip()

    if not matricula_valida(matricula):
        return {"ok": False, "error": f"Matrícula inválida. Debe empezar con {PREFIJO}."}

    conn = None
    try:
        conn = get_conexion()
        if conn is None:
            return {"ok": False, "error": "No hay conexión a la base de datos."}
        with conn.cursor() as cur:
            cur.execute("SELECT id, matricula, nombre FROM alumno WHERE matricula = %s", (matricula,))
            row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "Matrícula no registrada. ¿Quieres crear una cuenta?"}
            return {"ok": True, "alumno": dict(row)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if conn: conn.close()


def historial_alumno(matricula: str) -> list[dict]:
    """Devuelve todos los exámenes presentados por el alumno."""
    conn = None
    try:
        conn = get_conexion()
        if conn is None:
            return []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nombre_archivo, tipo_examen,
                       total_preguntas, correctas, calificacion,
                       fecha AT TIME ZONE 'America/Mexico_City' AS fecha
                FROM resultado_examen
                WHERE matricula = %s
                ORDER BY fecha DESC
            """, (matricula,))
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[auth] Error historial: {e}")
        return []
    finally:
        if conn: conn.close()