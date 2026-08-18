"""
app.py — Validador + Exámenes + Guardado de resultados en Supabase
"""
import os, uuid, tempfile
from flask import (Flask, render_template, request,
                   flash, session, redirect, url_for)
from parser import validar
from examenes import generar_examen
from db import guardar_resultado, ultimos_resultados

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-cambia-en-prod")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.jinja_env.filters["enumerate"] = enumerate

TEMP_DIR = os.path.join(tempfile.gettempdir(), "validador_md")
os.makedirs(TEMP_DIR, exist_ok=True)


def _guardar_md(contenido: str) -> str:
    fid = str(uuid.uuid4())
    with open(os.path.join(TEMP_DIR, fid + ".md"), "w", encoding="utf-8") as f:
        f.write(contenido)
    return fid


def _leer_md(fid: str) -> str | None:
    if not fid:
        return None
    ruta = os.path.join(TEMP_DIR, fid + ".md")
    return open(ruta, encoding="utf-8").read() if os.path.exists(ruta) else None


# ── Rutas ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
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
            flash("Sube un archivo .md o pega el contenido antes de validar.")
        else:
            resultado = validar(contenido)
            fid = _guardar_md(contenido)
            session["md_file_id"] = fid
            session["md_nombre"]  = nombre_archivo or "sin_nombre.md"

    return render_template("index.html", resultado=resultado,
                           nombre_archivo=nombre_archivo)


@app.route("/examen/<tipo>")
def examen(tipo: str):
    if tipo not in ("opcion_multiple","respuesta_multiple","completar_codigo","combinado"):
        return redirect(url_for("index"))
    contenido = _leer_md(session.get("md_file_id"))
    if not contenido:
        flash("Primero sube y valida un archivo .md para generar el examen.")
        return redirect(url_for("index"))
    r = validar(contenido)
    e = generar_examen(r, tipo)
    return render_template("examen.html", examen=e, tipo=tipo,
                           nombre=session.get("md_nombre",""))


@app.route("/examen/<tipo>/resultado", methods=["POST"])
def resultado_examen(tipo: str):
    contenido = _leer_md(session.get("md_file_id"))
    if not contenido:
        return redirect(url_for("index"))

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
            ok  = (sel == p.correcta)
            correctas_count += int(ok)
            detalle.append({"tipo":"opcion_multiple","pregunta":p.pregunta,
                "opciones":p.opciones,"correcta":p.correcta,
                "seleccionada":sel,"ok":ok,"explicacion":p.explicacion})

        elif p.tipo == "respuesta_multiple":
            vals = request.form.getlist(clave)
            sels = sorted([int(v) for v in vals if v.isdigit()])
            ok   = (sels == sorted(p.correctas))
            correctas_count += int(ok)
            detalle.append({"tipo":"respuesta_multiple","pregunta":p.pregunta,
                "opciones":p.opciones,"correctas":p.correctas,
                "seleccionadas":sels,"ok":ok,"explicacion":p.explicacion})

        elif p.tipo == "completar_codigo":
            resp = (request.form.get(clave) or "").strip()
            ok   = resp.lower() == p.respuestas[0].strip().lower()
            correctas_count += int(ok)
            detalle.append({"tipo":"completar_codigo","instruccion":p.instruccion,
                "codigo_con_huecos":p.codigo_con_huecos,
                "respuesta_correcta":p.respuestas[0],
                "respuesta_usuario":resp,"ok":ok,"explicacion":p.explicacion})

    calificacion = round((correctas_count / total) * 100) if total else 0

    # Guardar en Supabase (falla silenciosamente si no hay BD)
    guardado = guardar_resultado(
        nombre_archivo  = session.get("md_nombre",""),
        alumno          = r.alumno,
        proyecto_nombre = r.proyecto_nombre,
        tipo_examen     = tipo,
        total           = total,
        correctas       = correctas_count,
        calificacion    = calificacion,
    )

    return render_template("resultado_examen.html",
                           examen=examen_o, detalle=list(enumerate(detalle)),
                           correctas=correctas_count, total=total,
                           calificacion=calificacion,
                           nombre=session.get("md_nombre",""),
                           guardado=guardado)


@app.route("/historial")
def historial():
    resultados = ultimos_resultados(50)
    return render_template("historial.html", resultados=resultados)


if __name__ == "__main__":
    app.run(debug=True)