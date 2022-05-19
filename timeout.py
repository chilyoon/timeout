import discord
from discord.ext import commands, tasks
import datetime
import requests
from word_detection import word_detection   #비속어 필터링

a = word_detection()
a.load_data()
a.load_badword_data()

def filter(message):        #비속어 필터링
        word = str(message)
        a.input = word
        a.text_modification()
        a.lime_compare(a.token_badwords, a.token_detach_text[0], 0.9)
        result = a.result
        a.lime_compare(a.new_token_badwords, a.token_detach_text[1], 0.9, True)
        result += a.result
        if len(result) == 0:
            return False
        else:
            return True


intents = discord.Intents().all()
bot = commands.Bot(command_prefix=['$', ], intents=intents)

MSG_TO_TIMEOUT = {}


# Modification of @Rose's answer on https://stackoverflow.com/questions/70459488/discord-py-timeout-server-members
def timeout_user(bot, user_id, guild_id, expiration):
    url = "https://discord.com/api/v9/" + f'guilds/{guild_id}/members/{user_id}'

    headers = {"Authorization": f"Bot {bot.http.token}"}

    if expiration != None: until = expiration.isoformat()
    json = {'communication_disabled_until': until}

    session = requests.patch(url, json=json, headers=headers)
    return session.status_code


class Timeout:
    def __init__(self, bot, message, **kwargs):
        self.bot = bot

        self.activated = True

        self.message = message
        self.feedback_message = None

        self.target_users = message.author
        self.channel = message.channel
        self.guild = message.guild

        self.expire_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)

        self.options = {
            'min_votes': 3,
            'duration': 60,
        }

        for kw in kwargs:
            if kw not in self.options:
                raise ValueError

            self.options[kw] = kwargs[kw]

    # 타임아웃 기능
    async def execute_timeout(self):
        self.activated = False
        if self.target_users != self.bot.user:
            self.expire_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.options['duration'])

            status = timeout_user(self.bot, self.target_users.id, self.guild.id, self.expire_at)
            users=self.target_users
            if status == 200:  # HTTP Patch success
                self.feedback_message = await self.channel.send(f"{users.mention}에게 비속어 사용으로 인한 타임아웃을 적용합니다.")

    async def expire(self):
        if datetime.datetime.utcnow() > self.expire_at:
            users = self.target_users
            if self.feedback_message: await self.channel.send(f"{users.mention}에게 적용된 타임아웃을 해제합니다") # 봇 메시지
            return True

        else:
            return False


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))


@bot.event
async def on_message(message):
    if message.author.bot:
        return None
    if filter(message.content) == True:
        to = Timeout(bot, message)
        MSG_TO_TIMEOUT[message] = to
        await to.execute_timeout()      # 추가


@tasks.loop(seconds=10)
async def pool():
    expired = []

    for msg in MSG_TO_TIMEOUT:
        to = MSG_TO_TIMEOUT[msg]

        if await to.expire():
            expired.append(msg)

    for msg in expired:
        MSG_TO_TIMEOUT.pop(msg)


if __name__ == '__main__':
    with open('token.txt') as f:
        TOKEN = f.read()

    pool.start()
    bot.run(TOKEN)
