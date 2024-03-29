#!/usr/bin/env python

import sys
import json
import datetime
import asyncio
import argparse
import typing

import aiohttp
import twitchio.ext.commands.bot


__version__ = '4.5.0'


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
        self.send_lock = asyncio.Lock()

        super().__init__(
            irc_token='oauth:' + self.config['login']['oauth_token'],
            api_token=self.config['login']['oauth_token'],
            client_id=self.config['login']['client_id'],
            nick=self.config['login']['username'],
            prefix='j!',
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
            new_oauth = input('Twitch oauth token: ')
            self.config['login']['oauth_token'] = new_oauth
            self.save_config()
        # check for correct prefix on oauth token
        if self.config['login']['oauth_token'].startswith('oauth:'):
            self.config['login']['oauth_token'] = self.config['login']['oauth_token'][len('oauth:'):]
            self.save_config()

    async def send(self, messageable, content):
        async with self.send_lock:
            await asyncio.sleep(self.config['slowmode_seconds'])
            await messageable.send(content)

    async def switch_emote(self, new_emote, channel):
        print(f"Selling old emote and buying new - this will take {self.config['slowmode_seconds'] * 3} seconds")
        await self.send(channel, f'!sell {self.emote} all')

        self.emote, self.prev_emote = new_emote, self.emote
        self.config['emote'] = self.emote
        self.save_config()

        await self.send(channel, f'!buy {self.emote} all')

        await self.send(channel, f'!boost {self.emote} {self.emote} {self.emote}')
        print(f'Sold old emote {self.prev_emote} and bought, boosted new emote {self.emote}')

    async def update_from_api(self, channel):
        print('Checking api for new emote...')
        async with aiohttp.ClientSession(loop=self.loop) as aiohttp_session:
            try:
                async with aiohttp_session.get(self.config['api_url']) as api_response:
                    response_json = await api_response.json()
            except aiohttp.ClientConnectionError:
                print('Unable to connect to api')
                return
            else:
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

    async def claim_present(self, channel):
        utcnow = datetime.datetime.utcnow()
        days_since_epoch = (utcnow - datetime.datetime(1970, 1, 1)).days
        if days_since_epoch > self.config['last_present_claim']:
            self.config['last_present_claim'] = days_since_epoch
            self.save_config()
            await self.send(channel, '!present')
            print(f"Claimed present for {utcnow.strftime('%d/%m/%y')}, at {utcnow.strftime('%H:%M')} (UTC)")

    async def run_switcher(self):
        channel_objects: typing.List[twitchio.Channel] = [self.get_channel(c) for c in self.initial_channels]

        while self.keep_switching_emote:
            await asyncio.sleep(self.config['api_refresh_interval'])
            for channel in channel_objects:
                # check if the channel is live before bothering to do anything
                try:
                    channel_stream_info = await channel.get_stream()
                except twitchio.Unauthorized:
                    print(
                        f'Unable to check if channel {channel.name} is live, assuming it is.\n'
                        '  (Check your login client_id in config.json)'
                    )
                    channel_live = True
                else:
                    channel_live = channel_stream_info is not None

                if channel_live:
                    await self.update_from_api(channel)
                    await self.claim_present(channel)
                # todo: sleep for longer if the channel is not live?
                else:
                    print(f'Channel {channel.name} is not live, skipping')

    async def event_ready(self):
        print(f'Ready | {self.nick}')

        self.loop.create_task(self.run_switcher())

    async def event_pubsub(self, data):
        pass


twitch_client = PogBot(config_path='config.json', initial_channels=['ThePogMarket'])


# todo: put these in the class definition instead now I'm sure how to?
async def is_bot_user(ctx):
    return ctx.author.name == twitch_client.nick


# todo: prestige multiple times - standalone command
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
        print(f'Sending command {subcommand}')
        await twitch_client.send(ctx, subcommand)


# noinspection PyTypeChecker
@twitch_client.command(aliases=['prestigec', 'calc'])
@twitchio.ext.commands.check(is_bot_user)
async def prestigecalc(ctx, twitchcoin: int):
    if twitchcoin <= 500000:
        return await twitch_client.send(ctx, 'Too few twitchcoin')

    prestiges = 0
    remaining = twitchcoin
    out_text = str(twitchcoin)
    while remaining > 500000:
        remaining = int(remaining * 0.7)
        prestiges += 1
        out_text += f' -> {prestiges} -> {remaining}'

    await twitch_client.send(ctx, out_text)


# noinspection PyTypeChecker
@twitch_client.command(aliases=['prestige'])
@twitchio.ext.commands.check(is_bot_user)
async def prestigex(ctx, number: int):
    if number < 1:
        return

    print(f'Got prestige command !prestigex {number}')
    print(f'Prestiging {number} times')

    await twitch_client.send(ctx, f'!sell {twitch_client.emote} all')

    for i in range(number):
        await twitch_client.send(ctx, f'!prestige')
        await twitch_client.send(ctx, f'!prestige confirm')

    await twitch_client.send(ctx, f'!buy {twitch_client.emote} all')
    print(f'Done prestiging {number} times')


def main():
    parser = argparse.ArgumentParser(description='Self-bot for our twitch.tv/ThePogMarket team. Just run it!')
    parser.add_argument('--version', action='version', version=__version__)
    parser.parse_args()

    print('Starting')
    twitch_client.run()


if __name__ == '__main__':
    main()
