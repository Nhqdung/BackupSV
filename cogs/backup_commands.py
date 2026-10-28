import io
import json
import logging
from datetime import datetime
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from utils.security import is_authorized, check_authorized
from utils.backup_manager import (
    create_backup_data,
    save_backup_file,
    load_backup_data,
    list_backups_for_guild,
    delete_backup_file,
    get_guild_backup_dir
)
from utils.restorer import restore_guild, RestoreError

logger = logging.getLogger("backup_bot.cogs.backup")

class ConfirmRestoreView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=60.0)
        self.author_id = author_id
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Bạn không phải là người yêu cầu khôi phục này!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Xác nhận khôi phục (WIPE & RESTORE)", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="⏳ **Đang tiến hành khôi phục server... Vui lòng không thao tác gì trên server!**", view=self)

    @discord.ui.button(label="Hủy bỏ", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🛑 **Đã hủy thao tác khôi phục.**", view=self)

class BackupCommands(commands.Cog):
    """Cog xử lý toàn bộ lệnh tạo, xem và khôi phục Backup."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Nhóm lệnh Slash /backup
    backup_group = app_commands.Group(name="backup", description="Hệ thống sao lưu và khôi phục server chống Raid/Nuke")

    # ==========================================
    # SLASH COMMAND: /backup create
    # ==========================================
    @backup_group.command(name="create", description="Tạo một bản sao lưu mới cho server")
    @app_commands.describe(note="Ghi chú cho bản sao lưu này (ví dụ: Trước khi tuyển Admin mới)")
    async def slash_create(self, interaction: discord.Interaction, note: Optional[str] = ""):
        if not is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message(
                "⛔ **Chỉ Chủ Server (Server Owner) hoặc Bot Owner mới có quyền dùng chức năng này!**",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=False)
        try:
            data = await create_backup_data(
                guild=interaction.guild,
                author_id=interaction.user.id,
                author_name=interaction.user.name,
                note=note or ""
            )
            file_path = save_backup_file(data)

            embed = discord.Embed(
                title="✅ Đã tạo bản sao lưu thành công!",
                description=f"Server: **{interaction.guild.name}**\nMã Backup: `{data['backup_id']}`",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Ghi chú", value=note if note else "Không có", inline=False)
            embed.add_field(name="Roles", value=str(data["stats"]["role_count"]), inline=True)
            embed.add_field(name="Danh mục", value=str(data["stats"]["category_count"]), inline=True)
            embed.add_field(name="Kênh", value=str(data["stats"]["channel_count"]), inline=True)
            embed.set_footer(text=f"Kích thước file: {file_path.stat().st_size / 1024:.1f} KB")

            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.exception("Lỗi khi tạo backup:")
            await interaction.followup.send(f"❌ Đã xảy ra lỗi khi tạo backup: `{str(e)}`")

    # ==========================================
    # SLASH COMMAND: /backup list
    # ==========================================
    @backup_group.command(name="list", description="Xem danh sách các bản sao lưu hiện có của server")
    async def slash_list(self, interaction: discord.Interaction):
        if not is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message(
                "⛔ **Chỉ Chủ Server (Server Owner) hoặc Bot Owner mới có quyền dùng chức năng này!**",
                ephemeral=True
            )

        backups = list_backups_for_guild(interaction.guild.id)
        if not backups:
            return await interaction.response.send_message("ℹ️ Hiện chưa có bản sao lưu nào cho server này.", ephemeral=True)

        embed = discord.Embed(
            title=f"📦 Danh sách bản sao lưu ({len(backups)})",
            description=f"Server: **{interaction.guild.name}**\nDùng lệnh `/backup load <mã_backup>` để khôi phục.",
            color=discord.Color.blue()
        )

        for b in backups[:10]: # Hiển thị tối đa 10 bản gần nhất
            created_dt = datetime.fromtimestamp(b["created_timestamp"]).strftime("%d/%m/%Y %H:%M:%S")
            stats = b.get("stats", {})
            val = (
                f"🕒 Thời gian: **{created_dt}**\n"
                f"👤 Tạo bởi: {b.get('created_by', 'N/A')}\n"
                f"📝 Ghi chú: {b.get('note') or 'Không có'}\n"
                f"📊 {stats.get('role_count', 0)} roles | {stats.get('channel_count', 0)} kênh"
            )
            embed.add_field(name=f"ID: `{b['backup_id']}`", value=val, inline=False)

        await interaction.response.send_message(embed=embed)

    # ==========================================
    # SLASH COMMAND: /backup load
    # ==========================================
    @backup_group.command(name="load", description="Khôi phục server về trạng thái của bản sao lưu đã chọn")
    @app_commands.describe(backup_id="Mã bản sao lưu cần khôi phục")
    async def slash_load(self, interaction: discord.Interaction, backup_id: str):
        if not is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message(
                "⛔ **Chỉ Chủ Server (Server Owner) hoặc Bot Owner mới có quyền dùng chức năng này!**",
                ephemeral=True
            )

        backup_data = load_backup_data(backup_id, interaction.guild.id)
        if not backup_data:
            return await interaction.response.send_message(
                f"❌ Không tìm thấy bản sao lưu có mã `{backup_id}`!",
                ephemeral=True
            )

        # Cảnh báo trước khi wipe & restore
        embed = discord.Embed(
            title="⚠️ CẢNH BÁO QUAN TRỌNG: KHÔI PHỤC SERVER",
            description=(
                f"Bạn đang chuẩn bị khôi phục server về bản backup: `{backup_id}`\n\n"
                "**Thao tác này sẽ:**\n"
                "1. Xóa các kênh và role hiện tại (trừ kênh này và quyền hạn bot).\n"
                "2. Tạo lại cấu trúc Categories, Kênh text/voice, Roles và phân quyền chuẩn xác theo bản sao lưu.\n"
                "3. Khôi phục tên và cài đặt của server.\n\n"
                "**Bạn có chắc chắn 100% muốn tiếp tục?**"
            ),
            color=discord.Color.red()
        )

        view = ConfirmRestoreView(author_id=interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()

        if view.value is not True:
            return

        # Bắt đầu khôi phục
        progress_msg = await interaction.channel.send("🚀 Bắt đầu quá trình khôi phục server...")

        async def update_progress(status: str, percent: int):
            bar_len = 20
            filled = int(bar_len * (percent / 100.0))
            bar = "█" * filled + "░" * (bar_len - filled)
            try:
                await progress_msg.edit(content=f"**Tiến trình khôi phục: [{bar}] {percent}%**\n_{status}_")
            except Exception:
                pass

        try:
            summary = await restore_guild(
                guild=interaction.guild,
                backup_data=backup_data,
                clear_existing=True,
                current_channel_id=interaction.channel.id,
                progress_callback=update_progress
            )

            res_embed = discord.Embed(
                title="🎉 Khôi phục Server thành công!",
                description="Server của bạn đã được tái thiết lập theo đúng bản sao lưu an toàn.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            res_embed.add_field(name="Roles đã tạo", value=str(summary["roles_created"]), inline=True)
            res_embed.add_field(name="Danh mục đã tạo", value=str(summary["categories_created"]), inline=True)
            res_embed.add_field(name="Kênh đã tạo", value=str(summary["channels_created"]), inline=True)
            if summary["errors"]:
                res_embed.add_field(name="Cảnh báo", value=f"Có {len(summary['errors'])} lỗi nhỏ (xem console log).", inline=False)

            await interaction.channel.send(embed=res_embed)
        except Exception as e:
            logger.exception("Lỗi khi khôi phục:")
            await interaction.channel.send(f"❌ Quá trình khôi phục gặp sự cố: `{str(e)}`")

    # ==========================================
    # SLASH COMMAND: /backup download
    # ==========================================
    @backup_group.command(name="download", description="Tải file backup JSON về máy tính cá nhân để lưu trữ an toàn")
    @app_commands.describe(backup_id="Mã bản sao lưu cần tải")
    async def slash_download(self, interaction: discord.Interaction, backup_id: str):
        if not is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message(
                "⛔ **Chỉ Chủ Server (Server Owner) hoặc Bot Owner mới có quyền dùng chức năng này!**",
                ephemeral=True
            )

        backup_data = load_backup_data(backup_id, interaction.guild.id)
        if not backup_data:
            return await interaction.response.send_message(f"❌ Không tìm thấy mã `{backup_id}`", ephemeral=True)

        json_str = json.dumps(backup_data, ensure_ascii=False, indent=2)
        file = discord.File(io.BytesIO(json_str.encode("utf-8")), filename=f"backup_{backup_id}.json")
        await interaction.response.send_message(
            content=f"📥 Đây là file backup offline của bạn (`{backup_id}.json`). Hãy lưu trữ ở nơi an toàn!",
            file=file,
            ephemeral=True
        )

    # ==========================================
    # SLASH COMMAND: /backup delete
    # ==========================================
    @backup_group.command(name="delete", description="Xóa một bản sao lưu cũ không còn dùng")
    @app_commands.describe(backup_id="Mã bản sao lưu cần xóa")
    async def slash_delete(self, interaction: discord.Interaction, backup_id: str):
        if not is_authorized(interaction.user, interaction.guild):
            return await interaction.response.send_message(
                "⛔ **Chỉ Chủ Server (Server Owner) hoặc Bot Owner mới có quyền dùng chức năng này!**",
                ephemeral=True
            )

        success = delete_backup_file(backup_id, interaction.guild.id)
        if success:
            await interaction.response.send_message(f"🗑️ Đã xóa thành công bản sao lưu `{backup_id}`.")
        else:
            await interaction.response.send_message(f"❌ Không tìm thấy bản sao lưu `{backup_id}` để xóa.", ephemeral=True)

    # ==========================================
    # PREFIX COMMANDS (Lệnh dự phòng khẩn cấp)
    # ==========================================
    @commands.group(name="backup", invoke_without_command=True)
    @check_authorized()
    async def prefix_backup(self, ctx: commands.Context):
        prefix = ctx.prefix
        embed = discord.Embed(
            title="🛡️ Hướng dẫn lệnh Backup Server (Prefix)",
            description=(
                f"`{prefix}backup create [ghi chú]` - Tạo bản sao lưu mới\n"
                f"`{prefix}backup list` - Danh sách bản sao lưu\n"
                f"`{prefix}backup load <mã>` - Khôi phục server từ bản sao lưu\n"
                f"`{prefix}backup download <mã>` - Tải file JSON về máy\n"
                f"`{prefix}backup delete <mã>` - Xóa bản sao lưu\n"
            ),
            color=discord.Color.blurple()
        )
        await ctx.reply(embed=embed)

    @prefix_backup.command(name="create")
    @check_authorized()
    async def prefix_create(self, ctx: commands.Context, *, note: str = ""):
        msg = await ctx.reply("⏳ Đang thu thập dữ liệu và tạo bản sao lưu...")
        try:
            data = await create_backup_data(
                guild=ctx.guild,
                author_id=ctx.author.id,
                author_name=ctx.author.name,
                note=note
            )
            file_path = save_backup_file(data)
            await msg.edit(content=f"✅ Đã tạo thành công backup `{data['backup_id']}`! ({data['stats']['channel_count']} kênh, {data['stats']['role_count']} roles)")
        except Exception as e:
            logger.exception("Lỗi prefix create:")
            await msg.edit(content=f"❌ Thất bại: `{str(e)}`")

    @prefix_backup.command(name="list")
    @check_authorized()
    async def prefix_list(self, ctx: commands.Context):
        backups = list_backups_for_guild(ctx.guild.id)
        if not backups:
            return await ctx.reply("ℹ️ Chưa có bản sao lưu nào.")
        txt = "\n".join([f"• `{b['backup_id']}` - {datetime.fromtimestamp(b['created_timestamp']).strftime('%d/%m/%Y %H:%M')} ({b.get('note') or 'Không ghi chú'})" for b in backups[:10]])
        await ctx.reply(f"**Danh sách các bản sao lưu:**\n{txt}")

    @prefix_backup.command(name="load")
    @check_authorized()
    async def prefix_load(self, ctx: commands.Context, backup_id: str):
        backup_data = load_backup_data(backup_id, ctx.guild.id)
        if not backup_data:
            return await ctx.reply(f"❌ Không tìm thấy bản backup `{backup_id}`.")

        view = ConfirmRestoreView(author_id=ctx.author.id)
        confirm_msg = await ctx.reply(
            f"⚠️ **CẢNH BÁO:** Bạn sắp khôi phục server về `{backup_id}`. Các kênh và roles cũ sẽ bị xóa và tái tạo! Bạn có chắc không?",
            view=view
        )
        await view.wait()
        if view.value is not True:
            return

        progress_msg = await ctx.send("🚀 Bắt đầu khôi phục...")
        async def update_progress(status: str, percent: int):
            try:
                await progress_msg.edit(content=f"**Tiến trình: {percent}%** - {status}")
            except Exception:
                pass

        try:
            summary = await restore_guild(
                guild=ctx.guild,
                backup_data=backup_data,
                clear_existing=True,
                current_channel_id=ctx.channel.id,
                progress_callback=update_progress
            )
            await ctx.send(f"🎉 Khôi phục hoàn tất! Đã tạo {summary['roles_created']} roles, {summary['categories_created']} danh mục, {summary['channels_created']} kênh.")
        except Exception as e:
            logger.exception("Lỗi prefix load:")
            await ctx.send(f"❌ Lỗi khôi phục: `{str(e)}`")

async def setup(bot: commands.Bot):
    await bot.add_cog(BackupCommands(bot))
