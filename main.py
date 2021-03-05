#!/usr/bin/env python

import sys
import json
import random
import asyncio

import twitchio.ext.commands.bot


class SpammerBot(twitchio.ext.commands.bot.Bot):
    def __init__(self, config, *args, **kwargs):
        self.keep_spamming_channels = True
        self.config = config
        super().__init__(*args, **kwargs)

    def get_spam_message(self):
        if not self.config['emotes']:
            print('No emotes in config!')
            sys.exit(1)
        if not self.config['msg_templates']:
            print('No message templates in config!')
            sys.exit(2)

        template = random.choice(self.config['msg_templates'])
        emote = random.choice(self.config['emotes'])
        spam_message = template.format(emote, emote=emote)

        return spam_message

    async def spam_channel(self, channel):
        while self.keep_spamming_channels:
            print(f"{channel} - waiting for {self.config['cooldown_seconds']} seconds")
            await asyncio.sleep(self.config['cooldown_seconds'])
            spam_message = self.get_spam_message()
            print(f"{channel} - {spam_message}")
            await channel.send(spam_message)
            print(f"{channel} - message sent")

    async def on_ready(self):
        print(f'Ready | {self.nick}')
        # todo: spool off spam_channel for each joined channel

    async def event_pubsub(self, data):
        pass


def main():
    with open('config.json') as config_file:
        config = json.load(config_file)

    twitch_client = SpammerBot(
        config=config,
        irc_token=config['login']['oauth_token'], nick=config['login']['oauth_token'], prefix='j.',
        initial_channels=['ThePogMarket']
    )
    print('Starting')
    twitch_client.run()
