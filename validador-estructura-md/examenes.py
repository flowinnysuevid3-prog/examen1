"""
examenes.py — Exámenes profundos de código real.

Estrategia:
  - Analiza el código real del .md línea por línea
  - Genera preguntas sobre lógica, estructura, valores, parámetros
  - Completar código: bloques REALES con 3-4 huecos cada uno
  - Toda respuesta incorrecta tiene retroalimentación con el extracto original
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
    codigo_con_huecos: str = ""    # bloque completo con varios _____
    respuestas: list[str] = field(default_factory=list)   # en orden de aparición
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

def _py(archivos):   return [a for a in archivos if _limpia(a.titulo).endswith('.py')]
def _sql(archivos):  return [a for a in archivos if _limpia(a.titulo).endswith('.sql') or a.lenguaje.lower() == 'sql']
def _html(archivos): return [a for a in archivos if _limpia(a.titulo).endswith('.html')]
def _novacias(codigo): return [l for l in codigo.splitlines() if l.strip()]

def _nombre(a: Archivo) -> str:
    """Nombre limpio del archivo para mostrar en preguntas."""
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

def _rm(pregunta, correctas, falsas, explicacion, retro, rng):
    opts = list(correctas) + [f for f in falsas if f not in correctas]
    rng.shuffle(opts)
    idxs = sorted([opts.index(v) for v in correctas if v in opts])
    return RespuestaMultiple(
        pregunta=pregunta, opciones=opts, correctas=idxs,
        explicacion=explicacion, retroalimentacion=retro,
    )

def _dedup(banco):
    vistos = set()
    out = []
    for p in banco:
        key = p.codigo_con_huecos if hasattr(p,'codigo_con_huecos') else (p.pregunta if hasattr(p,'pregunta') else p.instruccion)
        if key not in vistos:
            vistos.add(key)
            out.append(p)
    return out

def _extracto(codigo: str, linea_buscada: str, contexto: int = 3) -> str:
    """Devuelve el extracto del código alrededor de la línea buscada."""
    lineas = codigo.splitlines()
    for i, l in enumerate(lineas):
        if linea_buscada.strip() in l:
            inicio = max(0, i - contexto)
            fin    = min(len(lineas), i + contexto + 1)
            return "\n".join(lineas[inicio:fin])
    return linea_buscada


# ── ANALIZADORES DE CÓDIGO ─────────────────────────────────────────────────────

def _analizar_clases(a: Archivo) -> list[dict]:
    """Extrae clases con sus métodos y parámetros."""
    resultado = []
    clase_actual = None
    for linea in a.codigo.splitlines():
        ls = linea.strip()
        if ls.startswith('class '):
            nombre = re.match(r'class\s+(\w+)', ls)
            if nombre:
                clase_actual = {"nombre": nombre.group(1), "metodos": [], "linea": ls}
                resultado.append(clase_actual)
        elif ls.startswith('def ') and clase_actual:
            m = re.match(r'def\s+(\w+)\s*\(([^)]*)\)', ls)
            if m:
                clase_actual["metodos"].append({
                    "nombre": m.group(1),
                    "params": m.group(2),
                    "linea":  ls,
                })
    return resultado

def _analizar_funciones_top(a: Archivo) -> list[dict]:
    """Funciones de nivel módulo (no dentro de clase)."""
    resultado = []
    en_clase = False
    for linea in a.codigo.splitlines():
        ls = linea.strip()
        if ls.startswith('class '): en_clase = True
        if re.match(r'^def\s+', linea) and not en_clase:  # sin indentación = top level
            m = re.match(r'def\s+(\w+)\s*\(([^)]*)\)', ls)
            if m:
                resultado.append({"nombre": m.group(1), "params": m.group(2), "linea": ls})
    return resultado

def _analizar_imports(a: Archivo) -> list[dict]:
    """Imports con módulo y nombre importado."""
    resultado = []
    for linea in _novacias(a.codigo):
        ls = linea.strip()
        if ls.startswith('from '):
            m = re.match(r'from\s+(\S+)\s+import\s+(.+)', ls)
            if m:
                resultado.append({"tipo": "from", "modulo": m.group(1),
                                   "nombres": [x.strip() for x in m.group(2).split(',')],
                                   "linea": ls})
        elif ls.startswith('import '):
            resultado.append({"tipo": "import", "modulo": ls.replace('import ','').strip(),
                               "nombres": [], "linea": ls})
    return resultado

def _analizar_sql_tablas(a: Archivo) -> list[dict]:
    """Extrae tablas con columnas, tipos, constraints."""
    tablas = []
    bloques = re.split(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?', a.codigo, flags=re.I)
    for bloque in bloques[1:]:
        nombre_m = re.match(r'(\w+)\s*\(', bloque)
        if not nombre_m: continue
        nombre = nombre_m.group(1)
        interior = re.search(r'\((.+?)(?:\);|\)\s*;)', bloque, re.DOTALL)
        if not interior: continue
        cuerpo = interior.group(1)
        columnas = []
        for l in cuerpo.splitlines():
            ls = l.strip()
            if not ls or ls.startswith('--') or ls.startswith('FOREIGN') or ls.startswith('UNIQUE') or ls.startswith('PRIMARY KEY ('): continue
            m = re.match(r'(\w+)\s+(INTEGER|REAL|TEXT|DATE|TIME|BLOB|BOOLEAN)(\s+.+)?', ls, re.I)
            if m:
                tipo = m.group(2).upper()
                resto = (m.group(3) or '').strip()
                notnull = 'NOT NULL' in resto.upper()
                default = re.search(r'DEFAULT\s+(\S+)', resto, re.I)
                columnas.append({"col": m.group(1), "tipo": tipo,
                                  "not_null": notnull,
                                  "default": default.group(1) if default else None})
        checks = re.findall(r'CHECK\((.+?)\)', cuerpo, re.DOTALL)
        checks = [re.sub(r'\s+', ' ', c.strip()) for c in checks]
        fks = re.findall(r'FOREIGN KEY\s*\((\w+)\)\s*REFERENCES\s*(\w+)\s*\((\w+)\)', cuerpo, re.I)
        tablas.append({"nombre": nombre, "columnas": columnas,
                       "checks": checks, "fks": fks})
    return tablas

def _analizar_html(a: Archivo) -> dict:
    """Extrae info relevante de templates."""
    codigo = a.codigo
    extends = re.search(r'\$extends\s+"([^"]+)"|\{\%\s*extends\s+"([^"]+)"', codigo)
    defs    = list(dict.fromkeys(re.findall(r'\$def\s+with\s*\(([^)]+)\)', codigo)))
    loops   = list(dict.fromkeys(re.findall(r'\$for\s+(\w+)\s+in\s+(\w+)', codigo)))
    ifs     = list(dict.fromkeys(re.findall(r'\$if\s+(.+?):', codigo)))
    inputs  = list(dict.fromkeys(re.findall(r'<input[^>]+name=["\']([^"\']+)["\']', codigo, re.I)))
    forms   = list(dict.fromkeys(re.findall(r'<form[^>]+action=["\']([^"\']+)["\']', codigo, re.I)))
    return {
        "extends": (extends.group(1) or extends.group(2)) if extends else None,
        "defs": defs, "loops": loops, "ifs": ifs,
        "inputs": inputs, "forms": forms,
    }


# ── BANCO OPCIÓN MÚLTIPLE ──────────────────────────────────────────────────────

def _banco_om(r: ResultadoValidacion, rng: random.Random) -> list[OpcionMultiple]:
    banco = []
    py_files   = _py(r.archivos)
    sql_files  = _sql(r.archivos)
    html_files = _html(r.archivos)

    # ── Clases: qué métodos tiene, qué parámetros recibe ───────────────────
    for a in py_files:
        clases = _analizar_clases(a)
        for cls in clases:
            nombre_cls = cls["nombre"]
            metodos = cls["metodos"]

            # Qué métodos existen en la clase
            if len(metodos) >= 2:
                nombres_m = [m["nombre"] for m in metodos]
                banco.append(_om(
                    f"¿Cuáles métodos define la clase `{nombre_cls}` en `{_nombre(a)}`?",
                    nombres_m[0],
                    ["conectar", "validar", "serializar", "autenticar",
                     "calcular", "exportar", "sincronizar"],
                    f"La clase {nombre_cls} define: {', '.join(nombres_m)}",
                    f"Busca `class {nombre_cls}` en {_nombre(a)}.\nMétodos reales: {', '.join(nombres_m)}",
                    rng
                ))

            # Parámetros de cada método
            for met in metodos:
                if ',' in met["params"]:  # tiene más de un param
                    params = [p.strip() for p in met["params"].split(',') if p.strip() not in ('self','')]
                    if params:
                        p_correcto = params[0]
                        banco.append(_om(
                            f"¿Qué parámetro recibe el método `{met['nombre']}` de `{nombre_cls}` en `{_nombre(a)}`?",
                            p_correcto,
                            ["request", "context", "payload", "config", "response",
                             "session", "token", "callback"],
                            f"Firma: {met['linea']}",
                            f"Firma completa en {_nombre(a)}:\n{met['linea']}",
                            rng
                        ))

    # ── Imports: qué se importa de qué módulo ──────────────────────────────
    for a in py_files:
        imports = _analizar_imports(a)
        from_imports = [i for i in imports if i["tipo"] == "from" and len(i["nombres"]) >= 2]
        for imp in rng.sample(from_imports, min(3, len(from_imports))):
            nombre_correcto = rng.choice(imp["nombres"])
            banco.append(_om(
                f"¿Cuál función/clase se importa desde `{imp['modulo']}` en `{_nombre(a)}`?",
                nombre_correcto,
                ["HttpResponse", "render_to_string", "validate_email",
                 "get_object_or_404", "login_required", "JsonResponse"],
                f"Línea: {imp['linea']}",
                f"Import real en {_nombre(a)}:\n{imp['linea']}",
                rng
            ))

    # ── Funciones top-level: nombre, parámetros, qué retorna ───────────────
    for a in py_files:
        funcs = _analizar_funciones_top(a)
        for func in rng.sample(funcs, min(4, len(funcs))):
            # Buscar qué retorna
            codigo_lineas = a.codigo.splitlines()
            retornos = []
            en_func = False
            for l in codigo_lineas:
                ls = l.strip()
                if f"def {func['nombre']}" in ls: en_func = True
                if en_func and ls.startswith('return ') and len(ls) < 80:
                    retornos.append(ls)
                if en_func and ls.startswith('def ') and func['nombre'] not in ls:
                    break
            if retornos:
                ret = retornos[0]
                banco.append(_om(
                    f"¿Qué retorna la función `{func['nombre']}` en `{_nombre(a)}`?",
                    ret,
                    ['return None', 'return True', 'return {}', 'return []'],
                    f"La función `{func['nombre']}` retorna: {ret}",
                    f"Busca `def {func['nombre']}` en {_nombre(a)}. La instrucción return es:\n{ret}",
                    rng
                ))

            banco.append(_om(
                f"¿Cuál es la firma correcta de la función `{func['nombre']}` en `{_nombre(a)}`?",
                func["linea"],
                [f"def {func['nombre']}(request, pk):",
                 f"def {func['nombre']}(self, context=None):",
                 f"def {func['nombre']}(*args, **kwargs):"],
                f"Firma: {func['linea']}",
                f"La firma real en {_nombre(a)} es:\n{func['linea']}",
                rng
            ))

    # ── SQL: lógica de constraints ─────────────────────────────────────────
    for a in sql_files:
        tablas = _analizar_sql_tablas(a)
        for tabla in tablas:

            # Tipo de dato de columna
            for col in rng.sample(tabla["columnas"], min(4, len(tabla["columnas"]))):
                banco.append(_om(
                    f"¿Qué tipo de dato tiene la columna `{col['col']}` en la tabla `{tabla['nombre']}`?",
                    col["tipo"],
                    [t for t in ["INTEGER","REAL","TEXT","DATE","TIME","BOOLEAN"] if t != col["tipo"]][:3],
                    f"Columna `{col['col']}` es {col['tipo']} en `{tabla['nombre']}`.",
                    f"En la tabla `{tabla['nombre']}` de script.sql:\n  {col['col']} {col['tipo']}{'  NOT NULL' if col['not_null'] else ''}",
                    rng
                ))

            # DEFAULT values
            cols_con_default = [c for c in tabla["columnas"] if c["default"]]
            for col in rng.sample(cols_con_default, min(2, len(cols_con_default))):
                banco.append(_om(
                    f"¿Cuál es el valor DEFAULT de `{col['col']}` en la tabla `{tabla['nombre']}`?",
                    col["default"],
                    ["NULL", "0", "1", "'N/A'", "CURRENT_TIMESTAMP", "''"],
                    f"DEFAULT de `{col['col']}` es {col['default']}.",
                    f"En la tabla `{tabla['nombre']}`:\n  {col['col']} ... DEFAULT {col['default']}",
                    rng
                ))

            # CHECK constraints — valor concreto
            for chk in rng.sample(tabla["checks"], min(3, len(tabla["checks"]))):
                # Extraer el valor del check para preguntar
                nums = re.findall(r'\d+\.?\d*', chk)
                if nums:
                    num = nums[0]
                    banco.append(_om(
                        f"¿Cuál es el valor numérico en el CHECK constraint `{chk[:50]}` de la tabla `{tabla['nombre']}`?",
                        num,
                        [str(int(num)+1), str(int(float(num))*2), str(max(0,int(float(num))-1)), "100"],
                        f"El CHECK es: CHECK({chk})",
                        f"En la tabla `{tabla['nombre']}`:\n  CHECK({chk})",
                        rng
                    ))

            # FOREIGN KEY: a qué tabla referencia
            for col_fk, tabla_ref, col_ref in rng.sample(tabla["fks"], min(3, len(tabla["fks"]))):
                banco.append(_om(
                    f"¿A qué tabla hace referencia la FK `{col_fk}` en `{tabla['nombre']}`?",
                    tabla_ref,
                    [t["nombre"] for t in tablas if t["nombre"] != tabla_ref][:3] or
                    ["usuarios","categorias","perfiles"],
                    f"FOREIGN KEY({col_fk}) REFERENCES {tabla_ref}({col_ref})",
                    f"En `{tabla['nombre']}`:\n  FOREIGN KEY({col_fk}) REFERENCES {tabla_ref}({col_ref})",
                    rng
                ))

    # ── HTML: estructura de templates ──────────────────────────────────────
    for a in html_files:
        info = _analizar_html(a)

        # Qué variables recibe el template ($def with)
        for defn in info["defs"][:3]:
            params = [p.strip() for p in defn.split(',')]
            if params:
                banco.append(_om(
                    f"¿Qué variables recibe el template `{_nombre(a)}` (definición $def with)?",
                    params[0],
                    ["request", "contexto", "datos", "config", "usuario", "error"],
                    f"$def with({defn})",
                    f"El template `{_nombre(a)}` tiene:\n$def with({defn})\nLa primera variable es: {params[0]}",
                    rng
                ))

        # Qué itera el $for
        for var, coleccion in rng.sample(info["loops"], min(3, len(info["loops"]))):
            banco.append(_om(
                f"¿Sobre qué colección itera el bucle `$for {var} in ...` en `{_nombre(a)}`?",
                coleccion,
                ["items", "datos", "resultados", "registros", "lista", "elementos"],
                f"$for {var} in {coleccion}",
                f"En `{_nombre(a)}`:\n$for {var} in {coleccion}",
                rng
            ))

        # Acción del form
        for action in info["forms"][:2]:
            banco.append(_om(
                f"¿A qué URL apunta el `action` del formulario en `{_nombre(a)}`?",
                action,
                ["/admin/save", "/api/submit", "/datos/guardar", "/form/process"],
                f"<form action=\"{action}\">",
                f"En `{_nombre(a)}`:\n<form action=\"{action}\">",
                rng
            ))

        # Inputs: qué campos tiene el form
        if len(info["inputs"]) >= 3:
            muestra = rng.sample(info["inputs"], min(4, len(info["inputs"])))
            campo = muestra[0]
            banco.append(_om(
                f"¿Cuál campo `name` tiene un input en el template `{_nombre(a)}`?",
                campo,
                ["correo", "usuario", "token", "clave", "descripcion", "precio"],
                f"<input name=\"{campo}\"> en {_nombre(a)}",
                f"El template `{_nombre(a)}` tiene inputs con name:\n" + "\n".join(f"  name=\"{c}\"" for c in muestra),
                rng
            ))

    return _dedup(banco)


# ── BANCO RESPUESTA MÚLTIPLE ──────────────────────────────────────────────────

def _banco_rm(r: ResultadoValidacion, rng: random.Random) -> list[RespuestaMultiple]:
    banco = []
    py_files   = _py(r.archivos)
    sql_files  = _sql(r.archivos)
    html_files = _html(r.archivos)

    # Métodos de cada clase
    for a in py_files:
        for cls in _analizar_clases(a):
            nombres_m = [m["nombre"] for m in cls["metodos"]]
            if len(nombres_m) >= 2:
                banco.append(_rm(
                    f"¿Cuáles métodos define la clase `{cls['nombre']}` en `{_nombre(a)}`?",
                    nombres_m,
                    ["conectar","validar","serializar","autenticar","exportar","migrar"],
                    f"Métodos de {cls['nombre']}: {', '.join(nombres_m)}",
                    f"Abre {_nombre(a)} y busca `class {cls['nombre']}`. Métodos reales:\n" + "\n".join(f"  def {m}(...)" for m in nombres_m),
                    rng
                ))

    # Imports de cada archivo
    for a in py_files:
        imports = _analizar_imports(a)
        modulos = list(dict.fromkeys([i["modulo"] for i in imports if i["tipo"]=="from"]))
        if len(modulos) >= 2:
            banco.append(_rm(
                f"¿Desde cuáles módulos hace imports `{_nombre(a)}`?",
                modulos[:5],
                ["django.db","flask_login","numpy","pandas","requests","celery"],
                f"Módulos en {_nombre(a)}: {', '.join(modulos)}",
                f"Los imports 'from X' en {_nombre(a)} son:\n" + "\n".join(f"  from {m} import ..." for m in modulos[:5]),
                rng
            ))

        todos_nombres = []
        for i in imports:
            todos_nombres.extend(i["nombres"])
        todos_nombres = list(dict.fromkeys(todos_nombres))
        if len(todos_nombres) >= 3:
            muestra = todos_nombres[:5]
            banco.append(_rm(
                f"¿Cuáles de estas funciones/clases son importadas en `{_nombre(a)}`?",
                muestra,
                ["HttpResponse","validate_email","get_or_create","send_mail","render_to_pdf"],
                f"Nombres importados: {', '.join(todos_nombres)}",
                f"Los nombres importados en {_nombre(a)}:\n" + "\n".join(f"  {n}" for n in muestra),
                rng
            ))

    # Columnas de cada tabla SQL
    for a in sql_files:
        for tabla in _analizar_sql_tablas(a):
            cols = [c["col"] for c in tabla["columnas"]]
            if len(cols) >= 3:
                muestra = cols[:6]
                banco.append(_rm(
                    f"¿Cuáles columnas pertenecen a la tabla `{tabla['nombre']}`?",
                    muestra,
                    ["precio_total","codigo_barras","nombre_comercial","stock_minimo","descuento"],
                    f"Columnas de {tabla['nombre']}: {', '.join(cols)}",
                    f"La tabla `{tabla['nombre']}` tiene estas columnas:\n" + "\n".join(f"  {c}" for c in muestra),
                    rng
                ))

            # Columnas NOT NULL
            nn = [c["col"] for c in tabla["columnas"] if c["not_null"]]
            if len(nn) >= 2:
                banco.append(_rm(
                    f"¿Cuáles columnas de `{tabla['nombre']}` tienen la restricción NOT NULL?",
                    nn,
                    [c["col"] for c in tabla["columnas"] if not c["not_null"]][:4] or
                    ["descripcion","notas","observaciones"],
                    f"Columnas NOT NULL en {tabla['nombre']}: {', '.join(nn)}",
                    f"En `{tabla['nombre']}`, las columnas NOT NULL son:\n" + "\n".join(f"  {c}" for c in nn),
                    rng
                ))

            # FK: a qué tablas referencia
            if tabla["fks"]:
                tablas_ref = list(dict.fromkeys([t for _,t,_ in tabla["fks"]]))
                banco.append(_rm(
                    f"¿A cuáles tablas hace referencia `{tabla['nombre']}` mediante FOREIGN KEY?",
                    tablas_ref,
                    ["productos","categorias","perfiles","configuracion","auditoria"],
                    f"FKs de {tabla['nombre']}: {', '.join(tablas_ref)}",
                    f"La tabla `{tabla['nombre']}` referencia mediante FK a:\n" + "\n".join(f"  {t}" for t in tablas_ref),
                    rng
                ))

    # Inputs de formularios HTML
    for a in html_files:
        info = _analizar_html(a)
        if len(info["inputs"]) >= 3:
            banco.append(_rm(
                f"¿Cuáles campos (name) tiene el formulario en `{_nombre(a)}`?",
                info["inputs"][:5],
                ["correo","usuario","token","clave","descripcion","precio","cantidad"],
                f"Campos en {_nombre(a)}: {', '.join(info['inputs'])}",
                f"Los inputs con name en `{_nombre(a)}`:\n" + "\n".join(f"  name=\"{i}\"" for i in info["inputs"][:5]),
                rng
            ))

    return _dedup(banco)


# ── BANCO COMPLETAR CÓDIGO (bloques con 3-4 huecos) ───────────────────────────

def _bloque_con_huecos(lineas_originales: list[str], targets: list[str],
                        n_huecos: int = 3) -> tuple[str, list[str]] | None:
    """
    Dado un bloque de líneas real y una lista de palabras clave,
    sustituye n_huecos de ellas por _____ y devuelve (bloque_con_huecos, [respuestas]).

    Reglas:
    - Targets más largos tienen prioridad (evita partir 'color' con 'or')
    - Usa word boundaries para no partir palabras a la mitad
    - Solo un hueco por línea para no confundir
    """
    import re as _re
    respuestas = []
    lineas_modificadas = list(lineas_originales)
    huecos_hechos = 0
    # ordenar targets de más largo a más corto para que 'cursor' gane a 'or'
    targets_ordenados = sorted(targets, key=len, reverse=True)

    for i, linea in enumerate(lineas_modificadas):
        if huecos_hechos >= n_huecos:
            break
        if "_____" in linea:
            continue  # ya tiene hueco esta línea
        for t in targets_ordenados:
            # buscar como palabra completa con word boundary
            # excepto targets que son operadores/símbolos especiales
            if t.isalpha() or t.replace("_","").isalpha():
                patron = _re.compile(r'\b' + _re.escape(t) + r'\b')
            else:
                patron = _re.compile(_re.escape(t))
            if patron.search(linea):
                nueva_linea = patron.sub("_____", linea, count=1)
                if nueva_linea != linea:  # realmente cambió algo
                    lineas_modificadas[i] = nueva_linea
                    respuestas.append(t)
                    huecos_hechos += 1
                    break

    if huecos_hechos < 2:  # mínimo 2 huecos para ser válido
        return None

    return "\n".join(lineas_modificadas), respuestas


def _banco_cc(r: ResultadoValidacion, rng: random.Random) -> list[CompletarCodigo]:
    banco = []
    py_files   = _py(r.archivos)
    sql_files  = _sql(r.archivos)
    html_files = _html(r.archivos)

    PY_TARGETS = [
        "web","render","return","def","class","import","from",
        "None","True","False","not","and","or","if","else",
        "GET","POST","self","raise","try","except","with",
        "obtener_usuario_actual","redirigir","web.input",
        "web.ctx","web.header","web.notfound","web.template",
        "render_partials","render_hospitalizacion",
        "INTEGER","REAL","TEXT","NOT NULL","DEFAULT","PRIMARY KEY",
        "FOREIGN KEY","REFERENCES","CHECK","UNIQUE","AUTOINCREMENT",
        "psycopg2","cursor","fetchone","fetchall","execute","commit",
        "session","request","flash","redirect","url_for",
        "render_template","blueprint","Blueprint",
    ]

    SQL_TARGETS = [
        "INTEGER","REAL","TEXT","DATE","TIME",
        "NOT NULL","DEFAULT","PRIMARY KEY","AUTOINCREMENT",
        "FOREIGN KEY","REFERENCES","CHECK","UNIQUE",
        "CREATE TABLE","DROP TABLE","CREATE INDEX",
        "IF NOT EXISTS","ON","IN","AND","OR",
    ]

    HTML_TARGETS = [
        "$for","in","$if","$else","$def","with",
        "$extends","action","method","name","type","value",
        "POST","GET","required","class","id",
    ]

    vistos_bloques: set[str] = set()

    # ── Python: bloques de funciones/métodos reales ─────────────────────
    for a in py_files:
        codigo_lineas = a.codigo.splitlines()
        n = len(codigo_lineas)

        # Extraer bloques de 6-10 líneas alrededor de cada def
        indices_def = [i for i, l in enumerate(codigo_lineas) if re.match(r'\s*def\s+', l)]
        rng.shuffle(indices_def)

        for idx in indices_def:
            if len(banco) >= 60: break
            # Tomar 8 líneas desde el def
            bloque_lineas = codigo_lineas[idx: min(idx + 8, n)]
            bloque_lineas = [l for l in bloque_lineas if l.strip()]
            if len(bloque_lineas) < 4: continue

            clave = "\n".join(bloque_lineas)
            if clave in vistos_bloques: continue

            resultado = _bloque_con_huecos(bloque_lineas, PY_TARGETS, n_huecos=rng.randint(3,4))
            if not resultado: continue

            bloque_hueco, respuestas = resultado
            vistos_bloques.add(clave)

            nombre_func = re.search(r'def\s+(\w+)', codigo_lineas[idx])
            fn = nombre_func.group(1) if nombre_func else "esta función"

            banco.append(CompletarCodigo(
                instruccion=f"Completa el bloque de `{fn}` en `{_nombre(a)}` ({len(respuestas)} huecos):",
                codigo_con_huecos=bloque_hueco,
                respuestas=respuestas,
                explicacion=f"Bloque original de {_nombre(a)}:\n{clave}",
                retroalimentacion=f"El código original de `{fn}` en {_nombre(a)} es:\n{clave}",
            ))

    # ── Python: bloques de class body ───────────────────────────────────
    for a in py_files:
        codigo_lineas = a.codigo.splitlines()
        indices_class = [i for i, l in enumerate(codigo_lineas) if re.match(r'\s*class\s+', l)]
        rng.shuffle(indices_class)
        for idx in indices_class:
            if len(banco) >= 80: break
            bloque_lineas = codigo_lineas[idx: min(idx+6, len(codigo_lineas))]
            bloque_lineas = [l for l in bloque_lineas if l.strip()]
            if len(bloque_lineas) < 3: continue
            clave = "\n".join(bloque_lineas)
            if clave in vistos_bloques: continue
            resultado = _bloque_con_huecos(bloque_lineas, PY_TARGETS, 3)
            if not resultado: continue
            bloque_hueco, respuestas = resultado
            vistos_bloques.add(clave)
            nombre_cls = re.search(r'class\s+(\w+)', codigo_lineas[idx])
            cn = nombre_cls.group(1) if nombre_cls else "esta clase"
            banco.append(CompletarCodigo(
                instruccion=f"Completa la definición de `{cn}` en `{_nombre(a)}` ({len(respuestas)} huecos):",
                codigo_con_huecos=bloque_hueco,
                respuestas=respuestas,
                explicacion=f"Código original:\n{clave}",
                retroalimentacion=f"La clase `{cn}` en {_nombre(a)} está definida así:\n{clave}",
            ))

    # ── SQL: bloques de CREATE TABLE ─────────────────────────────────────
    for a in sql_files:
        bloques_sql = re.split(r'(CREATE TABLE\b)', a.codigo, flags=re.I)
        i = 0
        while i < len(bloques_sql) - 1:
            if re.match(r'CREATE TABLE', bloques_sql[i], re.I):
                bloque_completo = bloques_sql[i] + bloques_sql[i+1] if i+1 < len(bloques_sql) else bloques_sql[i]
                lineas = [l for l in bloque_completo.splitlines() if l.strip() and not l.strip().startswith('--')]
                lineas = lineas[:12]
                if len(lineas) >= 5:
                    clave = "\n".join(lineas)
                    if clave not in vistos_bloques:
                        resultado = _bloque_con_huecos(lineas, SQL_TARGETS, rng.randint(3,4))
                        if resultado:
                            bloque_hueco, respuestas = resultado
                            vistos_bloques.add(clave)
                            nombre_tabla = re.search(r'(\w+)\s*\(', bloque_completo)
                            nt = nombre_tabla.group(1) if nombre_tabla else "tabla"
                            banco.append(CompletarCodigo(
                                instruccion=f"Completa el bloque SQL de `{nt}` ({len(respuestas)} huecos):",
                                codigo_con_huecos=bloque_hueco,
                                respuestas=respuestas,
                                explicacion=f"Bloque SQL original:\n{clave}",
                                retroalimentacion=f"El bloque SQL original de `{nt}` es:\n{clave}",
                            ))
            i += 1

    # ── HTML: bloques de form / loop ─────────────────────────────────────
    for a in html_files:
        lineas_html = a.codigo.splitlines()
        n = len(lineas_html)

        # Bloques de $for
        for i, l in enumerate(lineas_html):
            if '$for' in l:
                bloque = lineas_html[i:min(i+8, n)]
                bloque = [x for x in bloque if x.strip()][:8]
                if len(bloque) < 4: continue
                clave = "\n".join(bloque)
                if clave in vistos_bloques: continue
                resultado = _bloque_con_huecos(bloque, HTML_TARGETS, 3)
                if not resultado: continue
                bloque_hueco, respuestas = resultado
                vistos_bloques.add(clave)
                banco.append(CompletarCodigo(
                    instruccion=f"Completa el bucle en `{_nombre(a)}` ({len(respuestas)} huecos):",
                    codigo_con_huecos=bloque_hueco,
                    respuestas=respuestas,
                    explicacion=f"Bloque original:\n{clave}",
                    retroalimentacion=f"El bloque original en {_nombre(a)}:\n{clave}",
                ))

        # Bloques de <form>
        for i, l in enumerate(lineas_html):
            if '<form' in l.lower():
                bloque = lineas_html[i:min(i+10, n)]
                bloque = [x for x in bloque if x.strip()][:10]
                if len(bloque) < 4: continue
                clave = "\n".join(bloque)
                if clave in vistos_bloques: continue
                resultado = _bloque_con_huecos(bloque, HTML_TARGETS, rng.randint(3,4))
                if not resultado: continue
                bloque_hueco, respuestas = resultado
                vistos_bloques.add(clave)
                banco.append(CompletarCodigo(
                    instruccion=f"Completa el formulario en `{_nombre(a)}` ({len(respuestas)} huecos):",
                    codigo_con_huecos=bloque_hueco,
                    respuestas=respuestas,
                    explicacion=f"Bloque original:\n{clave}",
                    retroalimentacion=f"El formulario original en {_nombre(a)}:\n{clave}",
                ))

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

def gen_completar_codigo(r, n=10, seed=42):
    rng = random.Random(seed)
    banco = _banco_cc(r, rng)
    rng.shuffle(banco)
    return banco[:n]

def gen_combinado(r, n=40, seed=42):
    rng = random.Random(seed)
    om = gen_opcion_multiple(r, 14, seed)
    rm = gen_respuesta_multiple(r, 13, seed)
    cc = gen_completar_codigo(r, 13, seed)
    mezclado = om + rm + cc
    rng.shuffle(mezclado)
    return mezclado[:n]

TITULOS = {
    "opcion_multiple":    ("Examen de opción múltiple",    "Selecciona la única respuesta correcta en cada pregunta."),
    "respuesta_multiple": ("Examen de respuesta múltiple", "Puede haber más de una respuesta correcta por pregunta."),
    "completar_codigo":   ("Examen de completar código",   "Escribe las palabras que van en cada hueco (_____) en orden."),
    "combinado":          ("Examen combinado",              "Mezcla de opción múltiple, respuesta múltiple y completar código."),
}

def generar_examen(r: ResultadoValidacion, tipo: str, seed: int = 42) -> Examen:
    titulo, desc = TITULOS.get(tipo, ("Examen",""))
    gens = {
        "opcion_multiple":    lambda: gen_opcion_multiple(r, 40, seed),
        "respuesta_multiple": lambda: gen_respuesta_multiple(r, 40, seed),
        "completar_codigo":   lambda: gen_completar_codigo(r, 10, seed),
        "combinado":          lambda: gen_combinado(r, 40, seed),
    }
    return Examen(titulo=titulo, descripcion=desc, tipo=tipo,
                  duracion_minutos=40, preguntas=gens[tipo]())