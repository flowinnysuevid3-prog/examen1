"""
examenes.py — Generador de exámenes 100% de código.

- 40 preguntas por tipo (o todas las disponibles si el md tiene poco)
- Solo preguntas de código: imports, funciones, rutas, SQL, Jinja2
- Retroalimentación específica por pregunta indicando dónde está la respuesta
- Sin preguntas de datos personales del alumno
"""

from __future__ import annotations
import random, re
from dataclasses import dataclass, field
from parser import ResultadoValidacion, Archivo


# ── Tipos ─────────────────────────────────────────────────────────────────────

@dataclass
class OpcionMultiple:
    tipo: str = "opcion_multiple"
    pregunta: str = ""
    opciones: list[str] = field(default_factory=list)
    correcta: int = 0
    explicacion: str = ""
    retroalimentacion: str = ""   # se muestra si falla

@dataclass
class RespuestaMultiple:
    tipo: str = "respuesta_multiple"
    pregunta: str = ""
    opciones: list[str] = field(default_factory=list)
    correctas: list[int] = field(default_factory=list)
    explicacion: str = ""
    retroalimentacion: str = ""

@dataclass
class CompletarCodigo:
    tipo: str = "completar_codigo"
    instruccion: str = ""
    codigo_con_huecos: str = ""
    respuestas: list[str] = field(default_factory=list)
    explicacion: str = ""
    retroalimentacion: str = ""

Pregunta = OpcionMultiple | RespuestaMultiple | CompletarCodigo

@dataclass
class Examen:
    titulo: str
    descripcion: str
    tipo: str
    duracion_minutos: int
    preguntas: list[Pregunta] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _limpia(titulo): return titulo.strip().strip('`').strip()
def _py(archivos):   return [a for a in archivos if _limpia(a.titulo).endswith('.py')]
def _sql(archivos):  return [a for a in archivos if _limpia(a.titulo).endswith('.sql') or a.lenguaje.lower() == 'sql']
def _html(archivos): return [a for a in archivos if _limpia(a.titulo).endswith('.html')]
def _novacias(codigo): return [l for l in codigo.splitlines() if l.strip()]

def _om(pregunta, val_correcto, resto, explicacion, retroalimentacion, rng):
    opciones = [val_correcto] + [r for r in resto if r != val_correcto][:3]
    while len(opciones) < 4:
        opciones.append("# ninguna de las anteriores")
    opciones = opciones[:4]
    rng.shuffle(opciones)
    return OpcionMultiple(
        pregunta=pregunta, opciones=opciones,
        correcta=opciones.index(val_correcto),
        explicacion=explicacion,
        retroalimentacion=retroalimentacion,
    )

def _rm(pregunta, correctas_vals, falsas_vals, explicacion, retroalimentacion, rng):
    opciones = list(correctas_vals) + falsas_vals
    rng.shuffle(opciones)
    idxs = sorted([opciones.index(v) for v in correctas_vals if v in opciones])
    return RespuestaMultiple(
        pregunta=pregunta, opciones=opciones, correctas=idxs,
        explicacion=explicacion, retroalimentacion=retroalimentacion,
    )

def _cc(instruccion, linea_original, target, explicacion, retroalimentacion):
    hueco = linea_original.replace(target, "_____", 1).strip()
    return CompletarCodigo(
        instruccion=instruccion,
        codigo_con_huecos=hueco,
        respuestas=[target.strip()],
        explicacion=explicacion,
        retroalimentacion=retroalimentacion,
    )

def _dedup(banco):
    """Elimina preguntas con el mismo enunciado o el mismo hueco."""
    vistos = set()
    resultado = []
    for p in banco:
        if hasattr(p, 'codigo_con_huecos'):
            key = p.codigo_con_huecos
        elif hasattr(p, 'pregunta'):
            key = p.pregunta
        else:
            key = p.instruccion
        if key not in vistos:
            vistos.add(key)
            resultado.append(p)
    return resultado


# ── BANCO OPCIÓN MÚLTIPLE (código puro) ───────────────────────────────────────

