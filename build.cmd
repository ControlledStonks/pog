py -m pip install -U pyinstaller
pyinstaller --onefile --name pog --add-data config.example.json;config.example.json main.py
