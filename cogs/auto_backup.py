import logging
from datetime import datetime
import discord
from discord.ext import commands, tasks

import config
from utils.backup_manager import create_backup_data, save_backup_file

logger = logging.getLogger("backup_bot.cogs.auto_backup")

class AutoBackupCog(commands.Cog):
    """Cog tự động sao lưu server định kỳ để phòng ngừa sự cố bất ngờ."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if config.AUTO_BACKUP_ENABLED:
            self.auto_backup_loop.change_interval(hours=config.AUTO_BACKUP_INTERVAL_HOURS)
            self.auto_backup_loop.start()
            logger.info(f"Đã kích hoạt Auto-Backup mỗi {config.AUTO_BACKUP_INTERVAL_HOURS} giờ.")

    def cog_unload(self):
        if self.auto_backup_loop.is_running():
            self.auto_backup_loop.cancel()

    @tasks.loop(hours=24)
    async def auto_backup_loop(self):
        await self.bot.wait_until_ready()
        logger.info("Bắt đầu chu kỳ tự động sao lưu định kỳ...")

        for guild in self.bot.guilds:
            try:
                # Tạo backup tự động
                data = await create_backup_data(
                    guild=guild,
                    author_id=self.bot.user.id,
                    author_name="AutoBackup-System",
                    note=f"Tự động sao lưu định kỳ ({datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')})"
                )
                save_backup_file(data)
                logger.info(f"Đã sao lưu tự động thành công cho server: {guild.name} ({guild.id})")
            except Exception as e:
                logger.error(f"Lỗi khi tự động sao lưu server {guild.name}: {e}")

    @auto_backup_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoBackupCog(bot))
