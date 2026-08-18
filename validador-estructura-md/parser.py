"""
parser.py  —  Validador de estructura Markdown (genérico)

Estrategia: extrae primero todos los bloques de código con sus posiciones
exactas en el texto original, luego busca headers SOLO en las zonas de
texto que NO caen dentro de un bloque de código.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field


# ── Estructuras ──────────────────────────────────────────────────────────────

@dataclass
class Archivo:
    titulo: str
    lenguaje: str
    codigo: str

    @property
    def lineas(self) -> int:
        return len(self.codigo.splitlines())


@dataclass
class Modulo:
    numero: str
    texto: str


@dataclass
class ResultadoValidacion:
    alumno: dict[str, str]          = field(default_factory=dict)
    proyecto_nombre: str            = ""
    proyecto_objetivo: str          = ""
    modulos: list[Modulo]           = field(default_factory=list)
    estructura: str                 = ""
    archivos: list[Archivo]         = field(default_factory=list)
    encontrado: dict[str, bool]     = field(default_factory=dict)
    titulos_detectados: list[str]   = field(default_factory=list)

    CAMPOS_ALUMNO_ESPERADOS = ["Nombre", "Primer Apellido", "Segundo Apellido", "Email", "Grupo"]

    @property
    def checklist(self) -> list[dict]:
        return [
            {"clave": "seccion1",  "ok": self.encontrado.get("seccion1",  False),
             "label": "1. Datos del proyecto",       "detalle": "Encabezado principal"},
            {"clave": "seccion11", "ok": self.encontrado.get("seccion11", False),
             "label": "1.1 Datos del alumno",        "detalle": "Nombre, email, grupo…"},
            {"clave": "seccion12", "ok": self.encontrado.get("seccion12", False),
             "label": "1.2 Datos del proyecto",      "detalle": "Objetivo y módulos"},
            {"clave": "seccion2",  "ok": self.encontrado.get("seccion2",  False),
             "label": "2. Proyecto",                 "detalle": "Encabezado principal"},
            {"clave": "seccion21", "ok": self.encontrado.get("seccion21", False),
             "label": "2.1 Estructura del proyecto", "detalle": "Árbol de carpetas"},
            {"clave": "archivos",  "ok": len(self.archivos) > 0,
             "label": "Archivos de código (2.2+)",   "detalle": f"{len(self.archivos)} detectado(s)"},
        ]

    @property
    def campos_alumno_faltantes(self) -> list[str]:
        return [c for c in self.CAMPOS_ALUMNO_ESPERADOS
                if not self.alumno.get(c, "").strip()]

    @property
    def estado(self) -> str:
        pasados = sum(1 for c in self.checklist if c["ok"])
        total   = len(self.checklist)
        if pasados == total and not self.campos_alumno_faltantes:
            return "ok"
        return "warn" if pasados >= total - 1 else "bad"

    @property
    def resumen(self) -> str:
        pasados = sum(1 for c in self.checklist if c["ok"])
        total   = len(self.checklist)
        if self.estado == "ok":
            return f"Estructura completa: {pasados}/{total} secciones y {len(self.archivos)} archivo(s)."
        if self.estado == "warn":
            return f"Casi completa: {pasados}/{total} secciones. Revisa la lista de verificación."
        return f"Faltan secciones importantes: solo {pasados}/{total} detectadas."


# ── Regex ────────────────────────────────────────────────────────────────────

_CAMPO_RE    = re.compile(r"^\s*\d+\.\s*([^:\n]+):\s*(.+)$", re.MULTILINE)
_NOMBRE_RE   = re.compile(r"^\s*\d+\.\s*Nombre del proyecto:\s*(.+)$", re.IGNORECASE)
_OBJETIVO_RE = re.compile(r"^\s*\d+\.\s*Objetivo:\s*(.+)$",           re.IGNORECASE)
_MODULO_RE   = re.compile(r"^\s+(\d+\.\d+)\s+(.+)$")
_PREFIJO_RE  = re.compile(r"^[\d.]+\s*")
_HEADER_RE   = re.compile(r"^(#{1,4}) (.+)$", re.MULTILINE)

_EXT_LANG = {
    "py": "python", "html": "html", "css": "css", "js": "javascript",
    "sql": "sql", "json": "json", "txt": "text", "gitignore": "git",
    "md": "markdown", "yml": "yaml", "yaml": "yaml",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _limpiar_titulo(t: str) -> str:
    return _PREFIJO_RE.sub("", t).strip() or t

def _adivinar_lang(titulo: str) -> str:
    ext = titulo.rsplit(".", 1)[-1].lower() if "." in titulo else ""
    return _EXT_LANG.get(ext, "text")

def _parsear_campos(txt: str) -> dict[str, str]:
    return {m.group(1).strip(): m.group(2).strip()
            for m in _CAMPO_RE.finditer(txt)}

def _parsear_proyecto(txt: str) -> tuple[str, str, list[Modulo]]:
    nombre, objetivo, mods = "", "", []
    for line in txt.splitlines():
        if (m := _NOMBRE_RE.match(line)):    nombre   = m.group(1).strip()
        elif (m := _OBJETIVO_RE.match(line)): objetivo = m.group(1).strip()
        elif (m := _MODULO_RE.match(line)):
            mods.append(Modulo(m.group(1), m.group(2).strip()))
    return nombre, objetivo, mods


# ── Extracción de bloques de código con posiciones ───────────────────────────

def _extraer_bloques(texto: str) -> list[dict]:
    """
    Devuelve lista de dicts con:
        ini, fin  -> posiciones en `texto` (incluyen los ``` delimitadores)
        lang      -> lenguaje declarado
        codigo    -> contenido del bloque (sin los delimitadores)
    """
    bloques = []
    pos = 0
    FENCE_OPEN = re.compile(r"^(`{3,4})(\S*)\s*$", re.MULTILINE)

    for mo in FENCE_OPEN.finditer(texto):
        if pos > mo.start():
            continue   # ya consumido por un bloque anterior
        fence    = mo.group(1)   # ``` o ````
        lang     = mo.group(2)
        close_re = re.compile(r"^" + re.escape(fence) + r"\s*$", re.MULTILINE)
        mc = close_re.search(texto, mo.end())
        if not mc:
            continue   # fence sin cerrar, ignorar
        bloques.append({
            "ini":    mo.start(),
            "fin":    mc.end(),
            "lang":   lang,
            "codigo": texto[mo.end(): mc.start()].strip("\n"),
        })
        pos = mc.end()

    return bloques


