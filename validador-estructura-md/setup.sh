#!/usr/bin/env bash
# setup.sh — crea el entorno virtual, instala dependencias y levanta la app
# Uso: bash setup.sh

set -e

echo ""
echo "▶ Creando entorno virtual (.venv)..."
python3 -m venv .venv

echo "▶ Activando entorno virtual..."
source .venv/bin/activate

echo "▶ Instalando dependencias..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo ""
echo "✔  Todo listo. Levantando la app..."
echo "   Abre http://127.0.0.1:5000 en tu navegador"
echo "   Ctrl+C para detener"
echo ""
python app.py
