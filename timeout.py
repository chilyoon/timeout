import discord
from discord.ext import commands, tasks
import datetime
import requests
import re


intents = discord.Intents().all()
bot = commands.Bot(command_prefix=['$',], intents=intents)

VOTE_MSG_TO_TIMEOUT = {}

# Modification of @Rose's answer on https://stackoverflow.com/questions/70459488/discord-py-timeout-server-members
def timeout_user(bot, user_id, guild_id, expiration):
    url = "https://discord.com/api/v9/" + f'guilds/{guild_id}/members/{user_id}'

    headers = {"Authorization": f"Bot {bot.http.token}"}
    
    if expiration != None: until = expiration.isoformat()
    json = {'communication_disabled_until': until}

    session = requests.patch(url, json=json, headers=headers)
    return session.status_code

async def start_vote(message):
    min_votes = 3
    duration = 60

    options = re.findall('(\-[a-z] \d*)', message.content)
    for option in options:
        opt, val = option.split()
        if opt == '-t': duration = int(val)

    vote_message = await message.channel.send(
        f'''[VOTE HERE] Timeout {"".join(user.mention for user in message.mentions)} for {duration} seconds
{min_votes} people must agree.''')

    to = Timeout(bot, vote_message, min_votes=min_votes, duration=duration)
    VOTE_MSG_TO_TIMEOUT[vote_message] = to

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

        for kw in kwargs:
            if kw not in self.options:
                raise ValueError
            
            self.options[kw] = kwargs[kw]

        self.voted_users = set()

    async def add_new_voter(self, user):
        self.voted_users.add(user)

        if len(self.voted_users) >= self.options['min_votes']:
            self.activated = False
            await self.execute_timeout()
    
    async def remove_voter(self, user):
        self.voted_users -= {user, }

    async def execute_timeout(self):
        for user in self.target_users:
            if user == self.bot.user: continue

            # update expiration time
            self.expire_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.options['duration'])
            
            status = timeout_user(self.bot, user.id, self.guild.id, self.expire_at)

            if status == 200: # HTTP Patch success
                self.feedback_message = await self.channel.send(f"Timeout of {user.mention} has begun.")

    async def expire(self):
        if datetime.datetime.utcnow() > self.expire_at:
            if self.vote_message: await self.vote_message.delete()
            if self.feedback_message: await self.feedback_message.delete()
            return True
        
        else:
            return False



@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@bot.event
async def on_message(message):
    # captures vote suggestion message    
    if message.content.startswith('$timeout'):
        if message.mentions and bot.user not in message.mentions:
            await start_vote(message)
    
    text = re.findall('\$emoji ([a-z]+)', message.content)
    if text:
        emojis = [f':regional_indicator_{t}:' for t in text[0]]
        await message.channel.send(''.join(emojis))

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

        if await to.expire():
            expired.append(msg)

    for msg in expired:
        VOTE_MSG_TO_TIMEOUT.pop(msg)


if __name__ == '__main__':
    with open('token.txt') as f:
        TOKEN = f.read()

    pool.start()
    bot.run(TOKEN)