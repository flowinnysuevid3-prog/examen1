"""
app.py — Validador de estructura Markdown con autenticación por matrícula.

Flujo:
  /login      → /registro  → /dashboard
  /dashboard  → sube .md, valida ahí mismo → botones de examen
  /validar    → página completa con detalle del .md
  /examen/<tipo>         → presentar examen
  /examen/<tipo>/resultado → calificación y retroalimentación
"""

import os, uuid, tempfile
from functools import wraps
from flask import (Flask, render_template, request,
                   flash, session, redirect, url_for)
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env", override=True)

from parser import validar
from examenes import generar_examen
from db import guardar_resultado
from auth import login, registrar, historial_alumno

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-cambia-en-prod")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.jinja_env.filters["enumerate"] = enumerate

TEMP_DIR = os.path.join(tempfile.gettempdir(), "validador_md")
os.makedirs(TEMP_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _guardar_md(contenido: str) -> str:
    fid = str(uuid.uuid4())
    with open(os.path.join(TEMP_DIR, fid + ".md"), "w", encoding="utf-8") as f:
        f.write(contenido)
    return fid

def _leer_md(fid: str) -> str | None:
    if not fid: return None
    ruta = os.path.join(TEMP_DIR, fid + ".md")
    return open(ruta, encoding="utf-8").read() if os.path.exists(ruta) else None

def login_requerido(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if not session.get("matricula"):
            return redirect(url_for("login_view"))
        return f(*args, **kwargs)
    return decorado

def _ctx():
    """Contexto común para todas las vistas autenticadas."""
    return {"nombre": session.get("nombre", ""), "matricula": session.get("matricula", "")}

def _recomendacion(historial: list[dict]) -> str:
    if not historial:
        return "Aún no has presentado ningún examen. Sube tu archivo y empieza cuando quieras."
    calif_prom = sum(r["calificacion"] for r in historial) / len(historial)
    tipos: dict[str, list[int]] = {}
    for r in historial:
        tipos.setdefault(r["tipo_examen"], []).append(r["calificacion"])
    tipo_peor = min(tipos, key=lambda t: sum(tipos[t]) / len(tipos[t]))
    prom_peor = sum(tipos[tipo_peor]) / len(tipos[tipo_peor])
    nombres = {
        "opcion_multiple":    "opción múltiple",
        "respuesta_multiple": "respuesta múltiple",
        "completar_codigo":   "completar código",
        "combinado":          "examen combinado",
    }
    if calif_prom >= 80:
        return f"¡Vas muy bien! Tu promedio es {calif_prom:.0f}%. Sigue practicando para mantenerte."
    if calif_prom >= 60:
        return (f"Tu promedio es {calif_prom:.0f}%. Puedes mejorar — "
                f"el tipo donde más te cuesta es '{nombres.get(tipo_peor, tipo_peor)}' "
                f"con {prom_peor:.0f}% de promedio. Repasa esa sección de tu .md.")
    return (f"Tu promedio es {calif_prom:.0f}%. Te recomendamos leer tu .md completo con calma, "
            f"especialmente la parte de '{nombres.get(tipo_peor, tipo_peor)}' "
            f"donde tienes {prom_peor:.0f}%.")


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login_view():
    if session.get("matricula"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        matricula = request.form.get("matricula", "").strip()
        res = login(matricula)
        if res["ok"]:
            session["matricula"] = res["alumno"]["matricula"]
            session["nombre"]    = res["alumno"]["nombre"]
            return redirect(url_for("dashboard"))
        error = res["error"]
    return render_template("login.html", error=error)


@app.route("/registro", methods=["GET", "POST"])
def registro_view():
    if session.get("matricula"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        matricula = request.form.get("matricula", "").strip()
        nombre    = request.form.get("nombre", "").strip()
        res = registrar(matricula, nombre)
        if res["ok"]:
            session["matricula"] = matricula
            r2 = login(matricula)
            session["nombre"] = r2["alumno"]["nombre"] if r2["ok"] else nombre
            return redirect(url_for("dashboard"))
        error = res["error"]
    return render_template("registro.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_view"))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
@app.route("/dashboard", methods=["GET", "POST"])
@login_requerido
def dashboard():
    """
    Dashboard principal. También maneja el POST de validación
    para que el resultado aparezca ahí mismo sin salir de la página.
    """
    historial  = historial_alumno(session["matricula"])
    resultado  = None
    nombre_archivo = None

    if request.method == "POST":
        archivo = request.files.get("archivo")
        contenido = ""
        if archivo and archivo.filename:
            nombre_archivo = archivo.filename
            contenido = archivo.stream.read().decode("utf-8", errors="replace")
        else:
            contenido = (request.form.get("contenido") or "").strip()

        if not contenido.strip():
            flash("Sube un archivo .md o pega el contenido.")
        else:
            resultado = validar(contenido)
            fid = _guardar_md(contenido)
            session["md_file_id"] = fid
            session["md_nombre"]  = nombre_archivo or "sin_nombre.md"

    stats = {
        "total":    len(historial),
        "promedio": round(sum(r["calificacion"] for r in historial) / len(historial)) if historial else 0,
        "mejor":    max((r["calificacion"] for r in historial), default=0),
        "ultimo":   historial[0]["calificacion"] if historial else None,
    }

    return render_template("dashboard.html",
                           historial=historial,
                           recomendacion=_recomendacion(historial),
                           stats=stats,
                           resultado=resultado,
                           nombre_archivo=nombre_archivo,
                           **_ctx())


# ── Vista detalle del .md ─────────────────────────────────────────────────────

@app.route("/validar")
@login_requerido
def validar_detalle():
    """Muestra el detalle completo del .md ya validado (archivos, checklist, etc.)."""
    contenido = _leer_md(session.get("md_file_id"))
    if not contenido:
        flash("Primero sube y valida un archivo .md.")
        return redirect(url_for("dashboard"))
    resultado = validar(contenido)
    return render_template("validar.html",
                           resultado=resultado,
                           nombre_archivo=session.get("md_nombre", ""),
                           **_ctx())


# ── Exámenes ──────────────────────────────────────────────────────────────────

@app.route("/examen/<tipo>")
@login_requerido
def examen(tipo: str):
    if tipo not in ("opcion_multiple", "respuesta_multiple", "completar_codigo", "combinado"):
        return redirect(url_for("dashboard"))
    contenido = _leer_md(session.get("md_file_id"))
    if not contenido:
        flash("Primero sube y valida un archivo .md para poder hacer el examen.")
        return redirect(url_for("dashboard"))
    r = validar(contenido)
    e = generar_examen(r, tipo)
    return render_template("examen.html", examen=e, tipo=tipo, **_ctx())


@app.route("/examen/<tipo>/resultado", methods=["POST"])
@login_requerido
def resultado_examen(tipo: str):
    contenido = _leer_md(session.get("md_file_id"))
    if not contenido:
        return redirect(url_for("dashboard"))

    r        = validar(contenido)
    examen_o = generar_examen(r, tipo)
    detalle  = []
    correctas_count = 0
    total = len(examen_o.preguntas)

    for i, p in enumerate(examen_o.preguntas):
        clave = f"q{i}"
        if p.tipo == "opcion_multiple":
            val = request.form.get(clave, "")
            sel = int(val) if val.isdigit() else -1
            ok  = sel == p.correcta
            correctas_count += int(ok)
            detalle.append({"tipo": "opcion_multiple", "pregunta": p.pregunta,
                "opciones": p.opciones, "correcta": p.correcta,
                "seleccionada": sel, "ok": ok, "explicacion": p.explicacion,
                "retroalimentacion": p.retroalimentacion if not ok else ""})
        elif p.tipo == "respuesta_multiple":
            vals = request.form.getlist(clave)
            sels = sorted([int(v) for v in vals if v.isdigit()])
            ok   = sels == sorted(p.correctas)
            correctas_count += int(ok)
            detalle.append({"tipo": "respuesta_multiple", "pregunta": p.pregunta,
                "opciones": p.opciones, "correctas": p.correctas,
                "seleccionadas": sels, "ok": ok, "explicacion": p.explicacion,
                "retroalimentacion": p.retroalimentacion if not ok else ""})
        elif p.tipo == "completar_codigo":
            # Múltiples huecos: q0_h0, q0_h1, q0_h2, etc.
            respuestas_usuario = []
            todos_ok = True
            for hi, resp_correcta in enumerate(p.respuestas):
                resp = (request.form.get(f"{clave}_h{hi}") or
                        request.form.get(clave) or "").strip()
                ok_hueco = resp.lower() == resp_correcta.strip().lower()
                if not ok_hueco: todos_ok = False
                respuestas_usuario.append({
                    "usuario": resp,
                    "correcto": resp_correcta,
                    "ok": ok_hueco,
                })
            correctas_count += int(todos_ok)
            detalle.append({"tipo": "completar_codigo", "instruccion": p.instruccion,
                "codigo_con_huecos": p.codigo_con_huecos,
                "respuesta_correcta": p.respuestas,
                "respuesta_usuario": " / ".join(r["usuario"] for r in respuestas_usuario),
                "respuestas_usuario": respuestas_usuario,
                "ok": todos_ok, "explicacion": p.explicacion,
                "retroalimentacion": p.retroalimentacion if not todos_ok else ""})

    calificacion = round((correctas_count / total) * 100) if total else 0

    guardar_resultado(
        nombre_archivo  = session.get("md_nombre", ""),
        alumno          = r.alumno,
        proyecto_nombre = r.proyecto_nombre,
        tipo_examen     = tipo,
        total           = total,
        correctas       = correctas_count,
        calificacion    = calificacion,
        matricula       = session.get("matricula"),
    )

    return render_template("resultado_examen.html",
                           examen=examen_o,
                           detalle=list(enumerate(detalle)),
                           correctas=correctas_count,
                           total=total,
                           calificacion=calificacion,
                           **_ctx())


if __name__ == "__main__":
    app.run(debug=True)