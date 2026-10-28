import asyncio
import logging
import sys
import discord
from discord.ext import commands

import config

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("backup_bot")

# Cấu hình Intents
# Lưu ý: Bật Server Members Intent trên Discord Developer Portal để đọc đầy đủ danh sách thành viên nếu cần
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True  # Cho prefix commands

class AntiNukeBackupBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=config.PREFIX,
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Nạp các cogs
        initial_extensions = [
            "cogs.backup_commands",
            "cogs.auto_backup"
        ]
        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Đã nạp Cog thành công: {ext}")
            except Exception as e:
                logger.error(f"Thất bại khi nạp Cog {ext}: {e}")

        # Đồng bộ Slash Commands với Discord
        try:
            logger.info("Đang đồng bộ Slash Commands...")
            synced = await self.tree.sync()
            logger.info(f"Đã đồng bộ thành công {len(synced)} lệnh Slash!")
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ Slash commands: {e}")

    async def on_ready(self):
        logger.info(f"=== Bot đã sẵn sàng! Đăng nhập với tên: {self.user} (ID: {self.user.id}) ===")
        logger.info(f"Đang hoạt động trên {len(self.guilds)} server.")

        # Cài đặt status cho Bot
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"Bảo vệ {len(self.guilds)} Server | /backup create"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CheckFailure):
            # Lỗi check quyền đã được thông báo trong decorator
            return
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply(f"❌ Thiếu đối số cần thiết: `{error.param.name}`", ephemeral=True)
        
        logger.error(f"Lỗi lệnh '{ctx.command}': {error}")
        await ctx.reply(f"❌ Đã xảy ra lỗi: `{str(error)}`", ephemeral=True)

async def main():
    if not config.TOKEN:
        logger.critical("CHƯA CẤU HÌNH DISCORD_TOKEN! Vui lòng cấu hình file .env trước khi chạy bot.")
        sys.exit(1)

    bot = AntiNukeBackupBot()
    async with bot:
        await bot.start(config.TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot đã dừng bởi người dùng (Ctrl+C).")
