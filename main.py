#!/usr/bin/env python

import sys
import json
import time
import random
import asyncio

import aiohttp
import twitchio.ext.commands.bot


class SpammerBot(twitchio.ext.commands.bot.Bot):
    def __init__(self, config, *args, **kwargs):
        self.config = config
        if not self.config['emote']:
            print('No emote in config!')
            sys.exit(1)
        if len(self.config['msg_templates']) < 2:
            print('Not enough message templates in config (need >2)!')
            sys.exit(2)

        if self.config['use_api']:
            self.last_api_update_time = 0
            self.prev_emote = self.emote
        elif self.config['new_emote_on_startup']:
            self.emote = input('Emote to spam: ')
        else:
            self.emote = self.config['emote']


        self.keep_spamming_channels = True

        super().__init__(*args, **kwargs)

    async def switch_emote(self, new_emote, channel):
        print(f"Selling old emote and buying new - this will take {self.config['cooldown_seconds'] * 2} seconds")
        await asyncio.sleep(self.config['cooldown_seconds'])
        await channel.send(f'!sell {self.emote} all')

        self.emote, self.prev_emote = new_emote, self.emote

        await asyncio.sleep(self.config['cooldown_seconds'])
        await channel.send(f'!buy {self.emote} all')
        print(f'Sold old emote {self.prev_emote} and bought new emote {self.emote}')

    def get_spam_message(self):
        template = random.choice(self.config['msg_templates'])
        spam_message = template.format(self.emote, emote=self.emote)

        return spam_message

    async def update_from_api(self, channel):
        current_time = time.time() // self.config['api_refresh_interval']
        if self.last_api_update_time < current_time:
            print('Checking api for new emote...')
            async with aiohttp.ClientSession(loop=self.loop) as aiohttp_session:
                async with aiohttp_session.get(self.config['api_url']) as api_response:
                    new_emote = await api_response.json()

            if new_emote != self.emote:
                print(f'New emote: {new_emote}')
                await self.switch_emote(new_emote, channel)
                print('Switched to new emote')

    async def spam_channel(self, channel):
        while self.keep_spamming_channels:
            if self.config['use_api']:
                await self.update_from_api(channel)

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
