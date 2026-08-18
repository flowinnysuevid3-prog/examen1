"""
examenes.py — Generador de exámenes a partir de un .md validado.

Tipos disponibles:
  opcion_multiple    20 preguntas, 1 correcta de 4 opciones
  respuesta_multiple 15 preguntas, varias correctas
  completar_codigo   15 fragmentos con hueco _____
  combinado          20 preguntas mezcladas (7+7+6)

Las preguntas se derivan del contenido REAL del archivo .md;
no hay preguntas inventadas ni hardcodeadas.
"""

from __future__ import annotations
import random, re
from dataclasses import dataclass, field
from parser import ResultadoValidacion, Archivo


# ── Tipos de dato ─────────────────────────────────────────────────────────────

@dataclass
class OpcionMultiple:
    tipo: str = "opcion_multiple"
    pregunta: str = ""
    opciones: list[str] = field(default_factory=list)
    correcta: int = 0
    explicacion: str = ""

@dataclass
class RespuestaMultiple:
    tipo: str = "respuesta_multiple"
    pregunta: str = ""
    opciones: list[str] = field(default_factory=list)
    correctas: list[int] = field(default_factory=list)
    explicacion: str = ""

@dataclass
class CompletarCodigo:
    tipo: str = "completar_codigo"
    instruccion: str = ""
    codigo_con_huecos: str = ""
    respuestas: list[str] = field(default_factory=list)
    explicacion: str = ""

Pregunta = OpcionMultiple | RespuestaMultiple | CompletarCodigo

@dataclass
class Examen:
    titulo: str
    descripcion: str
    tipo: str
    duracion_minutos: int
    preguntas: list[Pregunta] = field(default_factory=list)


# ── Helpers generales ─────────────────────────────────────────────────────────

def _by_ext(archivos: list[Archivo], *exts) -> list[Archivo]:
    return [a for a in archivos if a.titulo.rsplit(".", 1)[-1].lower() in exts]

def _novacias(codigo: str) -> list[str]:
    return [l for l in codigo.splitlines() if l.strip()]

def _om(pregunta, val_correcto, resto: list[str], explicacion: str, rng: random.Random) -> OpcionMultiple:
    """Construye OpcionMultiple mezclando opciones y recalculando índice correcto."""
    opciones = [val_correcto] + [r for r in resto[:3] if r != val_correcto]
    while len(opciones) < 4:
        opciones.append("(ninguna de las anteriores)")
    opciones = opciones[:4]
    rng.shuffle(opciones)
    return OpcionMultiple(
        pregunta=pregunta,
        opciones=opciones,
        correcta=opciones.index(val_correcto),
        explicacion=explicacion,
    )

def _rm(pregunta, correctas_vals: list[str], falsas_vals: list[str],
        explicacion: str, rng: random.Random) -> RespuestaMultiple:
    """Construye RespuestaMultiple mezclando opciones."""
    opciones = list(correctas_vals) + falsas_vals
    rng.shuffle(opciones)
    idxs = sorted([opciones.index(v) for v in correctas_vals if v in opciones])
    return RespuestaMultiple(
        pregunta=pregunta,
        opciones=opciones,
        correctas=idxs,
        explicacion=explicacion,
    )


# ── Banco de preguntas: Opción múltiple ───────────────────────────────────────

