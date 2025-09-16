import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
from discord import TextChannel
import random, uuid, requests, asyncio, os, platform, psutil, threading
from flask import Flask
from datetime import datetime
import hashlib
from loguru import logger

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1405933240212258816
OWNER_ID = 1065954764019470420
ALERT_CHANNEL_ID = 1415593892585406525
CHANNEL_UI_ID = 1415555699454246985
CHANNEL_STATUS_ID = 1415345695069835267
CHANNEL_GUIDE_ID = 1415555569753788426
STATUS_DASHBOARD_ID = 1417378674537267333

bot_start_time = datetime.utcnow()
logger.remove()
logger.add("logs/bot.log", rotation="1 MB", retention="7 days", level="INFO")
logger.add("logs/error.log", rotation="1 MB", retention="7 days", level="ERROR")
logger.info(f"Bot initializing with fingerprint: {hashlib.sha256(f'{OWNER_ID}_{GUILD_ID}_NEKTRI_BOT'.encode()).hexdigest()[:16]}")

RANDOM_MESSAGES = [
    "เงี่ยนพ่อมึงอะ","จับยัดนะควย","ลงสอตรี่หาพ่อมึงเถอะ","พ่อเเม่พี่ตายยัง",
    "กู  nektri ","พ่อมึงต่ายลูกอีเหี้ย","ไปต่ายเถอะ","หี","ลูกหมา","ลุกเม่ต่าย",
    "กูNEKTRI","มาดิสัส","อย่าเก่งเเต่ปาก","มึงโดนเเล้ว","บักควย","ลุกอีสัส",
    "สันด้านหมา","มึงไม่ดีเอง","เกิดมาหาพ่อมึงอะ","อีสานจัด","มาดิจะ","นัดตีป่าว",
    "ออกมากูรอละ","ใจ๋กากจัด","ว้าวๆๆๆบูห","เข้ามาดิ","ไปต่าย","สาธุ1111","ลูกกาก",
    "ปากเเตก","น่าโดนสนตีน","หมดหี","ขายหีหรอหรือหำ","รั่วไหม","หนูเงี่ยนอะเสี่ย",
    "ช่วยเย็ดหน่อย","เป็นเเฟนเเม่มึงได้ไหม","ควย","สัส","ปัญญาอ่อนจัด","มา",
    "ทำไรห","กูสั่งงาน","กลับมาละ","เแลกหใัเไหใ","เขียนหร","กกนห","ขอเย็ดเเม่มึฃ",
    "หำเข็ฃ","เเตกในปะ","ควยเเข็งจริงนะ","ไม่ไหวเเตกละ",'เอารูปเเม่มึงมาเเตกในละ',
    "เสี่ยงมาก","ไปไหน","ไปพ่องไหม","พ่อมึงไปไหน","ลูกอีปอบ","พ่อมึงสั่งสอนปะ",
    "รั่วหี","ไอ้สัด","ไอ้เหี้ย","มึงบักหำ","สันดานหมา","อีเหี้ยเอ๊ย","ไอ้สัสสัส",
    "มึงเน่า","หัวควย","มึงกาก","อีสัส","ไอ้บัดซบ","สันขวานหมา","ไอ้ลูกหมา","ควยมึง",
    "มึงสัสจริง","อีคนโง่","มึงไร้ค่า","ไอ้ควาย","กากสัส","สัดเหี้ย"
]
COOLDOWN = 1
stop_sending = False
last_sent = {}

def is_server_owner(interaction): return interaction.user.id == OWNER_ID or (interaction.guild and interaction.guild.owner_id == interaction.user.id)
async def owner_only_check(interaction): 
    if not is_server_owner(interaction):
        await interaction.response.send_message("❌ คำสั่งนี้ใช้ได้เฉพาะเจ้าของเซิร์ฟเวอร์เท่านั้น!", ephemeral=True)
        return False
    return True

async def send_ngl(bot, username, amount, speed, message=None, is_random=True):
    global stop_sending, last_sent
    now = asyncio.get_event_loop().time()
    if username in last_sent and now - last_sent[username] < COOLDOWN:
        channel = bot.get_channel(CHANNEL_STATUS_ID)
        await channel.send(f"❌ {username} ต้องรออีก {round(COOLDOWN - (now - last_sent[username]))} วินาที")
        return
    stop_sending = False
    sent, fail = 0, 0
    channel = bot.get_channel(CHANNEL_STATUS_ID)
    status_message = await channel.send(f"🚀 กำลังยิง {username}...")
    for i in range(min(amount,200)):
        if stop_sending:
            await status_message.edit(content=f"⏹ หยุดยิงกลางทาง! ✅ สำเร็จ: {sent} ❌ ล้มเหลว: {fail}")
            break
        try:
            text = message if not is_random else random.choice(RANDOM_MESSAGES)
            payload = {"username": username,"question": text,"deviceId": str(uuid.uuid4())}
            headers = {"User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS {random.randint(14,17)}_0 like Mac OS X)", "Content-Type":"application/json"}
            res = requests.post("https://ngl.link/api/submit", json=payload, headers=headers)
            if res.status_code==200: sent+=1
            else: fail+=1
            await status_message.edit(content=f"🚀 ยิง {username}...\n✅ สำเร็จ: {sent}\n❌ ล้มเหลว: {fail}\nข้อความล่าสุด: {text}")
            await asyncio.sleep(speed*random.uniform(0.8,1.2))
        except Exception as e:
            fail += 1
            await status_message.edit(content=f"🚀 ยิง {username}...\n✅ สำเร็จ: {sent}\n❌ ล้มเหลว: {fail}\nException: {e}")
    await status_message.edit(content=f"✅ ส่งเสร็จแล้ว!\n✅ สำเร็จ: {sent}\n❌ ล้มเหลว: {fail}")
    last_sent[username] = asyncio.get_event_loop().time()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="bot-status", description="ตรวจสอบสถานะบอทและเซิร์ฟเวอร์")