def _banco_om(r: ResultadoValidacion, rng: random.Random) -> list[OpcionMultiple]:
    banco = []
    py_files  = _py(r.archivos)
    sql_files = _sql(r.archivos)
    html_files= _html(r.archivos)

    # ── PYTHON: imports ────────────────────────────────────────────────────────
    todos_imports = []
    for a in py_files:
        for l in _novacias(a.codigo):
            if l.strip().startswith(('import ','from ')):
                todos_imports.append((a.titulo, l.strip()))
    rng.shuffle(todos_imports)
    usados_imp = set()
    for fname, imp in todos_imports:
        if imp in usados_imp: continue
        usados_imp.add(imp)
        banco.append(_om(
            f"¿Cuál de estas líneas de importación existe en '{fname}'?",
            imp,
            ["import pandas as pd", "from django.db import models",
             "import tensorflow as tf", "from numpy import array"],
            f"La línea '{imp}' está declarada en {fname}.",
            f"Revisa la sección de imports al inicio de {fname}. La respuesta correcta es:\n{imp}",
            rng
        ))

    # ── PYTHON: definiciones de funciones ──────────────────────────────────────
    for a in py_files:
        defs = [l.strip() for l in _novacias(a.codigo)
                if l.strip().startswith('def ') and len(l.strip()) < 80]
        rng.shuffle(defs)
        for d in defs[:6]:
            nombre_func = d.split('(')[0].replace('def ','').strip()
            banco.append(_om(
                f"¿Cuál función está definida en '{a.titulo}'?",
                d,
                ["def procesar_pago(monto, cuenta):",
                 "def enviar_correo(destinatario, asunto):",
                 "def calcular_descuento(precio, porcentaje):"],
                f"'{d}' está definida en {a.titulo}.",
                f"Busca 'def {nombre_func}' en {a.titulo}. La firma correcta es:\n{d}",
                rng
            ))

    # ── PYTHON: rutas (decoradores) ─────────────────────────────────────────────
    for a in py_files:
        rutas = [l.strip() for l in _novacias(a.codigo)
                 if l.strip().startswith('@') and 'route' in l and len(l.strip()) < 100]
        rng.shuffle(rutas)
        for ruta in rutas[:5]:
            banco.append(_om(
                f"¿Cuál decorador de ruta existe en '{a.titulo}'?",
                ruta,
                ['@app.route("/shop/cart", methods=["GET"])',
                 '@bp.route("/admin/users", methods=["POST"])',
                 '@app.route("/payment/confirm")'],
                f"'{ruta}' está en {a.titulo}.",
                f"Busca los decoradores @route en {a.titulo}. La ruta correcta es:\n{ruta}",
                rng
            ))

    # ── PYTHON: líneas return con lógica ───────────────────────────────────────
    for a in py_files:
        returns = [l.strip() for l in _novacias(a.codigo)
                   if l.strip().startswith('return ') and
                   any(kw in l for kw in ['render_template','redirect','jsonify','url_for'])
                   and len(l.strip()) < 100]
        rng.shuffle(returns)
        for ret in returns[:4]:
            banco.append(_om(
                f"¿Cuál instrucción return existe en '{a.titulo}'?",
                ret,
                ["return render_template('admin/panel.html')",
                 "return redirect(url_for('shop.cart'))",
                 "return jsonify({'status': 'error'})"],
                f"'{ret}' está en {a.titulo}.",
                f"Revisa los returns en {a.titulo}. La respuesta correcta es:\n{ret}",
                rng
            ))

    # ── PYTHON: with/cursor ────────────────────────────────────────────────────
    for a in py_files:
        withs = [l.strip() for l in _novacias(a.codigo)
                 if l.strip().startswith('with ') and len(l.strip()) < 80]
        rng.shuffle(withs)
        for w in withs[:3]:
            banco.append(_om(
                f"¿Cuál bloque 'with' aparece en '{a.titulo}'?",
                w,
                ["with open('archivo.txt', 'r') as f:",
                 "with sqlite3.connect('db.sqlite') as conn:",
                 "with requests.Session() as s:"],
                f"'{w}' aparece en {a.titulo}.",
                f"Busca los bloques 'with' en {a.titulo}. La respuesta es:\n{w}",
                rng
            ))

    # ── SQL: tablas ─────────────────────────────────────────────────────────────
    if sql_files:
        tablas = list(dict.fromkeys(
            re.findall(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)',
                       sql_files[0].codigo, re.I)))
        falsas_t = [t for t in
                    ["pedido","factura","inventario","producto","empleado","cliente","proveedor"]
                    if t not in tablas]
        for tabla in rng.sample(tablas, min(6, len(tablas))):
            banco.append(_om(
                "¿Cuál tabla SÍ se define en el schema SQL del proyecto?",
                tabla,
                rng.sample(falsas_t, min(3,len(falsas_t))),
                f"La tabla '{tabla}' se crea con CREATE TABLE en script.sql.",
                f"Busca 'CREATE TABLE {tabla}' en script.sql. Esa tabla sí existe en el schema.",
                rng
            ))

    # ── SQL: columnas ───────────────────────────────────────────────────────────
    if sql_files:
        for tabla in list(dict.fromkeys(
            re.findall(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)',
                       sql_files[0].codigo, re.I)))[:6]:
            patron = rf'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?{tabla}\s*\((.*?)(?:CREATE TABLE|\Z)'
            bloque = re.search(patron, sql_files[0].codigo, re.DOTALL|re.I)
            if bloque:
                cols = re.findall(r'^\s+(\w+)\s+(?:INTEGER|TEXT|TIMESTAMP|DATE|BOOLEAN|REAL)',
                                  bloque.group(1), re.M|re.I)
                cols = [c for c in cols if c.upper() not in
                        ('FOREIGN','PRIMARY','CONSTRAINT','UNIQUE','CHECK')]
                if cols:
                    col = rng.choice(cols)
                    banco.append(_om(
                        f"¿Cuál columna pertenece a la tabla '{tabla}' en el schema SQL?",
                        col,
                        ["precio_unitario","codigo_barras","nombre_comercial","stock_minimo"],
                        f"La columna '{col}' está definida dentro de CREATE TABLE {tabla}.",
                        f"Abre script.sql y busca 'CREATE TABLE {tabla}'. La columna '{col}' está ahí.",
                        rng
                    ))

    # ── SQL: CHECK constraints ──────────────────────────────────────────────────
    if sql_files:
        checks = re.findall(r"CHECK\((.+?)\)", sql_files[0].codigo)
        for c in rng.sample(checks, min(5, len(checks))):
            banco.append(_om(
                "¿Cuál CHECK constraint aparece en el schema SQL?",
                f"CHECK({c})",
                ["CHECK(precio > 0)","CHECK(cantidad BETWEEN 1 AND 999)",
                 "CHECK(activo IN (0,1))"],
                f"El constraint CHECK({c}) está en script.sql.",
                f"Busca los CHECK en script.sql. El constraint correcto es:\nCHECK({c})",
                rng
            ))

    # ── SQL: FOREIGN KEY ────────────────────────────────────────────────────────
    if sql_files:
        fks = re.findall(
            r'FOREIGN KEY\s*\((\w+)\)\s*REFERENCES\s*(\w+)\s*\((\w+)\)',
            sql_files[0].codigo, re.I)
        for col, ref_tabla, ref_col in rng.sample(fks, min(4, len(fks))):
            fk_str = f"FOREIGN KEY ({col}) REFERENCES {ref_tabla}({ref_col})"
            banco.append(_om(
                "¿Cuál FOREIGN KEY está definida en el schema SQL?",
                fk_str,
                ["FOREIGN KEY (id_producto) REFERENCES catalogo(id)",
                 "FOREIGN KEY (empleado_id) REFERENCES staff(id)",
                 "FOREIGN KEY (orden_id) REFERENCES pedidos(cod)"],
                f"'{fk_str}' está en script.sql.",
                f"Busca las FOREIGN KEY en script.sql. La correcta es:\n{fk_str}",
                rng
            ))

    # ── SQL: tipo de dato de columna ────────────────────────────────────────────
    if sql_files:
        col_tipos = re.findall(
            r'^\s+(\w+)\s+(INTEGER|TEXT|TIMESTAMP|DATE|BOOLEAN|REAL)',
            sql_files[0].codigo, re.M|re.I)
        col_tipos = [(c,t) for c,t in col_tipos
                     if c.upper() not in ('FOREIGN','PRIMARY','CONSTRAINT')]
        for col, tipo in rng.sample(col_tipos, min(5, len(col_tipos))):
            banco.append(_om(
                f"¿Qué tipo de dato tiene la columna '{col}' en el schema SQL?",
                tipo.upper(),
                [t for t in ["INTEGER","TEXT","TIMESTAMP","DATE","BOOLEAN","REAL"]
                 if t != tipo.upper()][:3],
                f"La columna '{col}' es de tipo {tipo.upper()} en script.sql.",
                f"Busca '{col}' en script.sql. Su tipo de dato es {tipo.upper()}.",
                rng
            ))

    # ── HTML: extends ───────────────────────────────────────────────────────────
    for a in html_files:
        ext = re.search(r'{%\s*extends\s*"([^"]+)"', a.codigo)
        if ext:
            banco.append(_om(
                f"¿De qué template hereda '{a.titulo.split('/')[-1]}'?",
                ext.group(1),
                ["base/main.html","static/layout.html","templates/root.html"],
                f"{{% extends %}} apunta a '{ext.group(1)}' en {a.titulo.split('/')[-1]}.",
                f"Busca la directiva {{% extends %}} al inicio de {a.titulo.split('/')[-1]}. Hereda de: {ext.group(1)}",
                rng
            ))

    # ── HTML: bloques ────────────────────────────────────────────────────────────
    for a in html_files:
        bloques = list(dict.fromkeys(re.findall(r'{%\s*block\s+(\w+)', a.codigo)))
        for b in rng.sample(bloques, min(3, len(bloques))):
            banco.append(_om(
                f"¿Cuál bloque Jinja2 está definido en '{a.titulo.split('/')[-1]}'?",
                f"{{% block {b} %}}",
                ["{{% block sidebar %}}","{{% block footer %}}","{{% block scripts %}}"],
                f"El bloque '{b}' aparece en {a.titulo.split('/')[-1]}.",
                f"Busca '{{% block {b} %}}' en {a.titulo.split('/')[-1]}. Ese bloque sí existe.",
                rng
            ))

    # ── HTML: url_for ────────────────────────────────────────────────────────────
    for a in html_files:
        endpoints = list(dict.fromkeys(re.findall(r"url_for\('([^']+)'", a.codigo)))
        for ep in rng.sample(endpoints, min(4, len(endpoints))):
            banco.append(_om(
                f"¿Cuál endpoint se referencia con url_for en '{a.titulo.split('/')[-1]}'?",
                f"url_for('{ep}')",
                ["url_for('admin.panel')","url_for('shop.cart')","url_for('auth.register')"],
                f"url_for('{ep}') aparece en {a.titulo.split('/')[-1]}.",
                f"Busca url_for en {a.titulo.split('/')[-1]}. El endpoint correcto es: url_for('{ep}')",
                rng
            ))

    return _dedup(banco)


