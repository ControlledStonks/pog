#!/usr/bin/env python

import sys
import json
import time
import random
import asyncio
import threading
if sys.platform == 'win32':
    import msvcrt

import aiohttp
import twitchio.ext.commands.bot


# todo: discord bot command to rip all twitch emotes
# todo: make it so the same template won't be used twice in a row
# todo: linux support for controls, with getch


__version__ = '3.0.0'


class SpammerBot(twitchio.ext.commands.Bot):
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
        if len(self.config['msg_templates']) < 2:
            print('Not enough message templates in config (need >2)!')
            input()
            sys.exit(2)

        # emote getting logic
        if self.config['new_emote_on_startup']:
            self.config['emote'] = input('Emote to spam: ')
            self.save_config()
        if not self.config['emote']:
            print('No emote in config!')
            input()
            sys.exit(3)
        self.emote = self.config['emote']

        self.last_api_update_time = 0
        self.prev_emote = self.emote
        self.last_used_template = ''

        self.keep_spamming_channels = True
        self.run_control_loop = True
        self.quit = False

        super().__init__(
            irc_token=self.config['login']['oauth_token'], nick=self.config['login']['username'], prefix='j!',
            *args, **kwargs
        )

    def control_loop(self):
        if sys.platform != 'win32':
            return

        print(
            f"{self.config['controls']['quit']}: quit\n"
            f"{self.config['controls']['pause_spam']}: pause spam\n"
            f"{self.config['controls']['resume_spam']}: resume spam\n"
            'Customise controls in config.json'
        )
        while self.run_control_loop:
            if msvcrt.kbhit():
                keypress = msvcrt.getch().decode()
                if keypress == self.config['controls']['quit']:
                    print('Quitting..')
                    self.quit = True
                    sys.exit()
                elif keypress == self.config['controls']['pause_spam']:
                    if self.keep_spamming_channels:
                        print('Pausing spam..')
                        self.keep_spamming_channels = False
                        time.sleep(self.config['cooldown_seconds'])
                        print('Paused spam.')
                elif keypress == self.config['controls']['resume_spam']:
                    if not self.keep_spamming_channels:
                        print('Resuming spam..')
                        self.keep_spamming_channels = True
                        self.spool_spammers()
                        print('Resumed spam.')

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
        print(f"Selling old emote and buying new - this will take {self.config['cooldown_seconds'] * 2} seconds")
        await asyncio.sleep(self.config['cooldown_seconds'])
        await channel.send(f'!sell {self.emote} all')

        self.emote, self.prev_emote = new_emote, self.emote
        self.config['emote'] = self.emote
        self.save_config()

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

    async def spam_channel(self, channel):
        while self.keep_spamming_channels:
            if self.quit:
                sys.exit()

            if self.config['use_api']:
                await self.update_from_api(channel)

            print(f"{channel} - waiting for {self.config['cooldown_seconds']} seconds")
            await asyncio.sleep(self.config['cooldown_seconds'])

            spam_message = self.get_spam_message()
            print(f"{channel} - {spam_message}")

            await channel.send(spam_message)
            print(f"{channel} - message sent")

    def spool_spammers(self):
        for channel_name in self.initial_channels:
            channel_object = self.get_channel(channel_name)
            self.loop.create_task(self.spam_channel(channel_object))

    async def event_ready(self):
        print(f'Ready | {self.nick}')
        self.spool_spammers()
        threading.Thread(target=self.control_loop, daemon=True).start()

    async def event_pubsub(self, data):
        pass


twitch_client = SpammerBot(config_path='config.json', initial_channels=['ThePogMarket'])


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
    for subcommand in subcommands.split(';'):
        subcommand = '!' + subcommand.strip()
        print(f"Waiting for {twitch_client.config['cooldown_seconds']} seconds")
        await asyncio.sleep(twitch_client.config['cooldown_seconds'])
        print(f'Sending command {subcommand}')
        await ctx.send(subcommand)


if __name__ == '__main__':
    print('Starting')
    twitch_client.run()
