import discord
from discord import ui, app_commands
from discord.ext import commands, tasks
from discord import TextChannel
import random, uuid, requests, asyncio, time, threading, os, platform, psutil
from flask import Flask
from datetime import datetime, timedelta
import aiohttp
import hashlib
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box
from rich.table import Table
from rich.panel import Panel
from humanize import naturaltime
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from cryptography.fernet import Fernet
from loguru import logger
import httpx
# ---------------- CONFIG ----------------
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1405933240212258816
OWNER_ID = 1065954764019470420

# ---------------- Channel ล่าสุด ----------------
ALERT_CHANNEL_ID = 1415593892585406525
CHANNEL_UI_ID = 1415555699454246985
CHANNEL_STATUS_ID = 1415345695069835267
CHANNEL_GUIDE_ID = 1415555569753788426
STATUS_DASHBOARD_ID = 1417378674537267333  # สถานะเซิร์ฟเวอร์

# ---------------- ตัวแปรสำหรับ Bot Management ----------------
bot_start_time = datetime.utcnow()
console = Console()

# ---------------- Security และ Token Protection ----------------
BOT_FINGERPRINT = hashlib.sha256(f"{OWNER_ID}_{GUILD_ID}_NEKTRI_BOT".encode()).hexdigest()[:16]
AUTHORIZED_INSTANCE = True
LAST_HEARTBEAT = datetime.utcnow()

# ---------------- Professional Logging ----------------
logger.remove()  # ลบ default handler
logger.add("logs/bot.log", rotation="1 MB", retention="7 days", level="INFO")
logger.add("logs/error.log", rotation="1 MB", retention="7 days", level="ERROR")
logger.info(f"Bot initializing with fingerprint: {BOT_FINGERPRINT}")

# ---------------- Status Tracking ----------------
active_ngl_sessions = {}
server_stats = {
    'uptime_start': bot_start_time,
    'commands_executed': 0,
    'messages_processed': 0,
    'errors_count': 0,
    'last_restart': None
}

# ---------------- ห้องสำคัญไม่ให้ลบ ----------------
KEEP_CHANNELS = [
    ALERT_CHANNEL_ID,
    CHANNEL_UI_ID,
    CHANNEL_STATUS_ID,
    CHANNEL_GUIDE_ID
]

# ---------------- ข้อความสุ่ม ----------------
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

COOLDOWN = 1  # 1 วินาที
stop_sending = False
last_sent = {}

# ---------------- Auto-Moderation Channels ----------------
PROTECTED_CHANNELS = [
    ALERT_CHANNEL_ID,
    CHANNEL_UI_ID, 
    CHANNEL_STATUS_ID,
    CHANNEL_GUIDE_ID,
    STATUS_DASHBOARD_ID
]

# ช่องที่อนุญาตให้พูดคุยได้ (ไม่ลบข้อความ)
CHAT_ALLOWED_CHANNELS = [
    # เพิ่ม channel IDs ที่อนุญาตให้คุยทั่วไปตรงนี้
    # 1234567890123456789  # ตัวอย่าง Chat Channel
]

# ---------------- Helpers ----------------
def random_device_id():
    return str(uuid.uuid4())

def random_user_agent():
    return f"Mozilla/5.0 (iPhone; CPU iPhone OS {random.randint(14,17)}_0 like Mac OS X)"

async def alert_server(bot, message: str):
    try:
        channel = bot.get_channel(ALERT_CHANNEL_ID)
        if channel:
            await channel.send(f"⚠️ [แจ้งเตือนระบบ] {message}")
    except Exception as e:
        print(f"❌ ไม่สามารถส่งแจ้งเตือนได้: {e}")

