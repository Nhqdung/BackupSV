from typing import Union
import discord
from discord.ext import commands
import config

def is_authorized(user: Union[discord.User, discord.Member], guild: discord.Guild) -> bool:
    """
    Kiểm tra xem người dùng có quyền thực hiện backup/restore không.
    Chỉ cho phép:
    1. Chủ Server (Server Owner)
    2. Bot Owner trong danh sách config.OWNER_IDS
    LƯU Ý: Không cho phép Admin thông thường để tránh trường hợp Admin bị hack token nuke server.
    """
    if user.id in config.OWNER_IDS:
        return True
    if guild and guild.owner_id == user.id:
        return True
    return False

def check_authorized():
    """Custom check decorator cho prefix commands."""
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            await ctx.reply("❌ Lệnh này chỉ có thể sử dụng bên trong Server Discord!", ephemeral=True)
            return False
        if not is_authorized(ctx.author, ctx.guild):
            await ctx.reply(
                "⛔ **Truy cập bị từ chối!**\n"
                "Vì lý do bảo mật chống Raid/Nuke, chỉ **Chủ Server (Server Owner)** hoặc **Bot Owner** được cấu hình mới có quyền sử dụng chức năng Backup/Restore.",
                ephemeral=True
            )
            return False
        return True
    return commands.check(predicate)
