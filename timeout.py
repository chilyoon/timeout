import discord
from discord import user
from discord.ext import commands, tasks
import datetime
import requests
import re

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=['$', ], intents=intents)
client = discord.client
VOTE_MSG_TO_TIMEOUT = {}


# Modification of @Rose's answer on https://stackoverflow.com/questions/70459488/discord-py-timeout-server-members
def timeout_user(bot, user_id, guild_id, expiration):
    url = "https://discord.com/api/v9/" + f'guilds/{guild_id}/members/{user_id}'

    headers = {"Authorization": f"Bot {bot.http.token}"}

    if expiration != None: until = expiration.isoformat()
    json = {'communication_disabled_until': until}

    session = requests.patch(url, json=json, headers=headers)
    return session.status_code



class Timeout:
    def __init__(self, bot, vote_message, **kwargs):
        self.bot = bot

        self.activated = True

        self.vote_message = vote_message
        self.feedback_message = None

        self.target_users = vote_message.mentions
        self.channel = vote_message.channel
        self.guild = vote_message.guild

        self.expire_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)

        self.options = {
            'min_votes': 3,
            'duration': 60,
        }


    async def execute_timeout(self):
        for user in self.target_users:
            if user == self.bot.user: continue

            # update expiration time
            self.expire_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.options['duration'])

            status = timeout_user(self.bot, user.id, self.guild.id, self.expire_at)

            if status == 200:  # HTTP Patch success
                self.feedback_message = await self.channel.send(f"{user.mention} 유저에게 타임아웃을 적용합니다.")

    async def expire(self):
        if datetime.datetime.utcnow() > self.expire_at:
            if self.vote_message: await self.vote_message
            if self.feedback_message: await self.feedback_message
            return True

        else:
            return False


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))


@bot.event
async def on_message(message):
    # mute, umute command
        if message.content.startswith('!mute'):
            author = message.guild.get_member(int(message.content[6:24]))
            role = discord.utils.get(message.guild.roles, name="Mute")
            channel = message.channel
            await author.add_roles(role)
            await channel.send('채팅을 차단합니다')

        if message.content.startswith('!umute'):
            author = message.guild.get_member(int(message.content[7:25]))
            role = discord.utils.get(message.guild.roles, name="Mute")
            await author.remove_roles(role)
            channel = message.channel
            await channel.send('차단을 해제합니다')



@bot.event
async def on_reaction_add(reaction, user):
    message = reaction.message

    if message in VOTE_MSG_TO_TIMEOUT:
        to = VOTE_MSG_TO_TIMEOUT[message]
        if to.activated: await to.add_new_voter(user)

@bot.event
async def on_reaction_remove(reaction, user):
    message = reaction.message

    if message in VOTE_MSG_TO_TIMEOUT:
        to = VOTE_MSG_TO_TIMEOUT[message]
        await to.remove_voter(user)


@tasks.loop(seconds=10)
async def pool():
    expired = []

    for msg in VOTE_MSG_TO_TIMEOUT:
        to = VOTE_MSG_TO_TIMEOUT[msg]

    for msg in expired:
        VOTE_MSG_TO_TIMEOUT.pop(msg)


if __name__ == '__main__':
    with open('token.txt') as f:
        TOKEN = f.read()

    pool.start()
    bot.run(TOKEN)