def _banco_om(r: ResultadoValidacion, rng: random.Random) -> list[OpcionMultiple]:
    banco: list[OpcionMultiple] = []
    py    = _by_ext(r.archivos, "py")
    sql   = _by_ext(r.archivos, "sql")
    html  = _by_ext(r.archivos, "html")
    req   = next((a for a in r.archivos if "requirements" in a.titulo), None)
    gi    = next((a for a in r.archivos if "gitignore" in a.titulo), None)

    # ── Alumno / proyecto ─────────────────────────────────────────────────────
    banco.append(_om(
        "¿Cuál es el correo electrónico del alumno registrado en la sección 1.1?",
        r.alumno.get("Email","—"),
        ["admin@render.com","noreply@utec.mx","soporte@supabase.io"],
        f"El correo está en la sección 1.1: {r.alumno.get('Email','—')}.", rng))

    banco.append(_om(
        "¿A qué grupo pertenece el alumno que entregó este proyecto?",
        r.alumno.get("Grupo","—"),
        ["TI00","TSU99","ISC01"],
        f"Grupo declarado en 1.1: {r.alumno.get('Grupo','—')}.", rng))

    banco.append(_om(
        "¿Cuál es el nombre completo del primer apellido del alumno?",
        r.alumno.get("Primer Apellido","—"),
        ["García","Hernández","López"],
        f"Primer apellido: {r.alumno.get('Primer Apellido','—')}.", rng))

    obj = r.proyecto_objetivo
    banco.append(_om(
        "¿Cuál es el objetivo del proyecto según la sección 1.2?",
        obj[:80]+"…" if len(obj)>80 else obj,
        ["Vender productos en línea.","Gestionar nómina de empleados.","Crear red social médica."],
        "El objetivo se declara en la sección 1.2.", rng))

    banco.append(_om(
        "¿Cuál es el nombre del proyecto declarado en la sección 1.2?",
        r.proyecto_nombre,
        ["SistemaWeb","AppMedica","GestorEscolar"],
        f"Nombre: {r.proyecto_nombre}.", rng))

    if r.modulos:
        m = r.modulos[0]
        banco.append(_om(
            f"¿Qué operaciones incluye el módulo '{m.numero}'?",
            m.texto, ["Solo lectura","Solo escritura","Pagos y facturación"],
            f"Módulo {m.numero}: {m.texto}", rng))

    if len(r.modulos) > 1:
        m = r.modulos[1]
        banco.append(_om(
            f"¿Qué describe el módulo '{m.numero}' en este proyecto?",
            m.texto, ["Autenticación OAuth","Reportes fiscales","Gestión de inventario"],
            f"Módulo {m.numero}: {m.texto}", rng))

    # ── Estructura de carpetas ────────────────────────────────────────────────
    if r.estructura:
        lineas = [l for l in r.estructura.splitlines() if l.strip()]
        raiz = lineas[0].rstrip("/").strip()
        banco.append(_om(
            "¿Cuál es el nombre de la carpeta raíz del proyecto (sección 2.1)?",
            raiz, ["src","app","proyecto"],
            f"Primera línea del árbol: '{raiz}/'.", rng))

        carpetas = [re.sub(r'[├└│─\s]+','',l).split('/')[0]
                    for l in lineas[1:] if '/' not in re.sub(r'[├└│─\s]+','',l)
                    and re.sub(r'[├└│─\s]+','',l)]
        if carpetas:
            c = rng.choice(carpetas)
            banco.append(_om(
                f"¿Existe la entrada '{c}' en la estructura de carpetas del proyecto?",
                "Sí, aparece en la sección 2.1",
                ["No, esa carpeta no existe","Solo en producción","Es una librería externa"],
                f"'{c}' aparece explícitamente en el árbol de la sección 2.1.", rng))

    # ── Requirements ─────────────────────────────────────────────────────────
    if req:
        libs = [l.strip() for l in _novacias(req.codigo) if "==" in l]
        usadas: set[str] = set()
        for lib in libs:
            nombre = lib.split("==")[0]
            if nombre not in usadas:
                usadas.add(nombre)
                banco.append(_om(
                    f"¿Cuál es la versión exacta de '{nombre}' en requirements.txt?",
                    lib,
                    [f"{nombre}==1.0.0", f"{nombre}==99.9", f"{nombre}==0.0.1"],
                    f"requirements.txt declara '{lib}'.", rng))

    # ── .gitignore ────────────────────────────────────────────────────────────
    if gi:
        lineas_gi = [l.strip() for l in _novacias(gi.codigo)]
        for entry in rng.sample(lineas_gi, min(3, len(lineas_gi))):
            banco.append(_om(
                "¿Cuál de estas entradas está en el .gitignore del proyecto?",
                entry,
                ["dist/","build/","coverage/"],
                f"'{entry}' aparece en el .gitignore.", rng))

    # ── Python: imports ───────────────────────────────────────────────────────
    todos_imports: list[tuple[str,str]] = []
    for pf in py:
        for l in _novacias(pf.codigo):
            if l.strip().startswith(("import ","from ")):
                todos_imports.append((pf.titulo, l.strip()))

    rng.shuffle(todos_imports)
    usados_imp: set[str] = set()
    for fname, imp in todos_imports[:8]:
        if imp in usados_imp: continue
        usados_imp.add(imp)
        banco.append(_om(
            f"¿Cuál importación existe en '{fname}'?",
            imp,
            ["import pandas as pd","from django.db import models","import tensorflow as tf"],
            f"La línea '{imp}' está en {fname}.", rng))

    # ── Python: definición de funciones ───────────────────────────────────────
    for pf in py:
        defs = [l.strip() for l in _novacias(pf.codigo)
                if l.strip().startswith("def ") and len(l.strip()) < 80]
        rng.shuffle(defs)
        for d in defs[:3]:
            fname_func = d.split("(")[0].replace("def ","").strip()
            banco.append(_om(
                f"¿Cuál de estas funciones está definida en '{pf.titulo}'?",
                d,
                [f"def procesar_pago(request):",f"def enviar_email(to, body):",f"def calcular_iva(monto):"],
                f"'{d}' está en {pf.titulo}.", rng))

    # ── Python: decoradores de ruta ───────────────────────────────────────────
    for pf in py:
        rutas = [l.strip() for l in _novacias(pf.codigo)
                 if l.strip().startswith("@") and "route" in l and len(l.strip()) < 100]
        rng.shuffle(rutas)
        for ruta in rutas[:3]:
            banco.append(_om(
                f"¿Cuál ruta (decorador) existe en '{pf.titulo}'?",
                ruta,
                ['@app.route("/dashboard")', '@app.route("/shop")', '@bp.route("/payment")'],
                f"'{ruta}' está en {pf.titulo}.", rng))

    # ── SQL: tablas ───────────────────────────────────────────────────────────
    if sql:
        tablas = list(dict.fromkeys(
            re.findall(r'CREATE TABLE\s+(\w+)', sql[0].codigo, re.IGNORECASE)))
        falsas_t = [t for t in ["pedido","factura","inventario","producto","empleado","cliente"]
                    if t not in tablas]
        for tabla in rng.sample(tablas, min(5, len(tablas))):
            banco.append(_om(
                "¿Cuál de estas tablas SÍ se crea en el schema SQL?",
                tabla,
                rng.sample(falsas_t, min(3, len(falsas_t))),
                f"'{tabla}' se define con CREATE TABLE en script.sql.", rng))

        # ── SQL: columnas de una tabla ────────────────────────────────────────
        for tabla in rng.sample(tablas, min(3, len(tablas))):
            patron = rf'CREATE TABLE\s+{tabla}\s*\((.*?)(?:CREATE TABLE|\Z)'
            bloque = re.search(patron, sql[0].codigo, re.DOTALL | re.IGNORECASE)
            if bloque:
                cols = re.findall(r'^\s+(\w+)\s+\w+', bloque.group(1), re.MULTILINE)
                cols = [c for c in cols if c.upper() not in ("FOREIGN","PRIMARY","CONSTRAINT","UNIQUE")]
                if cols:
                    col = rng.choice(cols)
                    banco.append(_om(
                        f"¿Cuál columna pertenece a la tabla '{tabla}'?",
                        col,
                        ["precio_total","nombre_comercial","codigo_barras"],
                        f"La columna '{col}' está definida en la tabla {tabla}.", rng))

        # ── SQL: CHECK constraints ────────────────────────────────────────────
        checks = re.findall(r"CHECK\((.+?)\)", sql[0].codigo)
        for c in rng.sample(checks, min(4, len(checks))):
            banco.append(_om(
                "¿Cuál CHECK constraint aparece en el schema SQL?",
                f"CHECK({c})",
                ["CHECK(precio > 0)","CHECK(cantidad BETWEEN 100 AND 999)","CHECK(rol IN ('admin'))"],
                f"El constraint CHECK({c}) está en script.sql.", rng))

        # ── SQL: ON DELETE / ON UPDATE ────────────────────────────────────────
        on_clauses = re.findall(r'(ON (?:DELETE|UPDATE) \w+)', sql[0].codigo, re.IGNORECASE)
        on_clauses = list(dict.fromkeys(on_clauses))
        if on_clauses:
            oc = rng.choice(on_clauses)
            banco.append(_om(
                "¿Cuál cláusula referencial aparece en las FOREIGN KEY del schema?",
                oc,
                ["ON DELETE NOTHING","ON UPDATE IGNORE","ON DELETE RESTRICT ALL"],
                f"La cláusula '{oc}' está en las FK de script.sql.", rng))

    # ── HTML: extends y bloques ───────────────────────────────────────────────
    for hf in html:
        ext = re.search(r'{%\s*extends\s*"([^"]+)"', hf.codigo)
        if ext:
            banco.append(_om(
                f"¿De qué template hereda '{hf.titulo.split('/')[-1]}'?",
                ext.group(1),
                ["base/main.html","static/index.html","templates/root.html"],
                f"{{% extends %}} apunta a '{ext.group(1)}'.", rng))

        bloques = list(dict.fromkeys(re.findall(r'{%\s*block\s+(\w+)', hf.codigo)))
        for b in rng.sample(bloques, min(2, len(bloques))):
            banco.append(_om(
                f"¿Cuál bloque Jinja2 está definido en '{hf.titulo.split('/')[-1]}'?",
                f"{{% block {b} %}}",
                ["{% block sidebar %}","{% block footer %}","{% block meta %}"],
                f"El bloque '{b}' aparece en {hf.titulo.split('/')[-1]}.", rng))

        rutas_jinja = list(dict.fromkeys(
            re.findall(r"url_for\('([^']+)'", hf.codigo)))
        for rj in rng.sample(rutas_jinja, min(3, len(rutas_jinja))):
            banco.append(_om(
                f"¿Cuál endpoint se referencia con url_for en '{hf.titulo.split('/')[-1]}'?",
                f"url_for('{rj}')",
                ["url_for('admin.panel')","url_for('shop.cart')","url_for('auth.register')"],
                f"url_for('{rj}') aparece en {hf.titulo.split('/')[-1]}.", rng))

    return banco


