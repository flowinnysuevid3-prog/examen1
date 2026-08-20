"""
examenes.py — Exámenes profundos de código real.

Cantidades por tipo:
  opcion_multiple    → 25 preguntas
  respuesta_multiple → 25 preguntas  
  completar_codigo   → 10 preguntas (bloques reales con 3-4 huecos)
  combinado          → 30 preguntas

Solo preguntas de código real: lógica, parámetros, SQL, HTML.
Sin preguntas de datos personales del alumno.
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
    retroalimentacion: str = ""

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


# ── Utilidades ─────────────────────────────────────────────────────────────────

def _limpia(titulo: str) -> str:
    return titulo.strip().strip('`').strip()

def _py(archivos):
    return [a for a in archivos if _limpia(a.titulo).endswith('.py')]

def _sql(archivos):
    return [a for a in archivos if _limpia(a.titulo).endswith('.sql')
            or a.lenguaje.lower() == 'sql']

def _html(archivos):
    return [a for a in archivos if _limpia(a.titulo).endswith('.html')]

def _novacias(codigo: str) -> list[str]:
    return [l for l in codigo.splitlines() if l.strip()]

def _nombre(a: Archivo) -> str:
    return _limpia(a.titulo).split('/')[-1]

def _om(pregunta, correcto, resto, explicacion, retro, rng):
    opts = [correcto] + [r for r in resto if r != correcto][:3]
    while len(opts) < 4:
        opts.append("(ninguna de las anteriores)")
    opts = opts[:4]
    rng.shuffle(opts)
    return OpcionMultiple(
        pregunta=pregunta, opciones=opts,
        correcta=opts.index(correcto),
        explicacion=explicacion,
        retroalimentacion=retro,
    )

def _rm(pregunta, correctas_vals, falsas_vals, explicacion, retro, rng):
    # limpiar valores raros antes de armar opciones
    correctas_vals = [v for v in correctas_vals
                      if v and len(v) > 1 and v not in ('(', ')', ',', '')]
    if len(correctas_vals) < 2:
        return None
    falsas_vals = [v for v in falsas_vals
                   if v and len(v) > 1 and v not in correctas_vals]
    opts = list(correctas_vals[:6]) + falsas_vals[:4]
    rng.shuffle(opts)
    idxs = sorted([opts.index(v) for v in correctas_vals if v in opts])
    if not idxs:
        return None
    return RespuestaMultiple(
        pregunta=pregunta, opciones=opts, correctas=idxs,
        explicacion=explicacion, retroalimentacion=retro,
    )

def _dedup(banco):
    vistos = set()
    out = []
    for p in banco:
        if p is None:
            continue
        key = (p.codigo_con_huecos if hasattr(p, 'codigo_con_huecos')
               else (p.pregunta if hasattr(p, 'pregunta') else p.instruccion))
        if key not in vistos:
            vistos.add(key)
            out.append(p)
    return out


# ── Analizadores ───────────────────────────────────────────────────────────────

def _analizar_clases(a: Archivo) -> list[dict]:
    resultado = []
    clase_actual = None
    for linea in a.codigo.splitlines():
        ls = linea.strip()
        if re.match(r'^class\s+\w+', ls):
            m = re.match(r'class\s+(\w+)', ls)
            if m:
                clase_actual = {"nombre": m.group(1), "metodos": [], "linea": ls}
                resultado.append(clase_actual)
        elif re.match(r'^\s+def\s+', linea) and clase_actual:
            m = re.match(r'def\s+(\w+)\s*\(([^)]*)\)', ls)
            if m:
                clase_actual["metodos"].append({
                    "nombre": m.group(1),
                    "params": m.group(2),
                    "linea":  ls,
                })
    return resultado

def _analizar_funciones_top(a: Archivo) -> list[dict]:
    resultado = []
    for linea in a.codigo.splitlines():
        if re.match(r'^def\s+', linea):
            m = re.match(r'def\s+(\w+)\s*\(([^)]*)\)', linea.strip())
            if m:
                resultado.append({
                    "nombre": m.group(1),
                    "params": m.group(2),
                    "linea":  linea.strip()
                })
    return resultado

def _analizar_imports_limpios(a: Archivo) -> list[dict]:
    """Extrae imports evitando capturar paréntesis o comas sueltas."""
    resultado = []
    codigo = a.codigo
    # Normalizar imports multilínea: juntar líneas con paréntesis abierto
    lineas_norm = []
    buffer = ""
    for l in codigo.splitlines():
        ls = l.strip()
        if buffer:
            buffer += " " + ls
            if ')' in ls:
                lineas_norm.append(buffer)
                buffer = ""
        elif ls.startswith('from ') and '(' in ls and ')' not in ls:
            buffer = ls
        else:
            lineas_norm.append(ls)

    for ls in lineas_norm:
        if ls.startswith('from '):
            m = re.match(r'from\s+(\S+)\s+import\s+\(?(.+?)\)?$', ls)
            if m:
                modulo = m.group(1)
                nombres_raw = m.group(2)
                nombres = [n.strip().strip('()').strip()
                           for n in nombres_raw.split(',')
                           if n.strip().strip('()').strip()
                           and len(n.strip().strip('()').strip()) > 1]
                if nombres:
                    resultado.append({
                        "tipo": "from",
                        "modulo": modulo,
                        "nombres": nombres,
                        "linea": ls
                    })
        elif ls.startswith('import '):
            mod = ls.replace('import ', '').strip()
            if mod and len(mod) > 1:
                resultado.append({
                    "tipo": "import",
                    "modulo": mod,
                    "nombres": [mod],
                    "linea": ls
                })
    return resultado

def _analizar_sql_tablas(a: Archivo) -> list[dict]:
    tablas = []
    bloques = re.split(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?', a.codigo, flags=re.I)
    for bloque in bloques[1:]:
        nombre_m = re.match(r'(\w+)\s*\(', bloque)
        if not nombre_m:
            continue
        nombre = nombre_m.group(1)
        interior = re.search(r'\((.+?)(?:\);|\)\s*;)', bloque, re.DOTALL)
        if not interior:
            continue
        cuerpo = interior.group(1)
        columnas = []
        for l in cuerpo.splitlines():
            ls = l.strip()
            if not ls or ls.startswith('--'):
                continue
            if any(ls.upper().startswith(kw) for kw in
                   ('FOREIGN', 'UNIQUE', 'PRIMARY KEY (', 'CHECK', 'CONSTRAINT')):
                continue
            m = re.match(r'(\w+)\s+(INTEGER|REAL|TEXT|DATE|TIME|BLOB|BOOLEAN)',
                         ls, re.I)
            if m:
                tipo = m.group(2).upper()
                resto = ls[m.end():].strip()
                not_null = 'NOT NULL' in resto.upper()
                default_m = re.search(r'DEFAULT\s+(\S+)', resto, re.I)
                columnas.append({
                    "col": m.group(1),
                    "tipo": tipo,
                    "not_null": not_null,
                    "default": default_m.group(1) if default_m else None
                })
        checks = re.findall(r'CHECK\s*\((.+?)\)', cuerpo, re.DOTALL)
        checks = [re.sub(r'\s+', ' ', c.strip()) for c in checks]
        fks = re.findall(
            r'FOREIGN KEY\s*\((\w+)\)\s*REFERENCES\s*(\w+)\s*\((\w+)\)',
            cuerpo, re.I)
        if columnas:
            tablas.append({
                "nombre": nombre,
                "columnas": columnas,
                "checks": checks,
                "fks": fks
            })
    return tablas

def _analizar_html(a: Archivo) -> dict:
    codigo = a.codigo
    # web.py usa $for, Flask/Jinja usa {% for %}
    loops_webpy  = re.findall(r'\$for\s+(\w+)\s+in\s+(\w+)', codigo)
    loops_jinja  = re.findall(r'\{%[-\s]*for\s+(\w+)\s+in\s+(\w+)', codigo)
    loops = list(dict.fromkeys(loops_webpy + loops_jinja))

    ifs_webpy  = [i.strip() for i in re.findall(r'\$if\s+(.+?):', codigo)]
    ifs_jinja  = [i.strip() for i in re.findall(r'\{%[-\s]*if\s+(.+?)[-\s]*%\}', codigo)]
    ifs = list(dict.fromkeys(ifs_webpy + ifs_jinja))

    inputs  = list(dict.fromkeys(
        re.findall(r'<input[^>]+name=["\']([^"\']+)["\']', codigo, re.I)))
    forms   = list(dict.fromkeys(
        re.findall(r'<form[^>]+action=["\']([^"\']+)["\']', codigo, re.I)))
    selects = list(dict.fromkeys(
        re.findall(r'<select[^>]+name=["\']([^"\']+)["\']', codigo, re.I)))
    textareas = list(dict.fromkeys(
        re.findall(r'<textarea[^>]+name=["\']([^"\']+)["\']', codigo, re.I)))

    defs_webpy = re.findall(r'\$def\s+with\s*\(([^)]+)\)', codigo)
    extends_j  = re.search(r'\{%[-\s]*extends\s+"([^"]+)"', codigo)

    return {
        "loops": loops,
        "ifs": ifs,
        "inputs": inputs,
        "forms": forms,
        "selects": selects,
        "textareas": textareas,
        "defs": defs_webpy,
        "extends": extends_j.group(1) if extends_j else None,
    }


# ── BANCO OPCIÓN MÚLTIPLE ──────────────────────────────────────────────────────

def _banco_om(r: ResultadoValidacion, rng: random.Random) -> list[OpcionMultiple]:
    banco = []
    py_files   = _py(r.archivos)
    sql_files  = _sql(r.archivos)
    html_files = _html(r.archivos)

    # ── Clases: firma del método ────────────────────────────────────────────
    for a in py_files:
        for cls in _analizar_clases(a):
            for met in cls["metodos"]:
                params = [p.strip() for p in met["params"].split(',')
                          if p.strip() and p.strip() != 'self']
                if params:
                    p0 = params[0]
                    banco.append(_om(
                        f"¿Qué parámetro recibe `{met['nombre']}` de `{cls['nombre']}` en `{_nombre(a)}`?",
                        p0,
                        ["request", "context", "payload", "pk", "token", "data"],
                        f"Firma: {met['linea']}",
                        f"Firma real en {_nombre(a)}:\n  {met['linea']}",
                        rng
                    ))
                banco.append(_om(
                    f"¿Cuál es la firma correcta del método `{met['nombre']}` en la clase `{cls['nombre']}`?",
                    met["linea"],
                    [f"def {met['nombre']}(self):",
                     f"def {met['nombre']}(self, request, *args):",
                     f"def {met['nombre']}(context=None):"],
                    f"Firma: {met['linea']}",
                    f"La firma real de `{met['nombre']}` en {_nombre(a)} es:\n  {met['linea']}",
                    rng
                ))

    # ── Funciones top-level: firma y return ─────────────────────────────────
    for a in py_files:
        for func in _analizar_funciones_top(a):
            banco.append(_om(
                f"¿Cuál es la firma de la función `{func['nombre']}` en `{_nombre(a)}`?",
                func["linea"],
                [f"def {func['nombre']}(request, pk=None):",
                 f"def {func['nombre']}(*args, **kwargs):",
                 f"def {func['nombre']}(self, context):"],
                f"Firma: {func['linea']}",
                f"La firma real en {_nombre(a)} es:\n  {func['linea']}",
                rng
            ))
            # qué retorna
            retornos = []
            en_func = False
            for l in a.codigo.splitlines():
                ls = l.strip()
                if f"def {func['nombre']}" in ls:
                    en_func = True
                if en_func and ls.startswith('return ') and len(ls) < 80:
                    retornos.append(ls)
                if en_func and ls.startswith('def ') and func['nombre'] not in ls:
                    break
            if retornos:
                ret = retornos[0]
                banco.append(_om(
                    f"¿Qué retorna `{func['nombre']}` en `{_nombre(a)}`?",
                    ret,
                    ["return None", "return True", "return {}", "return []"],
                    f"Return: {ret}",
                    f"Busca `def {func['nombre']}` en {_nombre(a)}.\nEl return es:\n  {ret}",
                    rng
                ))

    # ── Imports: qué se importa de qué módulo ──────────────────────────────
    for a in py_files:
        for imp in _analizar_imports_limpios(a):
            if imp["tipo"] == "from" and len(imp["nombres"]) >= 1:
                nombre = rng.choice(imp["nombres"])
                banco.append(_om(
                    f"¿Cuál nombre se importa desde `{imp['modulo']}` en `{_nombre(a)}`?",
                    nombre,
                    ["HttpResponse", "validate_email", "get_object_or_404",
                     "send_mail", "JsonResponse", "login_required"],
                    f"Línea: {imp['linea']}",
                    f"Import real en {_nombre(a)}:\n  {imp['linea']}",
                    rng
                ))

    # ── SQL: tipo de columna ────────────────────────────────────────────────
    for a in sql_files:
        for tabla in _analizar_sql_tablas(a):
            for col in rng.sample(tabla["columnas"], min(4, len(tabla["columnas"]))):
                banco.append(_om(
                    f"¿Qué tipo de dato tiene `{col['col']}` en la tabla `{tabla['nombre']}`?",
                    col["tipo"],
                    [t for t in ["INTEGER","REAL","TEXT","DATE","TIME","BOOLEAN"]
                     if t != col["tipo"]][:3],
                    f"`{col['col']}` es {col['tipo']} en `{tabla['nombre']}`.",
                    f"En `{tabla['nombre']}` de script.sql:\n  {col['col']} {col['tipo']}{'  NOT NULL' if col['not_null'] else ''}",
                    rng
                ))
            # DEFAULT
            for col in [c for c in tabla["columnas"] if c["default"]]:
                banco.append(_om(
                    f"¿Cuál es el DEFAULT de `{col['col']}` en `{tabla['nombre']}`?",
                    col["default"],
                    ["NULL", "''", "CURRENT_TIMESTAMP", "1", "-1"],
                    f"DEFAULT de `{col['col']}` es {col['default']}.",
                    f"En `{tabla['nombre']}`:\n  {col['col']} ... DEFAULT {col['default']}",
                    rng
                ))
            # CHECK: valor numérico
            for chk in rng.sample(tabla["checks"], min(3, len(tabla["checks"]))):
                nums = re.findall(r"'[^']+?'|\d+\.?\d*", chk)
                if nums:
                    val = nums[0]
                    banco.append(_om(
                        f"¿Cuál valor aparece en el CHECK `{chk[:55]}...` de `{tabla['nombre']}`?",
                        val,
                        [str(int(float(val.strip("'"))) + 1) if val.strip("'").replace('.','').isdigit()
                         else "'otro'", "'N/A'", "100", "0"],
                        f"CHECK({chk})",
                        f"En `{tabla['nombre']}`:\n  CHECK({chk})",
                        rng
                    ))
            # FK
            for col_fk, tabla_ref, col_ref in tabla["fks"]:
                banco.append(_om(
                    f"¿A qué tabla referencia la FK `{col_fk}` en `{tabla['nombre']}`?",
                    tabla_ref,
                    [t["nombre"] for t in _analizar_sql_tablas(a)
                     if t["nombre"] != tabla_ref][:3] or
                    ["categorias", "perfiles", "logs"],
                    f"FOREIGN KEY({col_fk}) REFERENCES {tabla_ref}({col_ref})",
                    f"En `{tabla['nombre']}`:\n  FOREIGN KEY({col_fk}) REFERENCES {tabla_ref}({col_ref})",
                    rng
                ))

    # ── HTML: loops, forms, inputs ──────────────────────────────────────────
    for a in html_files:
        info = _analizar_html(a)
        for var, col in rng.sample(info["loops"], min(3, len(info["loops"]))):
            banco.append(_om(
                f"¿Sobre qué colección itera `{var}` en el template `{_nombre(a)}`?",
                col,
                ["items", "datos", "resultados", "registros", "lista"],
                f"for {var} in {col}",
                f"En `{_nombre(a)}`:\n  $for {var} in {col}",
                rng
            ))
        for action in info["forms"][:2]:
            banco.append(_om(
                f"¿A qué URL apunta el form en `{_nombre(a)}`?",
                action,
                ["/admin/save", "/api/submit", "/datos/guardar", "/process"],
                f"<form action=\"{action}\">",
                f"En `{_nombre(a)}`:\n  <form action=\"{action}\">",
                rng
            ))
        all_campos = info["inputs"] + info["selects"] + info["textareas"]
        if len(all_campos) >= 2:
            campo = rng.choice(all_campos)
            banco.append(_om(
                f"¿Cuál campo `name` existe en el formulario de `{_nombre(a)}`?",
                campo,
                ["correo", "token", "clave", "descripcion", "precio", "cantidad"],
                f"name=\"{campo}\" en {_nombre(a)}",
                f"El template `{_nombre(a)}` tiene:\n  name=\"{campo}\"",
                rng
            ))

    return _dedup(banco)


# ── BANCO RESPUESTA MÚLTIPLE ──────────────────────────────────────────────────

def _banco_rm(r: ResultadoValidacion, rng: random.Random) -> list[RespuestaMultiple]:
    banco = []
    py_files   = _py(r.archivos)
    sql_files  = _sql(r.archivos)
    html_files = _html(r.archivos)

    # ── Código Python: qué importa cada archivo ─────────────────────────────
    for a in py_files:
        imports = _analizar_imports_limpios(a)
        todos = []
        for imp in imports:
            todos.extend(imp["nombres"])
        todos = list(dict.fromkeys([n for n in todos if n and len(n) > 2]))
        if len(todos) >= 3:
            muestra = todos[:6]
            p = _rm(
                f"¿Cuáles de estos nombres son importados en `{_nombre(a)}`?",
                muestra[:4],
                ["HttpResponse", "validate_email", "send_mail", "JsonResponse",
                 "login_required", "get_or_create", "paginate"],
                f"Nombres importados en {_nombre(a)}: {', '.join(todos)}",
                f"Los nombres importados en {_nombre(a)}:\n" +
                "\n".join(f"  {n}" for n in muestra),
                rng
            )
            if p: banco.append(p)

    # ── Código Python: funciones definidas en cada archivo ──────────────────
    for a in py_files:
        # top-level
        funcs_top = [f["nombre"] for f in _analizar_funciones_top(a)]
        # dentro de clases
        funcs_cls = []
        for cls in _analizar_clases(a):
            funcs_cls.extend([m["nombre"] for m in cls["metodos"]])
        todas = list(dict.fromkeys(funcs_top + funcs_cls))
        if len(todas) >= 2:
            p = _rm(
                f"¿Cuáles funciones/métodos están definidos en `{_nombre(a)}`?",
                todas[:5],
                ["procesar_pago", "enviar_factura", "calcular_impuesto",
                 "validar_stock", "generar_reporte", "sincronizar"],
                f"Funciones en {_nombre(a)}: {', '.join(todas)}",
                f"Las funciones/métodos en {_nombre(a)}:\n" +
                "\n".join(f"  def {f}(...)" for f in todas[:5]),
                rng
            )
            if p: banco.append(p)

    # ── Código Python: líneas return con render/redirect ────────────────────
    for a in py_files:
        returns = list(dict.fromkeys([
            l.strip() for l in _novacias(a.codigo)
            if l.strip().startswith('return ')
            and any(kw in l for kw in
                    ['render','redirect','redirigir','web.found',
                     'web.notfound','web.ctx','jsonify'])
            and len(l.strip()) < 90
        ]))
        if len(returns) >= 2:
            muestra = returns[:4]
            p = _rm(
                f"¿Cuáles instrucciones `return` con render/redirect existen en `{_nombre(a)}`?",
                muestra,
                ["return render_template('admin.html')",
                 "return redirect('/login')",
                 "return jsonify({'ok': False})",
                 "return HttpResponse(404)"],
                f"Returns en {_nombre(a)}: {'; '.join(muestra)}",
                f"Los returns reales en {_nombre(a)}:\n" +
                "\n".join(f"  {ret}" for ret in muestra),
                rng
            )
            if p: banco.append(p)

    # ── Código Python: clases definidas en cada archivo ─────────────────────
    for a in py_files:
        clases = _analizar_clases(a)
        nombres_cls = [c["nombre"] for c in clases]
        if len(nombres_cls) >= 2:
            p = _rm(
                f"¿Cuáles clases están definidas en `{_nombre(a)}`?",
                nombres_cls,
                ["AdminView", "LoginController", "BaseModel",
                 "PaymentProcessor", "UserSerializer"],
                f"Clases en {_nombre(a)}: {', '.join(nombres_cls)}",
                f"Las clases en {_nombre(a)}:\n" +
                "\n".join(f"  class {c}" for c in nombres_cls),
                rng
            )
            if p: banco.append(p)

    # ── SQL: columnas de cada tabla ─────────────────────────────────────────
    for a in sql_files:
        for tabla in _analizar_sql_tablas(a):
            cols = [c["col"] for c in tabla["columnas"]]
            if len(cols) >= 3:
                muestra = cols[:6]
                p = _rm(
                    f"¿Cuáles columnas pertenecen a la tabla `{tabla['nombre']}`?",
                    muestra,
                    ["precio_total", "codigo_barras", "nombre_comercial",
                     "stock_minimo", "descuento", "referencia"],
                    f"Columnas de {tabla['nombre']}: {', '.join(cols)}",
                    f"La tabla `{tabla['nombre']}` tiene:\n" +
                    "\n".join(f"  {c}" for c in muestra),
                    rng
                )
                if p: banco.append(p)

            # NOT NULL
            nn = [c["col"] for c in tabla["columnas"] if c["not_null"]]
            nullable = [c["col"] for c in tabla["columnas"] if not c["not_null"]]
            if len(nn) >= 2:
                p = _rm(
                    f"¿Cuáles columnas de `{tabla['nombre']}` son NOT NULL?",
                    nn[:5],
                    nullable[:4] or ["descripcion", "notas", "observaciones"],
                    f"NOT NULL en {tabla['nombre']}: {', '.join(nn)}",
                    f"En `{tabla['nombre']}`, las columnas NOT NULL son:\n" +
                    "\n".join(f"  {c}" for c in nn),
                    rng
                )
                if p: banco.append(p)

            # FKs
            if len(tabla["fks"]) >= 2:
                cols_fk = [col for col, _, _ in tabla["fks"]]
                p = _rm(
                    f"¿Cuáles columnas de `{tabla['nombre']}` son FOREIGN KEY?",
                    cols_fk,
                    [c["col"] for c in tabla["columnas"]
                     if c["col"] not in cols_fk][:4] or
                    ["precio", "nombre", "descripcion"],
                    f"FKs de {tabla['nombre']}: {', '.join(cols_fk)}",
                    f"En `{tabla['nombre']}`, las FOREIGN KEY son:\n" +
                    "\n".join(f"  {c}" for c in cols_fk),
                    rng
                )
                if p: banco.append(p)

    # ── HTML: campos del formulario ─────────────────────────────────────────
    for a in html_files:
        info = _analizar_html(a)
        all_campos = list(dict.fromkeys(
            info["inputs"] + info["selects"] + info["textareas"]))
        if len(all_campos) >= 3:
            p = _rm(
                f"¿Cuáles campos `name` tiene el formulario en `{_nombre(a)}`?",
                all_campos[:5],
                ["correo", "usuario", "token", "clave",
                 "descripcion", "precio", "cantidad"],
                f"Campos en {_nombre(a)}: {', '.join(all_campos)}",
                f"Los campos name en `{_nombre(a)}`:\n" +
                "\n".join(f"  name=\"{c}\"" for c in all_campos[:5]),
                rng
            )
            if p: banco.append(p)

        # Condiciones $if
        ifs_limpios = [i for i in info["ifs"] if len(i) > 3 and len(i) < 60]
        if len(ifs_limpios) >= 2:
            p = _rm(
                f"¿Cuáles condiciones `if` aparecen en `{_nombre(a)}`?",
                ifs_limpios[:4],
                ["usuario is None", "precio > 0", "stock == 0",
                 "activo == False", "token is not None"],
                f"Condiciones if en {_nombre(a)}: {'; '.join(ifs_limpios[:4])}",
                f"Las condiciones if en `{_nombre(a)}`:\n" +
                "\n".join(f"  if {i}:" for i in ifs_limpios[:4]),
                rng
            )
            if p: banco.append(p)

    return [p for p in _dedup(banco) if p is not None]


# ── BANCO COMPLETAR CÓDIGO (10 bloques con 3-4 huecos) ────────────────────────

def _bloque_con_huecos(lineas: list[str], targets: list[str],
                       n: int = 3) -> tuple[str, list[str]] | None:
    """
    Sustituye n palabras clave de un bloque real por _____.
    - targets ordenados de mayor a menor longitud (evita partir palabras)
    - word boundary para palabras alfabéticas
    - máximo 1 hueco por línea
    """
    targets_ord = sorted(targets, key=len, reverse=True)
    respuestas = []
    lineas_mod = list(lineas)
    hechos = 0

    for i, linea in enumerate(lineas_mod):
        if hechos >= n:
            break
        if "_____" in linea:
            continue
        for t in targets_ord:
            if t.replace('_', '').isalpha():
                pat = re.compile(r'\b' + re.escape(t) + r'\b')
            else:
                pat = re.compile(re.escape(t))
            nueva = pat.sub("_____", linea, count=1)
            if nueva != linea:
                lineas_mod[i] = nueva
                respuestas.append(t)
                hechos += 1
                break

    if hechos < 2:
        return None
    return "\n".join(lineas_mod), respuestas


def _banco_cc(r: ResultadoValidacion, rng: random.Random) -> list[CompletarCodigo]:
    banco = []
    py_files   = _py(r.archivos)
    sql_files  = _sql(r.archivos)
    html_files = _html(r.archivos)
    vistos: set[str] = set()

    PY_T = sorted([
        "web", "render", "return", "def", "class", "import", "from",
        "None", "True", "False", "self", "raise", "try", "except", "with",
        "GET", "POST", "cursor", "fetchone", "fetchall", "execute", "commit",
        "session", "request", "flash", "redirect", "url_for",
        "render_template", "Blueprint", "psycopg2", "RealDictCursor",
        "get_conexion", "wraps", "datetime", "timedelta", "uuid",
        "obtener_usuario_actual", "redirigir", "web.input", "web.template",
        "NOT NULL", "DEFAULT", "PRIMARY KEY", "FOREIGN KEY",
    ], key=len, reverse=True)

    SQL_T = sorted([
        "INTEGER", "REAL", "TEXT", "DATE", "TIME",
        "NOT NULL", "DEFAULT", "PRIMARY KEY", "AUTOINCREMENT",
        "FOREIGN KEY", "REFERENCES", "CHECK", "UNIQUE",
        "CREATE TABLE", "DROP TABLE", "CREATE INDEX",
        "IF NOT EXISTS", "GENERATED ALWAYS AS IDENTITY",
    ], key=len, reverse=True)

    HTML_T = sorted([
        "action", "method", "name", "type", "value",
        "POST", "GET", "required", "class", "id",
        "for", "in", "if", "else",
    ], key=len, reverse=True)

    # ── Python: bloques de funciones ────────────────────────────────────────
    for a in py_files:
        lineas_a = a.codigo.splitlines()
        indices = [i for i, l in enumerate(lineas_a) if re.match(r'\s*def\s+', l)]
        rng.shuffle(indices)
        for idx in indices:
            if len(banco) >= 15: break
            bloque = [l for l in lineas_a[idx:idx+9] if l.strip()][:8]
            if len(bloque) < 4: continue
            clave = "\n".join(bloque)
            if clave in vistos: continue
            res = _bloque_con_huecos(bloque, PY_T, rng.randint(3, 4))
            if not res: continue
            hueco, resps = res
            vistos.add(clave)
            fn = re.search(r'def\s+(\w+)', lineas_a[idx])
            nombre_fn = fn.group(1) if fn else "función"
            banco.append(CompletarCodigo(
                instruccion=f"Completa el bloque de `{nombre_fn}` en `{_nombre(a)}` ({len(resps)} huecos):",
                codigo_con_huecos=hueco,
                respuestas=resps,
                explicacion=f"Bloque original:\n{clave}",
                retroalimentacion=f"El código original de `{nombre_fn}` en {_nombre(a)}:\n{clave}",
            ))

    # ── Python: bloques de class ─────────────────────────────────────────────
    for a in py_files:
        lineas_a = a.codigo.splitlines()
        indices = [i for i, l in enumerate(lineas_a) if re.match(r'\s*class\s+', l)]
        rng.shuffle(indices)
        for idx in indices:
            if len(banco) >= 20: break
            bloque = [l for l in lineas_a[idx:idx+7] if l.strip()][:6]
            if len(bloque) < 3: continue
            clave = "\n".join(bloque)
            if clave in vistos: continue
            res = _bloque_con_huecos(bloque, PY_T, 3)
            if not res: continue
            hueco, resps = res
            vistos.add(clave)
            cn = re.search(r'class\s+(\w+)', lineas_a[idx])
            nombre_cls = cn.group(1) if cn else "clase"
            banco.append(CompletarCodigo(
                instruccion=f"Completa la clase `{nombre_cls}` en `{_nombre(a)}` ({len(resps)} huecos):",
                codigo_con_huecos=hueco,
                respuestas=resps,
                explicacion=f"Código original:\n{clave}",
                retroalimentacion=f"La clase `{nombre_cls}` en {_nombre(a)}:\n{clave}",
            ))

    # ── SQL: bloques de CREATE TABLE ─────────────────────────────────────────
    for a in sql_files:
        partes = re.split(r'(CREATE TABLE\b)', a.codigo, flags=re.I)
        i = 0
        while i < len(partes) - 1:
            if re.match(r'CREATE TABLE', partes[i], re.I):
                bloque_raw = partes[i] + (partes[i+1] if i+1 < len(partes) else "")
                lineas = [l for l in bloque_raw.splitlines()
                          if l.strip() and not l.strip().startswith('--')][:12]
                if len(lineas) >= 5:
                    clave = "\n".join(lineas)
                    if clave not in vistos:
                        res = _bloque_con_huecos(lineas, SQL_T, rng.randint(3, 4))
                        if res:
                            hueco, resps = res
                            vistos.add(clave)
                            nt = re.search(r'(\w+)\s*\(', bloque_raw)
                            nombre_t = nt.group(1) if nt else "tabla"
                            banco.append(CompletarCodigo(
                                instruccion=f"Completa el bloque SQL de `{nombre_t}` ({len(resps)} huecos):",
                                codigo_con_huecos=hueco,
                                respuestas=resps,
                                explicacion=f"SQL original:\n{clave}",
                                retroalimentacion=f"El SQL original de `{nombre_t}`:\n{clave}",
                            ))
            i += 1

    # ── HTML: bloques de form ────────────────────────────────────────────────
    for a in html_files:
        lineas_h = a.codigo.splitlines()
        for i, l in enumerate(lineas_h):
            if len(banco) >= 35: break
            if '<form' in l.lower():
                bloque = [x for x in lineas_h[i:i+10] if x.strip()][:10]
                if len(bloque) < 4: continue
                clave = "\n".join(bloque)
                if clave in vistos: continue
                res = _bloque_con_huecos(bloque, HTML_T, rng.randint(3, 4))
                if not res: continue
                hueco, resps = res
                vistos.add(clave)
                banco.append(CompletarCodigo(
                    instruccion=f"Completa el form en `{_nombre(a)}` ({len(resps)} huecos):",
                    codigo_con_huecos=hueco,
                    respuestas=resps,
                    explicacion=f"Form original:\n{clave}",
                    retroalimentacion=f"El form original en {_nombre(a)}:\n{clave}",
                ))

    return _dedup(banco)


# ── Generadores ────────────────────────────────────────────────────────────────

def gen_opcion_multiple(r, n=25, seed=42):
    rng = random.Random(seed)
    banco = _banco_om(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_respuesta_multiple(r, n=25, seed=42):
    rng = random.Random(seed)
    banco = _banco_rm(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_completar_codigo(r, n=10, seed=42):
    rng = random.Random(seed)
    banco = _banco_cc(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_combinado(r, n=30, seed=42):
    rng = random.Random(seed)
    om = gen_opcion_multiple(r, 10, seed)
    rm = gen_respuesta_multiple(r, 10, seed)
    cc = gen_completar_codigo(r, 10, seed)
    mezclado = om + rm + cc
    rng.shuffle(mezclado)
    return mezclado[:n]


TITULOS = {
    "opcion_multiple":    ("Examen de opción múltiple",    "Selecciona la única respuesta correcta."),
    "respuesta_multiple": ("Examen de respuesta múltiple", "Puede haber más de una respuesta correcta."),
    "completar_codigo":   ("Examen de completar código",   "Escribe las palabras que van en cada hueco (_____) en orden."),
    "combinado":          ("Examen combinado",              "Mezcla de los 3 tipos de preguntas."),
}

def generar_examen(r: ResultadoValidacion, tipo: str, seed: int = 42) -> Examen:
    titulo, desc = TITULOS.get(tipo, ("Examen", ""))
    gens = {
        "opcion_multiple":    lambda: gen_opcion_multiple(r, 25, seed),
        "respuesta_multiple": lambda: gen_respuesta_multiple(r, 25, seed),
        "completar_codigo":   lambda: gen_completar_codigo(r, 10, seed),
        "combinado":          lambda: gen_combinado(r, 30, seed),
    }
    return Examen(titulo=titulo, descripcion=desc, tipo=tipo,
                  duracion_minutos=40, preguntas=gens[tipo]())