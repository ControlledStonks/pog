# pog
poggers

## usage
1. Duplicate `config.example.json` to create `config.json`
2. Fill in your login details; if you don't have an oauth token, or a way to get one you can use [this website](https://twitchapps.com/tmi/), but bear in mind that will give the token total control over your account rather than just the ability to send messages.
3. Fill in the emote you want to use. You can also add any templates you want.    
   If you want to input a new emote every time you run the program instead, just set `new_emote_on_startup` to `true`.
4. Install [Python](https://www.python.org/downloads/), if you haven't already
5. Install the required python packages ([`twitchio`](https://pypi.org/project/twitchio/)) - `python -m pip install -r requirements.txt` in the command line, in this folder
6. Run main.py