def _en_bloque(pos: int, bloques: list[dict]) -> bool:
    """True si `pos` cae dentro de algún bloque de código."""
    return any(b["ini"] <= pos < b["fin"] for b in bloques)


def _primer_bloque_en_rango(ini: int, fin: int, bloques: list[dict]):
    """Primer bloque cuyo inicio cae dentro de [ini, fin)."""
    for b in bloques:
        if ini <= b["ini"] < fin:
            return b
    return None


# ── Función principal ────────────────────────────────────────────────────────

def validar(texto: str) -> ResultadoValidacion:
    texto = texto.replace("\r\n", "\n")

    # 1. Ubicar todos los bloques de código para saber qué ignorar
    bloques = _extraer_bloques(texto)

    # 2. Extraer headers que NO estén dentro de un bloque de código
    headers = []
    for m in _HEADER_RE.finditer(texto):
        if not _en_bloque(m.start(), bloques):
            headers.append({
                "nivel":     len(m.group(1)),
                "titulo":    m.group(2).strip(),
                "inicio":    m.start(),
                "fin_match": m.end(),
            })

    resultado = ResultadoValidacion()
    resultado.titulos_detectados = [h["titulo"] for h in headers]
    resultado.encontrado = {k: False for k in
        ("seccion1", "seccion11", "seccion12", "seccion2", "seccion21")}

    for i, h in enumerate(headers):
        ini_contenido = h["fin_match"]
        fin_contenido = headers[i + 1]["inicio"] if i + 1 < len(headers) else len(texto)

        # Texto plano del segmento (puede contener marcadores de bloque)
        contenido_txt = texto[ini_contenido: fin_contenido]

        titulo       = h["titulo"]
        titulo_lower = titulo.lower()
        nivel        = h["nivel"]

        # ── secciones raíz ────────────────────────────────────────────────
        if nivel == 1 and re.match(r"1[\.\s]", titulo):
            resultado.encontrado["seccion1"] = True
        if nivel == 1 and re.match(r"2[\.\s]", titulo):
            resultado.encontrado["seccion2"] = True

        # ── secciones especiales (no son archivos) ────────────────────────
        if "datos del alumno" in titulo_lower:
            resultado.encontrado["seccion11"] = True
            resultado.alumno = _parsear_campos(contenido_txt)
            continue

        if "datos del proyecto" in titulo_lower and nivel >= 2:
            resultado.encontrado["seccion12"] = True
            n, o, mods = _parsear_proyecto(contenido_txt)
            resultado.proyecto_nombre   = n
            resultado.proyecto_objetivo = o
            resultado.modulos           = mods
            continue

        if "estructura del proyecto" in titulo_lower:
            resultado.encontrado["seccion21"] = True
            bloque = _primer_bloque_en_rango(ini_contenido, fin_contenido, bloques)
            if bloque:
                resultado.estructura = bloque["codigo"]
            continue

        # ── nivel 1 restante = contenedor ────────────────────────────────
        if nivel == 1:
            continue

        # ── nivel 2+ con bloque de código = archivo ───────────────────────
        bloque = _primer_bloque_en_rango(ini_contenido, fin_contenido, bloques)
        if bloque:
            titulo_limpio = _limpiar_titulo(titulo)
            resultado.archivos.append(Archivo(
                titulo   = titulo_limpio,
                lenguaje = bloque["lang"] or _adivinar_lang(titulo_limpio),
                codigo   = bloque["codigo"],
            ))

    return resultado