# ── Banco de preguntas: Respuesta múltiple ────────────────────────────────────

def _banco_rm(r: ResultadoValidacion, rng: random.Random) -> list[RespuestaMultiple]:
    banco: list[RespuestaMultiple] = []
    py  = _by_ext(r.archivos, "py")
    sql = _by_ext(r.archivos, "sql")
    req = next((a for a in r.archivos if "requirements" in a.titulo), None)
    gi  = next((a for a in r.archivos if "gitignore" in a.titulo), None)
    html = _by_ext(r.archivos, "html")

    # módulos
    if r.modulos:
        textos = [m.texto.split("(")[0].strip() for m in r.modulos]
        banco.append(_rm(
            "¿Cuáles son módulos desarrollados en este proyecto? (selecciona todos)",
            textos, ["Inventario","Nómina","Pagos en línea","Logística"],
            f"Módulos: {', '.join(textos)}.", rng))

    # librerías
    if req:
        libs = [l.split("==")[0].strip() for l in _novacias(req.codigo) if "==" in l]
        banco.append(_rm(
            "¿Cuáles librerías están en requirements.txt?",
            libs, ["Django","NumPy","TensorFlow","Celery","Pillow"],
            f"Librerías: {', '.join(libs)}.", rng))

    # gitignore
    if gi:
        lineas = [l.strip() for l in _novacias(gi.codigo)]
        muestra = lineas[:5]
        banco.append(_rm(
            "¿Cuáles entradas están en el .gitignore?",
            muestra, ["dist/","build/","coverage/","release/"],
            f"Entradas reales: {', '.join(muestra)}.", rng))

    # tablas SQL
    if sql:
        tablas = list(dict.fromkeys(
            re.findall(r'CREATE TABLE\s+(\w+)', sql[0].codigo, re.IGNORECASE)))
        muestra = rng.sample(tablas, min(5, len(tablas)))
        falsas = [t for t in ["pedido","factura","inventario","cliente","empleado"] if t not in tablas]
        banco.append(_rm(
            "¿Cuáles tablas SÍ existen en el schema SQL?",
            muestra, falsas[:4],
            f"Tablas reales: {', '.join(tablas)}.", rng))

        # Tipos de datos usados
        tipos = list(dict.fromkeys(re.findall(r'\b(INTEGER|TEXT|TIMESTAMP|DATE|BOOLEAN|REAL)\b', sql[0].codigo)))
        if tipos:
            banco.append(_rm(
                "¿Cuáles tipos de dato se usan en el schema SQL?",
                tipos, ["FLOAT","VARCHAR","MONEY","BLOB"],
                f"Tipos usados: {', '.join(tipos)}.", rng))

        # Tablas con ON DELETE CASCADE
        cascade_tablas = list(dict.fromkeys(re.findall(
            r'CREATE TABLE\s+(\w+).*?ON DELETE CASCADE', sql[0].codigo, re.DOTALL | re.IGNORECASE)))
        if cascade_tablas:
            falsas_c = [t for t in tablas if t not in cascade_tablas]
            banco.append(_rm(
                "¿Cuáles tablas tienen FOREIGN KEY con ON DELETE CASCADE?",
                cascade_tablas[:4], falsas_c[:4],
                f"Tablas con CASCADE: {', '.join(cascade_tablas)}.", rng))

    # imports Python (por archivo)
    for pf in py:
        imports = list(dict.fromkeys([
            l.strip() for l in _novacias(pf.codigo)
            if l.strip().startswith(("import ","from "))]))[:6]
        if len(imports) >= 2:
            banco.append(_rm(
                f"¿Cuáles importaciones están en '{pf.titulo}'?",
                imports[:4],
                ["import pandas as pd","from django.db import models","import tensorflow"],
                f"Imports reales en {pf.titulo}: {', '.join(imports)}.", rng))

    # campos del alumno
    campos = [f"{k}: {v}" for k, v in r.alumno.items()]
    banco.append(_rm(
        "¿Cuáles datos del alumno son correctos según la sección 1.1?",
        campos, ["Nombre: John Doe","Email: fake@fake.com","Grupo: TSI00"],
        "Los datos correctos están en la sección 1.1.", rng))

    # bloques Jinja2 en HTML
    for hf in html:
        bloques = list(dict.fromkeys(re.findall(r'{%\s*block\s+(\w+)', hf.codigo)))
        if len(bloques) >= 2:
            banco.append(_rm(
                f"¿Cuáles bloques Jinja2 están en '{hf.titulo.split('/')[-1]}'?",
                bloques[:4], ["sidebar","footer","meta","ads"],
                f"Bloques reales: {', '.join(bloques)}.", rng))

    # endpoints url_for en HTML
    for hf in html:
        endpoints = list(dict.fromkeys(re.findall(r"url_for\('([^']+)'", hf.codigo)))
        if len(endpoints) >= 2:
            banco.append(_rm(
                f"¿Cuáles endpoints se usan con url_for en '{hf.titulo.split('/')[-1]}'?",
                endpoints[:4], ["admin.panel","shop.cart","auth.register"],
                f"Endpoints reales: {', '.join(endpoints)}.", rng))

    return banco