# ── BANCO RESPUESTA MÚLTIPLE ──────────────────────────────────────────────────

def _banco_rm(r: ResultadoValidacion, rng: random.Random) -> list[RespuestaMultiple]:
    banco = []
    py_files  = _py(r.archivos)
    sql_files = _sql(r.archivos)
    html_files= _html(r.archivos)

    # imports por archivo
    for a in py_files:
        imports = list(dict.fromkeys([
            l.strip() for l in _novacias(a.codigo)
            if l.strip().startswith(('import ','from '))]))
        muestra = imports[:6] if len(imports) >= 3 else imports
        if len(muestra) >= 2:
            banco.append(_rm(
                f"¿Cuáles de estas importaciones están en '{a.titulo}'?",
                muestra[:4],
                ["import pandas as pd","from django.db import models",
                 "import tensorflow","from numpy import array"],
                f"Imports reales en {a.titulo}: {', '.join(muestra)}.",
                f"Abre {a.titulo} y revisa los imports al inicio. Los correctos son:\n" + "\n".join(muestra[:4]),
                rng
            ))

    # funciones por archivo
    for a in py_files:
        defs = list(dict.fromkeys([
            l.strip().split('(')[0].replace('def ','').strip()
            for l in _novacias(a.codigo) if l.strip().startswith('def ')]))
        if len(defs) >= 3:
            muestra = defs[:5]
            banco.append(_rm(
                f"¿Cuáles funciones están definidas en '{a.titulo}'?",
                muestra[:4],
                ["procesar_pago","enviar_factura","calcular_impuesto","validar_stock"],
                f"Funciones reales en {a.titulo}: {', '.join(defs)}.",
                f"Busca 'def ' en {a.titulo}. Las funciones que SÍ existen son:\n" + "\n".join(f"def {d}(...)" for d in muestra[:4]),
                rng
            ))

    # rutas por archivo
    for a in py_files:
        rutas = list(dict.fromkeys([
            re.search(r'["\']([^"\']+)["\']', l).group(1)
            for l in _novacias(a.codigo)
            if '@' in l and 'route' in l and re.search(r'["\']([^"\']+)["\']', l)]))
        if len(rutas) >= 3:
            muestra = rutas[:5]
            banco.append(_rm(
                f"¿Cuáles rutas están definidas en '{a.titulo}'?",
                muestra[:4],
                ["/shop/cart","/admin/dashboard","/payment/confirm"],
                f"Rutas reales en {a.titulo}: {', '.join(rutas)}.",
                f"Busca los decoradores @route en {a.titulo}. Las rutas que SÍ existen:\n" + "\n".join(muestra[:4]),
                rng
            ))

    # tablas SQL
    if sql_files:
        tablas = list(dict.fromkeys(
            re.findall(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)',
                       sql_files[0].codigo, re.I)))
        falsas = [t for t in ["pedido","factura","inventario","producto","empleado"]
                  if t not in tablas]
        muestra = rng.sample(tablas, min(5, len(tablas)))
        banco.append(_rm(
            "¿Cuáles tablas SÍ existen en el schema SQL?",
            muestra,
            falsas[:4],
            f"Tablas reales: {', '.join(tablas)}.",
            f"Busca los CREATE TABLE en script.sql. Las tablas que SÍ existen:\n" + "\n".join(muestra),
            rng
        ))

    # tipos de dato usados
    if sql_files:
        tipos = list(dict.fromkeys(re.findall(
            r'\b(INTEGER|TEXT|TIMESTAMP|DATE|BOOLEAN|REAL)\b',
            sql_files[0].codigo)))
        if len(tipos) >= 2:
            banco.append(_rm(
                "¿Cuáles tipos de dato se usan en el schema SQL?",
                tipos,
                [t for t in ["FLOAT","VARCHAR","MONEY","BLOB","CHAR"] if t not in tipos],
                f"Tipos usados: {', '.join(tipos)}.",
                f"Revisa las definiciones de columnas en script.sql. Los tipos que SÍ aparecen:\n" + ", ".join(tipos),
                rng
            ))

    # columnas de una tabla
    if sql_files:
        for tabla in rng.sample(
            list(dict.fromkeys(re.findall(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)',
                               sql_files[0].codigo, re.I))), min(4,14)):
            patron = rf'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?{tabla}\s*\((.*?)(?:CREATE TABLE|\Z)'
            bloque = re.search(patron, sql_files[0].codigo, re.DOTALL|re.I)
            if bloque:
                cols = re.findall(r'^\s+(\w+)\s+\w+', bloque.group(1), re.M)
                cols = [c for c in cols if c.upper() not in
                        ('FOREIGN','PRIMARY','CONSTRAINT','UNIQUE','CHECK')]
                if len(cols) >= 3:
                    muestra = cols[:5]
                    banco.append(_rm(
                        f"¿Cuáles columnas pertenecen a la tabla '{tabla}'?",
                        muestra,
                        ["precio_total","codigo_barras","nombre_comercial","stock_minimo"],
                        f"Columnas de {tabla}: {', '.join(cols)}.",
                        f"Busca 'CREATE TABLE {tabla}' en script.sql. Las columnas correctas:\n" + "\n".join(muestra),
                        rng
                    ))

    # bloques HTML
    for a in html_files:
        bloques = list(dict.fromkeys(re.findall(r'{%\s*block\s+(\w+)', a.codigo)))
        if len(bloques) >= 2:
            banco.append(_rm(
                f"¿Cuáles bloques Jinja2 están en '{a.titulo.split('/')[-1]}'?",
                bloques[:4],
                ["sidebar","footer","meta","ads","scripts_extra"],
                f"Bloques reales en {a.titulo.split('/')[-1]}: {', '.join(bloques)}.",
                f"Busca '{{% block %}}' en {a.titulo.split('/')[-1]}. Los bloques que SÍ existen:\n" + "\n".join(f"{{% block {b} %}}" for b in bloques[:4]),
                rng
            ))

    # endpoints url_for
    for a in html_files:
        endpoints = list(dict.fromkeys(re.findall(r"url_for\('([^']+)'", a.codigo)))
        if len(endpoints) >= 3:
            muestra = endpoints[:5]
            banco.append(_rm(
                f"¿Cuáles endpoints se usan con url_for en '{a.titulo.split('/')[-1]}'?",
                muestra[:4],
                ["admin.panel","shop.cart","auth.register","payment.confirm"],
                f"Endpoints reales: {', '.join(endpoints)}.",
                f"Busca url_for( en {a.titulo.split('/')[-1]}. Los endpoints correctos:\n" + "\n".join(f"url_for('{ep}')" for ep in muestra[:4]),
                rng
            ))

    return _dedup(banco)


