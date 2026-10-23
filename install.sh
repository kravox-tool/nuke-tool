#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "[*] Instalando dependencias del sistema..."
pkg update -y
pkg install -y python git clang make libffi openssl

echo "[*] Preparando pip..."
python -m pip install --upgrade pip setuptools wheel

echo "[*] Instalando dependencias de Python..."
pip install -r requirements.txt

echo "[+] Listo. Ejecuta: python main.py"