async def bot_status(interaction: discord.Interaction):
    if not await owner_only_check(interaction): return
    uptime = datetime.utcnow() - bot_start_time
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    embed = discord.Embed(title="🤖 สถานะบอทและเซิร์ฟเวอร์", color=discord.Color.green())
    embed.add_field(name="🟢 สถานะบอท", value="ออนไลน์", inline=True)
    embed.add_field(name="⏱️ Uptime", value=str(uptime).split('.')[0], inline=True)
    embed.add_field(name="🏓 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="💻 CPU", value=f"{cpu_percent}%", inline=True)
    embed.add_field(name="🧠 RAM", value=f"{memory.percent}% ({memory.used // 1024**3}GB/{memory.total // 1024**3}GB)", inline=True)
    embed.add_field(name="🖥️ OS", value=platform.system(), inline=True)
    embed.add_field(name="🐍 Python", value=platform.python_version(), inline=True)
    embed.add_field(name="🔧 Discord.py", value=discord.__version__, inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="restart-bot", description="รีสตาร์ทบอทและเซอร์วิส")
async def restart_bot(interaction: discord.Interaction):
    if not await owner_only_check(interaction): return
    await interaction.response.send_message(embed=discord.Embed(title="🔄 กำลังรีสตาร์ทบอท", color=discord.Color.orange()), ephemeral=True)
    await asyncio.sleep(2)
    os._exit(0)

@tasks.loop(minutes=5)
async def keep_alive_task():
    try:
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f"📊 24/7 | Uptime: {(datetime.utcnow() - bot_start_time).days}d"),
            status=discord.Status.online
        )
    except Exception as e:
        logger.error(f"Keep-alive task error: {e}")

class NGLModal(ui.Modal, title="ยิง NGL ระบบ UI"):
    username_input = ui.TextInput(label="ชื่อผู้ใช้ NGL", placeholder="example123")
    amount_input = ui.TextInput(label="จำนวนครั้ง (1-200)", default="10")
    speed_input = ui.TextInput(label="ความเร็วส่งข้อความ (วินาที)", default="0.5")
    mode_input = ui.TextInput(label="โหมดข้อความ (1 สุ่ม, 2 กำหนดเอง)")
    custom_message_input = ui.TextInput(label="ข้อความเอง (ถ้าเลือก 2)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        username = self.username_input.value.strip()
        try: amount=int(self.amount_input.value.strip()); amount=max(1,min(200,amount))
        except: amount=10
        try: speed=float(self.speed_input.value.strip()); speed=max(0.1,speed)
        except: speed=0.5
        mode = self.mode_input.value.strip()
        message = self.custom_message_input.value.strip() if mode=="2" else None
        is_random = mode=="1"
        await interaction.response.send_message(f"🟢 เริ่มยิง {username}...", ephemeral=True)
        await send_ngl(bot, username, amount, speed, message, is_random)

class NGLView(ui.View):
    @ui.button(label="ยิง NGL", style=discord.ButtonStyle.green)
    async def start_ngl(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NGLModal())
    @ui.button(label="หยุดยิง", style=discord.ButtonStyle.red)
    async def stop_ngl(self, interaction: discord.Interaction, button: discord.ui.Button):
        global stop_sending
        stop_sending = True
        await interaction.response.send_message("⏹️ สั่งหยุดยิงเรียบร้อย", ephemeral=True)

@bot.event
async def on_ready():
    try: await bot.tree.sync()
    except Exception as e: print(f"❌ Slash Commands Sync Error: {e}")
    if not keep_alive_task.is_running(): keep_alive_task.start()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="📊 เซิร์ฟเวอร์ออนไลน์ 24/7"), status=discord.Status.online)
    ui_channel = bot.get_channel(CHANNEL_UI_ID)
    if ui_channel and isinstance(ui_channel, TextChannel):
        async for msg in ui_channel.history(limit=10): await msg.delete()
        await ui_channel.send("🔘 ปุ่มกดยิง NGL:", view=NGLView())

app = Flask('')

@app.route('/')
def home():
    return "Server is running!"

def run_flask():
    app.run(host='0.0.0.0', port=5000)

threading.Thread(target=run_flask).start()
if TOKEN: bot.run(TOKEN)
else: print("❌ ไม่พบ DISCORD_TOKEN ในตัวแปรสภาพแวดล้อม!")