# ---------------- NGL Sending ----------------
async def send_ngl(bot, username, amount, speed, message=None, is_random=True):
    global stop_sending, last_sent
    now = time.time()
    if username in last_sent and now - last_sent[username] < COOLDOWN:
        channel = bot.get_channel(CHANNEL_STATUS_ID)
        await channel.send(f"❌ {username} ต้องรออีก {round(COOLDOWN - (now - last_sent[username]))} วินาที")
        return

    stop_sending = False
    sent, fail = 0, 0
    start_time = time.time()
    channel = bot.get_channel(CHANNEL_STATUS_ID)

    # ลบข้อความเก่าก่อนเริ่มส่งใหม่
    async for msg in channel.history(limit=50):
        if msg.id not in KEEP_CHANNELS:
            await msg.delete()

    status_message = await channel.send(f"🚀 กำลังยิง {username}...")

    for i in range(min(amount,200)):
        if stop_sending:
            await status_message.edit(content=f"⏹ หยุดยิงกลางทาง! ✅ สำเร็จ: {sent} ❌ ล้มเหลว: {fail}")
            break
        try:
            text = message if not is_random else random.choice(RANDOM_MESSAGES)
            payload = {"username": username,"question": text,"deviceId": random_device_id()}
            headers = {"User-Agent": random_user_agent(),"Content-Type":"application/json"}
            res = requests.post("https://ngl.link/api/submit", json=payload, headers=headers)
            if res.status_code==200: sent+=1
            else: fail+=1
            await status_message.edit(content=f"🚀 ยิง {username}...\n✅ สำเร็จ: {sent}\n❌ ล้มเหลว: {fail}\nข้อความล่าสุด: {text}")
            await asyncio.sleep(speed*random.uniform(0.8,1.2))
        except Exception as e:
            fail+=1
            await status_message.edit(content=f"🚀 ยิง {username}...\n✅ สำเร็จ: {sent}\n❌ ล้มเหลว: {fail}\nException: {e}")
            await alert_server(bot, f"เกิดข้อผิดพลาดขณะยิง NGL: {e}")

    duration = round(time.time()-start_time,2)
    await status_message.edit(content=f"✅ ส่งเสร็จแล้ว!\n✅ สำเร็จ: {sent}\n❌ ล้มเหลว: {fail}\n⏱ เวลา: {duration} วินาที")
    channel_success = bot.get_channel(CHANNEL_GUIDE_ID)
    if channel_success:
        await channel_success.send(f"📢 การยิงไปยัง {username} เสร็จเรียบร้อย ใช้เวลา {duration} วินาที ✅")
    last_sent[username] = time.time()

# ---------------- ฟังก์ชันตรวจสอบสิทธิ์ ----------------
def is_server_owner(interaction: discord.Interaction) -> bool:
    """ตรวจสอบว่าเป็นเจ้าของเซิร์ฟเวอร์หรือไม่ (เฉพาะเจ้าของเซิร์ฟเวอร์เท่านั้น)"""
    # ตรวจสอบ OWNER_ID ที่กำหนดไว้
    if interaction.user.id == OWNER_ID:
        return True
    
    # ตรวจสอบว่าเป็นเจ้าของเซิร์ฟเวอร์จริง
    if interaction.guild and interaction.guild.owner_id == interaction.user.id:
        return True
    
    return False

async def owner_only_check(interaction: discord.Interaction) -> bool:
    """Decorator check สำหรับคำสั่งเฉพาะเจ้าของ"""
    if not is_server_owner(interaction):
        await interaction.response.send_message("❌ คำสั่งนี้ใช้ได้เฉพาะเจ้าของเซิร์ฟเวอร์เท่านั้น!", ephemeral=True)
        return False
    return True

# ---------------- Discord Bot ----------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- Slash Commands สำหรับจัดการบอท ----------------
@bot.tree.command(name="bot-status", description="ตรวจสอบสถานะบอทและเซิร์ฟเวอร์")
async def bot_status(interaction: discord.Interaction):
    if not await owner_only_check(interaction):
        return
    
    uptime = datetime.utcnow() - bot_start_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # ข้อมูลระบบ
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    embed = discord.Embed(
        title="🤖 สถานะบอทและเซิร์ฟเวอร์",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(name="🟢 สถานะบอท", value="ออนไลน์", inline=True)
    embed.add_field(name="⏱️ Uptime", value=f"{days}d {hours}h {minutes}m {seconds}s", inline=True)
    embed.add_field(name="🏓 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    
    embed.add_field(name="💻 CPU", value=f"{cpu_percent}%", inline=True)
    embed.add_field(name="🧠 RAM", value=f"{memory.percent}% ({memory.used // 1024**3}GB/{memory.total // 1024**3}GB)", inline=True)
    embed.add_field(name="💾 Disk", value=f"{disk.percent}% ({disk.used // 1024**3}GB/{disk.total // 1024**3}GB)", inline=True)
    
    embed.add_field(name="🖥️ OS", value=platform.system(), inline=True)
    embed.add_field(name="🐍 Python", value=platform.python_version(), inline=True)
    embed.add_field(name="🔧 Discord.py", value=discord.__version__, inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="force-online", description="บังคับให้บอทออนไลน์ตลอดเวลา")
async def force_online(interaction: discord.Interaction):
    if not await owner_only_check(interaction):
        return
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="📊 เซิร์ฟเวอร์ออนไลน์ 24/7"
        ),
        status=discord.Status.online
    )
    
    embed = discord.Embed(
        title="✅ บังคับบอทออนไลน์สำเร็จ",
        description="บอทจะออนไลน์ตลอดเวลาและแสดงสถานะการเฝ้าระวัง",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="server-check", description="ตรวจสอบการเชื่อมต่อเซิร์ฟเวอร์")
