#!/usr/bin/env python

import sys
import json
import random
import asyncio

import twitchio.ext.commands.bot


class SpammerBot(twitchio.ext.commands.bot.Bot):
    def __init__(self, config, *args, **kwargs):
        self.config = config
        if self.config['new_emote_on_startup']:
            self.config['emote'] = input('Emote to spam: ')
        self.keep_spamming_channels = True

        super().__init__(*args, **kwargs)

    def get_spam_message(self):
        if not self.config['emote']:
            print('No emotes in config!')
            sys.exit(1)
        if not self.config['msg_templates']:
            print('No message templates in config!')
            sys.exit(2)

        template = random.choice(self.config['msg_templates'])
        emote = self.config['emote']
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

    async def event_ready(self):
        print(f'Ready | {self.nick}')
        for channel_name in self.initial_channels:
            channel_object = self.get_channel(channel_name)
            self.loop.create_task(self.spam_channel(channel_object))

    async def event_pubsub(self, data):
        pass


def main():
    with open('config.json') as config_file:
        config = json.load(config_file)

    twitch_client = SpammerBot(
        config=config,
        irc_token=config['login']['oauth_token'], nick=config['login']['username'], prefix='j.',
        initial_channels=['ThePogMarket']
    )
    print('Starting')
    twitch_client.run()


if __name__ == '__main__':
    main()
