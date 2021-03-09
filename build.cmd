py -m pip install -U pyinstaller
pyinstaller -y --name pog --icon PogChamp.ico --add-data config.example.json;. main.py
tar -c -f "zips\pog-exe.zip" -C "dist" "pog"
