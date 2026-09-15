@echo off
setlocal

if not exist .venv (
    py -3.11 -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --name JuntaA --paths src src\juntaa\__main__.py

echo.
echo Build concluído. Executável em dist\JuntaA.exe
endlocal