async def server_check(interaction: discord.Interaction, url: str = None):
    if not await owner_only_check(interaction):
        return
    
    await interaction.response.defer()
    
    # ถ้าไม่ใส่ URL จะเช็ค Flask server ของตัวเอง
    if url is None:
        url = "http://localhost:5000"
    
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    try:
        start_time = asyncio.get_event_loop().time()
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                response_time = round((asyncio.get_event_loop().time() - start_time) * 1000)
                
                status_emoji = "🟢" if response.status == 200 else "🟡"
                status_color = discord.Color.green() if response.status == 200 else discord.Color.yellow()
                
                embed = discord.Embed(
                    title=f"{status_emoji} สถานะเซิร์ฟเวอร์",
                    color=status_color,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="🌐 URL", value=url, inline=False)
                embed.add_field(name="📊 Status Code", value=response.status, inline=True)
                embed.add_field(name="⚡ Response Time", value=f"{response_time}ms", inline=True)
                
    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="🔴 เซิร์ฟเวอร์ไม่ตอบสนอง",
            description="Request timeout - เซิร์ฟเวอร์ใช้เวลานานเกินไป",
            color=discord.Color.red()
        )
    except Exception as e:
        embed = discord.Embed(
            title="🔴 เกิดข้อผิดพลาด",
            description=f"Error: {str(e)}",
            color=discord.Color.red()
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="restart-bot", description="รีสตาร์ทบอทและเซอร์วิส")
async def restart_bot(interaction: discord.Interaction):
    if not await owner_only_check(interaction):
        return
    
    embed = discord.Embed(
        title="🔄 กำลังรีสตาร์ทบอท",
        description="บอทจะรีสตาร์ทใน 5 วินาที...",
        color=discord.Color.orange()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # ส่งข้อความแจ้งเตือนไปยัง status channel
    status_channel = bot.get_channel(STATUS_DASHBOARD_ID)
    if status_channel and isinstance(status_channel, TextChannel):
        alert_embed = discord.Embed(
            title="🔄 รีสตาร์ทระบบ",
            description=f"Admin {interaction.user.mention} สั่งรีสตาร์ทบอท - รอสักครู่...",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        await status_channel.send(embed=alert_embed)
    
    # รีสตาร์ทบอทหลังจาก 5 วินาที
    await asyncio.sleep(5)
    import os
    os._exit(0)  # ปิดบอทเพื่อให้ workflow supervisor รีสตาร์ทใหม่

# ---------------- Auto Keep-Alive และ Status Monitoring ----------------
@tasks.loop(minutes=5)  # ทุก 5 นาที
async def keep_alive_task():
    """ฟังก์ชัน keep-alive เพื่อให้บอทออนไลน์ตลอดเวลา"""
    try:
        # อัพเดทสถานะบอท
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"📊 เซิร์ฟเวอร์ 24/7 | Uptime: {(datetime.utcnow() - bot_start_time).days}d"
            ),
            status=discord.Status.online
        )
        
        # ส่งสถานะไปยัง status channel
        status_channel = bot.get_channel(STATUS_DASHBOARD_ID)
        if status_channel and isinstance(status_channel, TextChannel):
            # คำนวณ uptime
            uptime = datetime.utcnow() - bot_start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            # ข้อมูลระบบ
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # สร้าง embed สถานะ
            embed = discord.Embed(
                title="🟢 สถานะเซิร์ฟเวอร์ - ออนไลน์",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="⏱️ Uptime", value=f"{days}d {hours}h {minutes}m", inline=True)
            embed.add_field(name="🏓 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
            embed.add_field(name="💻 CPU", value=f"{cpu_percent}%", inline=True)
            embed.add_field(name="🧠 RAM", value=f"{memory.percent}%", inline=True)
            embed.add_field(name="🔋 Status", value="🟢 ปกติ", inline=True)
            embed.add_field(name="📡 Connected", value="✅ เชื่อมต่อแล้ว", inline=True)
            
            embed.set_footer(text="อัพเดทอัตโนมัติทุก 5 นาที")
            
            # ลบข้อความเก่าและส่งใหม่ (เก็บแค่ข้อความล่าสุด)
            async for message in status_channel.history(limit=10):
                if message.author == bot.user and "สถานะเซิร์ฟเวอร์" in (message.embeds[0].title if message.embeds else ""):
                    await message.delete()
                    break
            
            await status_channel.send(embed=embed)
            
    except Exception as e:
        print(f"❌ Keep-alive task error: {e}")

@tasks.loop(minutes=1)  # ทุก 1 นาที
async def health_check():
    """ตรวจสอบสุขภาพเซิร์ฟเวอร์และส่งแจ้งเตือนหากมีปัญหา"""
    try:
        # ตรวจสอบ CPU และ Memory
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # แจ้งเตือนหาก CPU หรือ Memory สูงเกินไป
        if cpu_percent > 80 or memory.percent > 85:
            alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
            if alert_channel and isinstance(alert_channel, TextChannel):
                embed = discord.Embed(
                    title="⚠️ แจ้งเตือนประสิทธิภาพระบบ",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                
                if cpu_percent > 80:
                    embed.add_field(name="🔥 CPU สูง", value=f"{cpu_percent}%", inline=True)
                
                if memory.percent > 85:
                    embed.add_field(name="🧠 RAM สูง", value=f"{memory.percent}%", inline=True)
                
                embed.set_footer(text="กรุณาตรวจสอบระบบ")
                await alert_channel.send(embed=embed)
                
    except Exception as e:
        print(f"❌ Health check error: {e}")

@keep_alive_task.before_loop
async def before_keep_alive():
    await bot.wait_until_ready()

@health_check.before_loop  
async def before_health_check():
    await bot.wait_until_ready()

# ---------------- Modal ----------------
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

# ---------------- View ----------------
class NGLView(ui.View):
    @ui.button(label="ยิง NGL", style=discord.ButtonStyle.green)
    async def start_ngl(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NGLModal())

    @ui.button(label="หยุดยิง", style=discord.ButtonStyle.red)
    async def stop_ngl(self, interaction: discord.Interaction, button: discord.ui.Button):
        global stop_sending
        stop_sending = True
        await interaction.response.send_message("⏹️ สั่งหยุดยิงเรียบร้อย", ephemeral=True)

# ---------------- on_ready ----------------
@bot.event
async def on_ready():
    print(f"Bot พร้อมใช้งาน: {bot.user}")
    try: 
        await bot.tree.sync()
        print("Slash Commands Synced ✅")
    except Exception as e: 
        print(f"❌ Slash Commands Sync Error: {e}")

    # เริ่ม keep-alive และ monitoring tasks
    if not keep_alive_task.is_running():
        keep_alive_task.start()
        print("✅ Keep-Alive Task เริ่มทำงาน")
    
    if not health_check.is_running():
        health_check.start()
        print("✅ Health Check Task เริ่มทำงาน")
    
    # ตั้งสถานะเริ่มต้น
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="📊 เซิร์ฟเวอร์ออนไลน์ 24/7"
        ),
        status=discord.Status.online
    )

    # ลบข้อความเก่าในช่อง UI ก่อนส่งใหม่
    ui_channel = bot.get_channel(CHANNEL_UI_ID)
    if ui_channel and isinstance(ui_channel, TextChannel):
        async for msg in ui_channel.history(limit=50):
            if msg.id not in KEEP_CHANNELS:
                await msg.delete()
        await ui_channel.send("🔘 ปุ่มกดยิง NGL:", view=NGLView())
    
    # ส่งข้อความแจ้งเตือนการเริ่มทำงาน
    alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
    if alert_channel and isinstance(alert_channel, TextChannel):
        startup_embed = discord.Embed(
            title="🟢 บอทเริ่มทำงาน",
            description="บอทพร้อมใช้งานและระบบ Keep-Alive ทำงานแล้ว",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        await alert_channel.send(embed=startup_embed)

# ---------------- Keep-Alive (Flask) ----------------
app = Flask('')

@app.route('/')
def home():
    return "Server is running!"

def run_flask():
    app.run(host='0.0.0.0', port=5000)

# ---------------- Run Bot + Flask 24/7 ----------------
threading.Thread(target=run_flask).start()  # รัน Flask แบบ background
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ไม่พบ DISCORD_TOKEN ในตัวแปรสภาพแวดล้อม!")
