del /s /q build
del /s /q dist

py -m pip install -U pyinstaller
pyinstaller --name pog --add-data config.example.json;. main.py