# ── BANCO COMPLETAR CÓDIGO ────────────────────────────────────────────────────

PY_FLASK = [
    "Flask","Blueprint","render_template","redirect","url_for",
    "session","request","flash","jsonify","abort","g","current_app",
    "psycopg2","RealDictCursor","get_conexion","wraps",
    "cursor","fetchone","fetchall","execute","commit","rollback",
    "session.get","session.pop","session.clear",
    "request.form","request.files","request.method","request.args",
    "request.json","request.get_json",
    "app.route","bp.route","blueprint",
    "os.environ","datetime","timedelta","uuid","json","base64",
    "check_password_hash","generate_password_hash",
    "login_required","make_response",
]
PY_KW    = [
    "def ","return ","from ","import ","if ","elif ","else:",
    "try:","except ","with ","for ","while ","class ",
    "raise ","yield ","lambda ","assert ","pass","break","continue",
    "not ","and ","or ","in ","is ","None","True","False",
]
SQL_KW   = [
    "PRIMARY KEY","FOREIGN KEY","REFERENCES","NOT NULL","DEFAULT",
    "CHECK","UNIQUE","INTEGER","TEXT","TIMESTAMP","DATE","BOOLEAN","REAL",
    "ON DELETE CASCADE","ON UPDATE CASCADE","GENERATED ALWAYS AS IDENTITY",
    "ON DELETE RESTRICT","ON DELETE SET NULL","CREATE TABLE","CREATE INDEX",
    "INSERT INTO","VALUES","SELECT","WHERE","JOIN","LEFT JOIN","INNER JOIN",
    "GROUP BY","ORDER BY","HAVING","LIMIT","OFFSET","RETURNING",
    "AT TIME ZONE","STRING_AGG","COUNT","SUM","AVG","MAX","MIN",
]
HTML_KW  = ["extends","block","endblock","for","endfor","if","endif","url_for",
            "with","endwith","set","include","macro","call","filter"]


