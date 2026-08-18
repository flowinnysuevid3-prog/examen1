"""
Pruebas rápidas del módulo parser.py, sin levantar Flask.
Ejecutar con: python -m unittest test_parser.py  (o simplemente: python test_parser.py)
"""

import unittest
from pathlib import Path

from parser import validar

EJEMPLO = Path(__file__).parent / "estructura_base_ejemplo.md"


class TestParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.texto = EJEMPLO.read_text(encoding="utf-8")
        cls.resultado = validar(cls.texto)

    def test_secciones_detectadas(self):
        self.assertTrue(self.resultado.encontrado["seccion1"])
        self.assertTrue(self.resultado.encontrado["seccion11"])
        self.assertTrue(self.resultado.encontrado["seccion12"])
        self.assertTrue(self.resultado.encontrado["seccion2"])
        self.assertTrue(self.resultado.encontrado["seccion21"])

    def test_alumno(self):
        self.assertEqual(self.resultado.alumno["Nombre"], "Dejah")
        self.assertEqual(self.resultado.alumno["Email"], "1711243@email.com")
        self.assertEqual(self.resultado.alumno["Grupo"], "TI30")
        self.assertEqual(self.resultado.campos_alumno_faltantes, [])

    def test_proyecto(self):
        self.assertEqual(self.resultado.proyecto_nombre, "AgendaWeb")
        self.assertIn("agenda web", self.resultado.proyecto_objetivo.lower())
        self.assertEqual(len(self.resultado.modulos), 2)

    def test_estructura_de_carpetas(self):
        self.assertTrue(self.resultado.estructura.startswith("webapp/"))

    def test_archivos_detectados(self):
        self.assertEqual(len(self.resultado.archivos), 11)
        nombres = [a.titulo for a in self.resultado.archivos]
        self.assertIn("app.py", nombres)
        self.assertIn("views/contactos/ver_contacto.html", nombres)

    def test_estado_final(self):
        self.assertEqual(self.resultado.estado, "ok")


class TestParserProyectoDistinto(unittest.TestCase):
    """Confirma que el parser no depende del contenido de un proyecto en
    particular: valida InventarioWeb igual de bien que AgendaWeb."""

    @classmethod
    def setUpClass(cls):
        ruta = Path(__file__).parent / "ejemplos" / "inventario_ejemplo.md"
        cls.resultado = validar(ruta.read_text(encoding="utf-8"))

    def test_alumno_distinto(self):
        self.assertEqual(self.resultado.alumno["Nombre"], "Marco")
        self.assertEqual(self.resultado.alumno["Grupo"], "TI22")

    def test_proyecto_distinto(self):
        self.assertEqual(self.resultado.proyecto_nombre, "InventarioWeb")
        self.assertEqual(len(self.resultado.modulos), 2)

    def test_archivo_anidado(self):
        nombres = [a.titulo for a in self.resultado.archivos]
        self.assertIn("templates/index.html", nombres)

    def test_estado_ok(self):
        self.assertEqual(self.resultado.estado, "ok")


class TestParserIncompleto(unittest.TestCase):
    """Confirma que detecta correctamente cuando faltan secciones/campos,
    sin importar de qué proyecto se trate."""

    @classmethod
    def setUpClass(cls):
        ruta = Path(__file__).parent / "ejemplos" / "incompleto_ejemplo.md"
        cls.resultado = validar(ruta.read_text(encoding="utf-8"))

    def test_faltan_campos_alumno(self):
        self.assertIn("Segundo Apellido", self.resultado.campos_alumno_faltantes)
        self.assertIn("Grupo", self.resultado.campos_alumno_faltantes)

    def test_falta_estructura_de_carpetas(self):
        self.assertFalse(self.resultado.encontrado["seccion21"])

    def test_estado_no_es_ok(self):
        self.assertNotEqual(self.resultado.estado, "ok")


if __name__ == "__main__":
    unittest.main()
