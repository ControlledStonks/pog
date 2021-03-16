#!/usr/bin/env python

import sys
import json
import asyncio

import aiohttp
import twitchio.ext.commands.bot


__version__ = '4.0.0'


class PogBot(twitchio.ext.commands.Bot):
    def __init__(self, config_path, *args, **kwargs):
        try:
            with open(config_path) as config_file:
                self.config = json.load(config_file)
        except FileNotFoundError:
            try:
                with open('config.example.json') as config_example_file:
                    self.config = json.load(config_example_file)
                    self.save_config()
            except FileNotFoundError:
                print('Config file and config.example.json not found!')
                input()
                sys.exit(1)

        self.check_login()
        # emote getting logic
        if self.config['new_emote_on_startup']:
            self.config['emote'] = input('Emote to spam: ')
            self.save_config()
        if not self.config['emote']:
            print('No emote in config!')
            input()
            sys.exit(3)
        self.emote = self.config['emote']

        self.prev_emote = self.emote
        self.keep_switching_emote = True

        super().__init__(
            irc_token=self.config['login']['oauth_token'], nick=self.config['login']['username'], prefix='j!',
            *args, **kwargs
        )

    def save_config(self):
        with open('config.json', 'w') as config_file:
            json.dump(self.config, config_file)

    def check_login(self):
        # check for username and get from input if not present
        if not self.config['login']['username']:
            new_username = input('Twitch username: ')
            self.config['login']['username'] = new_username
            self.save_config()
        # check for token and get from input if not present
        if not self.config['login']['oauth_token']:
            new_username = input('Twitch oauth token: ')
            self.config['login']['oauth_token'] = new_username
            self.save_config()
        # check for correct prefix on oauth token
        if not self.config['login']['oauth_token'].startswith('oauth:'):
            self.config['login']['oauth_token'] = 'oauth:' + self.config['login']['oauth_token']
            self.save_config()

    async def switch_emote(self, new_emote, channel):
        print(f"Selling old emote and buying new - this will take {self.config['slowmode_seconds'] * 3} seconds")
        await asyncio.sleep(self.config['slowmode_seconds'])
        await channel.send(f'!sell {self.emote} all')

        self.emote, self.prev_emote = new_emote, self.emote
        self.config['emote'] = self.emote
        self.save_config()

        await asyncio.sleep(self.config['slowmode_seconds'])
        await channel.send(f'!buy {self.emote} all')

        await asyncio.sleep(self.config['slowmode_seconds'])
        await channel.send(f'!boost {self.emote} {self.emote} {self.emote}')
        print(f'Sold old emote {self.prev_emote} and bought, boosted new emote {self.emote}')

    async def update_from_api(self, channel):
        print('Checking api for new emote...')
        async with aiohttp.ClientSession(loop=self.loop) as aiohttp_session:
            async with aiohttp_session.get(self.config['api_url']) as api_response:
                response_json = await api_response.json()
                if isinstance(response_json, str):
                    new_emote = response_json
                else:
                    new_emote = response_json['emote']
                    if 'new_api_url' in response_json:
                        self.config['api_url'] = response_json['new_api_url']
                        self.save_config()

        if new_emote != self.emote:
            print(f'New emote: {new_emote}')
            await self.switch_emote(new_emote, channel)
            print('Switched to new emote')

    async def run_switcher(self):
        channel_objects = [self.get_channel(c) for c in self.initial_channels]

        while self.keep_switching_emote:
            await asyncio.sleep(self.config['api_refresh_interval'])
            for channel in channel_objects:
                await self.update_from_api(channel)

    async def event_ready(self):
        print(f'Ready | {self.nick}')

        self.loop.create_task(self.run_switcher())

    async def event_pubsub(self, data):
        pass


twitch_client = PogBot(config_path='config.json', initial_channels=['ThePogMarket'])


async def is_bot_user(ctx):
    return ctx.author.name == twitch_client.nick


# noinspection PyTypeChecker
@twitch_client.command(aliases=['multi'])
@twitchio.ext.commands.check(is_bot_user)
async def multirun(ctx, *, subcommands):
    macros = {
        'prestige': lambda: 'sell {emote} all; prestige; prestige confirm; buy {emote} all'
                            .format(emote=twitch_client.emote)
    }

    print(f'Got multirun command j!multirun {subcommands}')
    if subcommands in macros:
        subcommands = macros[subcommands]()
        print(f'Converted to macro: {subcommands}')
    for subcommand in subcommands.split(';'):
        subcommand = '!' + subcommand.strip()
        print(f"Waiting for {twitch_client.config['slowmode_seconds']} seconds")
        await asyncio.sleep(twitch_client.config['slowmode_seconds'])
        print(f'Sending command {subcommand}')
        await ctx.send(subcommand)


if __name__ == '__main__':
    print('Starting')
    twitch_client.run()