def _banco_cc(r: ResultadoValidacion, rng: random.Random) -> list[CompletarCodigo]:
    banco = []
    py_files  = _py(r.archivos)
    sql_files = _sql(r.archivos)
    html_files= _html(r.archivos)
    vistos: set[str] = set()

    # Python Flask/librerías
    for a in py_files:
        lineas = _novacias(a.codigo)
        rng.shuffle(lineas)
        for l in lineas:
            ls = l.strip()
            if len(ls) > 100 or ls in vistos: continue
            for t in PY_FLASK:
                if t in ls:
                    vistos.add(ls)
                    banco.append(_cc(
                        f"Completa la línea de '{a.titulo}':",
                        ls, t,
                        f"Línea original: {ls}",
                        f"La palabra que falta es '{t}'. Está en {a.titulo}:\n{ls}",
                    ))
                    break

    # Python keywords
    for a in py_files:
        lineas = _novacias(a.codigo)
        rng.shuffle(lineas)
        for l in lineas:
            ls = l.strip()
            if len(ls) > 80 or ls in vistos: continue
            for t in PY_KW:
                if ls.startswith(t) and len(ls) > len(t)+3:
                    vistos.add(ls)
                    banco.append(_cc(
                        f"Completa la instrucción en '{a.titulo}':",
                        ls, t,
                        f"Línea original: {ls}",
                        f"La palabra clave que falta es '{t.strip()}'. La línea completa es:\n{ls}",
                    ))
                    break

    # SQL
    for a in sql_files:
        lineas = _novacias(a.codigo)
        rng.shuffle(lineas)
        for l in lineas:
            ls = l.strip()
            if len(ls) > 90 or ls in vistos or ls.startswith('--'): continue
            for t in SQL_KW:
                if t.lower() in ls.lower():
                    hueco = re.sub(re.escape(t), "_____", ls, count=1, flags=re.I)
                    if hueco == ls: continue
                    vistos.add(ls)
                    banco.append(CompletarCodigo(
                        instruccion=f"Completa la línea SQL de '{a.titulo}':",
                        codigo_con_huecos=hueco,
                        respuestas=[t],
                        explicacion=f"Línea original: {ls}",
                        retroalimentacion=f"La palabra SQL que falta es '{t}'. La línea completa es:\n{ls}",
                    ))
                    break

    # Jinja2 / HTML
    for a in html_files:
        lineas = _novacias(a.codigo)
        rng.shuffle(lineas)
        for l in lineas:
            ls = l.strip()
            if len(ls) > 120 or ls in vistos: continue
            for t in HTML_KW:
                pattern = r'\{%-?\s*' + re.escape(t) + r'[\s%{]'
                if re.search(pattern, ls, re.I):
                    hueco = re.sub(re.escape(t), "_____", ls, count=1)
                    if hueco == ls: continue
                    vistos.add(ls)
                    banco.append(CompletarCodigo(
                        instruccion=f"Completa la directiva Jinja2 en '{a.titulo.split('/')[-1]}':",
                        codigo_con_huecos=hueco,
                        respuestas=[t],
                        explicacion=f"Línea original: {ls}",
                        retroalimentacion=f"La directiva Jinja2 que falta es '{t}'. La línea completa es:\n{ls}",
                    ))
                    break

    return _dedup(banco)