# ── Banco de preguntas: Completar código ──────────────────────────────────────

PY_TARGETS = [
    "Flask","Blueprint","render_template","redirect","url_for","session",
    "request","flash","jsonify","abort","get_flashed_messages",
    "psycopg2","RealDictCursor","get_conexion",
]
PY_KW = ["def ","return ","from ","import ","if ","elif ","else:","try:","except ","with ","for "]
SQL_TARGETS = [
    "PRIMARY KEY","FOREIGN KEY","REFERENCES","NOT NULL","DEFAULT","CHECK",
    "UNIQUE","INTEGER","TEXT","TIMESTAMP","DATE","ON DELETE CASCADE",
    "ON UPDATE CASCADE","GENERATED ALWAYS AS IDENTITY","ON DELETE RESTRICT",
    "ON DELETE SET NULL",
]
HTML_TARGETS = ["extends","block","endblock","for","endfor","if","endif","url_for","with","endwith"]


def _hacer_hueco(linea: str, target: str) -> tuple[str, str] | None:
    if target not in linea:
        return None
    return linea.replace(target, "_____", 1), target


def _banco_cc(r: ResultadoValidacion, rng: random.Random) -> list[CompletarCodigo]:
    banco: list[CompletarCodigo] = []
    py   = _by_ext(r.archivos, "py")
    sql  = _by_ext(r.archivos, "sql")
    html = _by_ext(r.archivos, "html")

    vistos: set[str] = set()

    # ── Python: librerías/funciones Flask ────────────────────────────────────
    for pf in py:
        lineas = _novacias(pf.codigo)
        rng.shuffle(lineas)
        for linea in lineas:
            if len(linea.strip()) > 100 or linea.strip() in vistos:
                continue
            for t in PY_TARGETS:
                if t in linea.strip():
                    hueco, resp = linea.replace(t, "_____", 1), t
                    vistos.add(linea.strip())
                    banco.append(CompletarCodigo(
                        instruccion=f"Completa la línea de '{pf.titulo}':",
                        codigo_con_huecos=hueco.strip(),
                        respuestas=[resp],
                        explicacion=f"Línea original: {linea.strip()}"))
                    break

    # ── Python: keywords ─────────────────────────────────────────────────────
    for pf in py:
        lineas = _novacias(pf.codigo)
        rng.shuffle(lineas)
        for linea in lineas:
            if len(linea.strip()) > 80 or linea.strip() in vistos:
                continue
            for t in PY_KW:
                if linea.strip().startswith(t) and len(linea.strip()) > len(t) + 3:
                    hueco = t.replace(t, "_____", 1) + linea.strip()[len(t):]
                    vistos.add(linea.strip())
                    banco.append(CompletarCodigo(
                        instruccion=f"Completa la instrucción en '{pf.titulo}':",
                        codigo_con_huecos=hueco,
                        respuestas=[t.strip()],
                        explicacion=f"Línea original: {linea.strip()}"))
                    break

    # ── SQL ───────────────────────────────────────────────────────────────────
    for pf in sql:
        lineas = _novacias(pf.codigo)
        rng.shuffle(lineas)
        for linea in lineas:
            if len(linea.strip()) > 90 or linea.strip() in vistos:
                continue
            for t in SQL_TARGETS:
                if t.lower() in linea.lower():
                    hueco = re.sub(re.escape(t), "_____", linea.strip(), count=1, flags=re.IGNORECASE)
                    vistos.add(linea.strip())
                    banco.append(CompletarCodigo(
                        instruccion=f"Completa la línea SQL de '{pf.titulo}':",
                        codigo_con_huecos=hueco,
                        respuestas=[t],
                        explicacion=f"Línea original: {linea.strip()}"))
                    break

    # ── HTML / Jinja2 ─────────────────────────────────────────────────────────
    for hf in html:
        lineas = _novacias(hf.codigo)
        rng.shuffle(lineas)
        for linea in lineas:
            if len(linea.strip()) > 120 or linea.strip() in vistos:
                continue
            for t in HTML_TARGETS:
                pattern = r'\{%-?\s*' + re.escape(t) + r'[\s%]'
                if re.search(pattern, linea, re.IGNORECASE):
                    hueco = re.sub(re.escape(t), "_____", linea.strip(), count=1)
                    vistos.add(linea.strip())
                    banco.append(CompletarCodigo(
                        instruccion=f"Completa la directiva Jinja2 en '{hf.titulo.split('/')[-1]}':",
                        codigo_con_huecos=hueco,
                        respuestas=[t],
                        explicacion=f"Línea original: {linea.strip()}"))
                    break

    return banco


