py -m pip install -U pyinstaller
pyinstaller -y --name pog --add-data config.example.json;. main.py
tar -c -f "zips\pog-exe.zip" "dist\pog"
