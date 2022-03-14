import discord
from discord.ext import commands
import datetime
import requests

with open('token.txt') as f:
    token = f.read()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=['$',], intents=intents)

VOTE_STATUS = {} # dictionary of, (Message)vote_message:(list)voted_users

async def vote_count(message, user_id, threshold=1):
    if user_id in VOTE_STATUS[message]:
        # print('vote not counted')
        return
    
    else:
        VOTE_STATUS[message].append(user_id)
        # print('vote counted')

        if len(VOTE_STATUS) >= threshold:
            await begin_timeout(message)

# Modification of @Rose's answer on https://stackoverflow.com/questions/70459488/discord-py-timeout-server-members
def timeout_user(user_id, guild_id, duration):
    url = "https://discord.com/api/v9/" + f'guilds/{guild_id}/members/{user_id}'
    
    headers = {"Authorization": f"Bot {bot.http.token}"}

    timeout = (datetime.datetime.utcnow() + datetime.timedelta(seconds=duration)).isoformat()
    json = {'communication_disabled_until': timeout}

    session = requests.patch(url, json=json, headers=headers)
    # print(session.status_code)

async def begin_timeout(message):
    guild_id = message.guild.id

    mentions = message.mentions
    for m in mentions:
        user_id = m.id
        timeout_user(user_id, guild_id, 60)

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@bot.event
async def on_message(message):    
    if message.content.startswith('$timeout'):
        if message.mentions:
            await message.channel.send('[VOTE HERE] Timeout ' + ''.join(m.mention for m in message.mentions))
        
        await message.delete()
        return
    
    if message.author == bot.user:
        if message.content.startswith('[VOTE HERE]'):
            VOTE_STATUS[message] = []
        
        return

@bot.event
async def on_reaction_add(reaction, user):
    if reaction.message in VOTE_STATUS:
        await vote_count(reaction.message, user.id)

bot.run(token)