# ── Generadores finales ────────────────────────────────────────────────────────

def gen_opcion_multiple(r: ResultadoValidacion, n=20, seed=42) -> list[OpcionMultiple]:
    rng = random.Random(seed)
    banco = _banco_om(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_respuesta_multiple(r: ResultadoValidacion, n=15, seed=42) -> list[RespuestaMultiple]:
    rng = random.Random(seed)
    banco = _banco_rm(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_completar_codigo(r: ResultadoValidacion, n=15, seed=42) -> list[CompletarCodigo]:
    rng = random.Random(seed)
    banco = _banco_cc(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_combinado(r: ResultadoValidacion, n=20, seed=42) -> list[Pregunta]:
    rng = random.Random(seed)
    om  = gen_opcion_multiple(r, 7, seed)
    rm  = gen_respuesta_multiple(r, 7, seed)
    cc  = gen_completar_codigo(r, 6, seed)
    mezclado: list[Pregunta] = om + rm + cc
    rng.shuffle(mezclado)
    return mezclado[:n]


DURACIONES = {
    "opcion_multiple":    40,
    "respuesta_multiple": 40,
    "completar_codigo":   40,
    "combinado":          40,
}

TITULOS = {
    "opcion_multiple":    ("Examen de opción múltiple",    "Selecciona la única respuesta correcta en cada pregunta."),
    "respuesta_multiple": ("Examen de respuesta múltiple", "Puede haber más de una respuesta correcta por pregunta."),
    "completar_codigo":   ("Examen de completar código",   "Escribe la palabra o instrucción que va en cada hueco (_____)." ),
    "combinado":          ("Examen combinado",              "Mezcla de opción múltiple, respuesta múltiple y completar código."),
}

def generar_examen(r: ResultadoValidacion, tipo: str, seed=42) -> Examen:
    titulo, desc = TITULOS.get(tipo, ("Examen",""))
    gens = {
        "opcion_multiple":    lambda: gen_opcion_multiple(r, 20, seed),
        "respuesta_multiple": lambda: gen_respuesta_multiple(r, 15, seed),
        "completar_codigo":   lambda: gen_completar_codigo(r, 15, seed),
        "combinado":          lambda: gen_combinado(r, 20, seed),
    }
    return Examen(titulo=titulo, descripcion=desc, tipo=tipo,
                  duracion_minutos=DURACIONES[tipo],
                  preguntas=gens[tipo]())