# ── Generadores finales ────────────────────────────────────────────────────────

def gen_opcion_multiple(r, n=40, seed=42):
    rng = random.Random(seed)
    banco = _banco_om(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_respuesta_multiple(r, n=40, seed=42):
    rng = random.Random(seed)
    banco = _banco_rm(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_completar_codigo(r, n=40, seed=42):
    rng = random.Random(seed)
    banco = _banco_cc(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_combinado(r, n=40, seed=42):
    rng = random.Random(seed)
    om  = gen_opcion_multiple(r, 14, seed)
    rm  = gen_respuesta_multiple(r, 13, seed)
    cc  = gen_completar_codigo(r, 13, seed)
    mezclado = om + rm + cc
    rng.shuffle(mezclado)
    return mezclado[:n]


TITULOS = {
    "opcion_multiple":    ("Examen de opción múltiple",    "Selecciona la única respuesta correcta en cada pregunta."),
    "respuesta_multiple": ("Examen de respuesta múltiple", "Puede haber más de una respuesta correcta por pregunta."),
    "completar_codigo":   ("Examen de completar código",   "Escribe la palabra o instrucción que va en cada hueco (_____)."),
    "combinado":          ("Examen combinado",              "Mezcla de opción múltiple, respuesta múltiple y completar código."),
}

def generar_examen(r: ResultadoValidacion, tipo: str, seed=42):
    titulo, desc = TITULOS.get(tipo, ("Examen",""))
    gens = {
        "opcion_multiple":    lambda: gen_opcion_multiple(r, 40, seed),
        "respuesta_multiple": lambda: gen_respuesta_multiple(r, 40, seed),
        "completar_codigo":   lambda: gen_completar_codigo(r, 40, seed),
        "combinado":          lambda: gen_combinado(r, 40, seed),
    }
    from examenes import Examen
    return Examen(titulo=titulo, descripcion=desc, tipo=tipo,
                  duracion_minutos=40, preguntas=gens[tipo]())