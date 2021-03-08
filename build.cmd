py -m pip install -U pyinstaller
pyinstaller -y --name pog --add-data config.example.json;. main.py
