import asyncio
import logging
from typing import Dict, Any, Callable, Awaitable, Optional
import discord

logger = logging.getLogger("backup_bot.restorer")

class RestoreError(Exception):
    pass

async def restore_guild(
    guild: discord.Guild,
    backup_data: Dict[str, Any],
    clear_existing: bool = True,
    current_channel_id: Optional[int] = None,
    progress_callback: Optional[Callable[[str, int], Awaitable[None]]] = None
) -> Dict[str, Any]:
    """
    Khôi phục cấu hình server từ dữ liệu backup.
    """
    bot_member = guild.me
    if not bot_member.guild_permissions.administrator:
        raise RestoreError("Bot cần quyền 'Administrator' (Quản trị viên) và Role cao nhất có thể để thực hiện khôi phục!")

    async def report(status: str, percent: int):
        if progress_callback:
            try:
                await progress_callback(status, percent)
            except Exception as e:
                logger.warning(f"Lỗi khi gửi callback tiến trình: {e}")

    summary = {
        "roles_created": 0,
        "categories_created": 0,
        "channels_created": 0,
        "errors": []
    }

    # ==========================================
    # BƯỚC 1: CẬP NHẬT CÀI ĐẶT SERVER CHUNG
    # ==========================================
    await report("Đang cập nhật cài đặt cơ bản của server...", 5)
    settings = backup_data.get("settings", {})
    try:
        edit_kwargs = {}
        if "name" in settings and settings["name"]:
            edit_kwargs["name"] = settings["name"]
        if "verification_level" in settings:
            try:
                edit_kwargs["verification_level"] = discord.VerificationLevel(settings["verification_level"])
            except Exception:
                pass
        if "default_notifications" in settings:
            try:
                edit_kwargs["default_notifications"] = discord.NotificationLevel(settings["default_notifications"])
            except Exception:
                pass
        if "explicit_content_filter" in settings:
            try:
                edit_kwargs["explicit_content_filter"] = discord.ContentFilter(settings["explicit_content_filter"])
            except Exception:
                pass
        if "afk_timeout" in settings:
            edit_kwargs["afk_timeout"] = settings["afk_timeout"]

        if edit_kwargs:
            await guild.edit(**edit_kwargs)
    except Exception as e:
        logger.warning(f"Không thể cập nhật một số cài đặt server: {e}")
        summary["errors"].append(f"Cài đặt server: {str(e)}")

    # ==========================================
    # BƯỚC 2: DỌN DẸP KÊNH & ROLE CŨ (NẾU CÓ CHỌN CLEAR)
    # ==========================================
    if clear_existing:
        await report("Đang dọn dẹp các kênh bị phá/cũ...", 15)
        # Xóa các kênh cũ (trừ kênh hiện tại đang chạy lệnh để tránh mất kết nối bot)
        for channel in list(guild.channels):
            if channel.id == current_channel_id:
                continue
            try:
                await channel.delete(reason="Khôi phục Backup Server: Dọn dẹp kênh cũ")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.debug(f"Không thể xóa kênh {channel.name}: {e}")

        await report("Đang dọn dẹp các role cũ...", 25)
        # Xóa các role cũ (chỉ xóa role thấp hơn bot và không phải managed / everyone)
        for role in list(guild.roles):
            if role.is_default() or role.managed:
                continue
            if role >= bot_member.top_role:
                continue
            try:
                await role.delete(reason="Khôi phục Backup Server: Dọn dẹp role cũ")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.debug(f"Không thể xóa role {role.name}: {e}")

    # ==========================================
    # BƯỚC 3: KHÔI PHỤC ROLES
    # ==========================================
    await report("Đang tạo và khôi phục các Role...", 40)
    role_mapping: Dict[int, discord.Role] = {}

    # Cập nhật quyền của role @everyone
    everyone_perms_val = backup_data.get("everyone_permissions")
    if everyone_perms_val is not None:
        try:
            await guild.default_role.edit(
                permissions=discord.Permissions(everyone_perms_val),
                reason="Khôi phục Backup: @everyone permissions"
            )
        except Exception as e:
            logger.warning(f"Không thể cập nhật quyền @everyone: {e}")

    # Tạo các role từ vị trí thấp lên cao
    roles_list = backup_data.get("roles", [])
    roles_sorted = sorted(roles_list, key=lambda r: r.get("position", 0))

    for r_data in roles_sorted:
        try:
            perms = discord.Permissions(r_data.get("permissions", 0))
            color = discord.Colour(r_data.get("color", 0))
            new_role = await guild.create_role(
                name=r_data["name"],
                permissions=perms,
                colour=color,
                hoist=r_data.get("hoist", False),
                mentionable=r_data.get("mentionable", False),
                reason="Khôi phục Backup Server"
            )
            role_mapping[r_data["id"]] = new_role
            summary["roles_created"] += 1
            await asyncio.sleep(0.4)
        except Exception as e:
            logger.warning(f"Lỗi khi tạo role {r_data.get('name')}: {e}")
            summary["errors"].append(f"Role {r_data.get('name')}: {str(e)}")

    # Helper chuyển đổi overwrites data sang discord.PermissionOverwrite
    def build_overwrites(overwrites_raw):
        result = {}
        for ow in overwrites_raw:
            target = None
            if ow.get("type") == "role":
                if ow.get("is_everyone"):
                    target = guild.default_role
                else:
                    target = role_mapping.get(ow.get("target_id"))
            elif ow.get("type") == "member":
                target = guild.get_member(ow.get("target_id"))

            if target:
                allow_perms = discord.Permissions(ow.get("allow", 0))
                deny_perms = discord.Permissions(ow.get("deny", 0))
                result[target] = discord.PermissionOverwrite.from_pair(allow_perms, deny_perms)
        return result

    # ==========================================
    # BƯỚC 4: KHÔI PHỤC CATEGORIES (DANH MỤC)
    # ==========================================
    await report("Đang tạo lại các danh mục kênh (Categories)...", 60)
    category_mapping: Dict[int, discord.CategoryChannel] = {}
    categories_list = backup_data.get("categories", [])
    categories_sorted = sorted(categories_list, key=lambda c: c.get("position", 0))

    for cat_data in categories_sorted:
        try:
            cat_overwrites = build_overwrites(cat_data.get("overwrites", []))
            new_cat = await guild.create_category(
                name=cat_data["name"],
                overwrites=cat_overwrites,
                reason="Khôi phục Backup Server"
            )
            category_mapping[cat_data["id"]] = new_cat
            summary["categories_created"] += 1
            await asyncio.sleep(0.4)
        except Exception as e:
            logger.warning(f"Lỗi khi tạo danh mục {cat_data.get('name')}: {e}")
            summary["errors"].append(f"Danh mục {cat_data.get('name')}: {str(e)}")

    # ==========================================
    # BƯỚC 5: KHÔI PHỤC KÊNH (CHANNELS)
    # ==========================================
    await report("Đang tạo lại các kênh văn bản & giọng nói...", 80)
    channels_list = backup_data.get("channels", [])
    channels_sorted = sorted(channels_list, key=lambda c: c.get("position", 0))

    for c_data in channels_sorted:
        c_type = c_data.get("type", "text")
        c_name = c_data["name"]
        c_overwrites = build_overwrites(c_data.get("overwrites", []))
        c_cat = category_mapping.get(c_data.get("category_id"))

        try:
            if c_type == "text":
                await guild.create_text_channel(
                    name=c_name,
                    category=c_cat,
                    topic=c_data.get("topic"),
                    slowmode_delay=c_data.get("slowmode_delay", 0),
                    nsfw=c_data.get("nsfw", False),
                    overwrites=c_overwrites,
                    reason="Khôi phục Backup Server"
                )
                summary["channels_created"] += 1
            elif c_type == "voice":
                bitrate = c_data.get("bitrate", 64000)
                # Giới hạn bitrate phù hợp với level boost của server
                bitrate = min(bitrate, guild.bitrate_limit)
                await guild.create_voice_channel(
                    name=c_name,
                    category=c_cat,
                    bitrate=bitrate,
                    user_limit=c_data.get("user_limit", 0),
                    overwrites=c_overwrites,
                    reason="Khôi phục Backup Server"
                )
                summary["channels_created"] += 1
            elif c_type == "stage":
                try:
                    await guild.create_stage_channel(
                        name=c_name,
                        category=c_cat,
                        overwrites=c_overwrites,
                        reason="Khôi phục Backup Server"
                    )
                    summary["channels_created"] += 1
                except Exception:
                    # Nếu server không bật Community, fallback về voice
                    await guild.create_voice_channel(
                        name=c_name,
                        category=c_cat,
                        overwrites=c_overwrites,
                        reason="Khôi phục Backup Server (Fallback)"
                    )
                    summary["channels_created"] += 1
            elif c_type == "forum":
                try:
                    await guild.create_forum(
                        name=c_name,
                        category=c_cat,
                        topic=c_data.get("topic"),
                        overwrites=c_overwrites,
                        reason="Khôi phục Backup Server"
                    )
                    summary["channels_created"] += 1
                except Exception:
                    # Nếu server không bật Community, fallback về text
                    await guild.create_text_channel(
                        name=c_name,
                        category=c_cat,
                        topic=c_data.get("topic"),
                        overwrites=c_overwrites,
                        reason="Khôi phục Backup Server (Fallback)"
                    )
                    summary["channels_created"] += 1

            await asyncio.sleep(0.4)
        except Exception as e:
            logger.warning(f"Lỗi khi tạo kênh {c_name}: {e}")
            summary["errors"].append(f"Kênh {c_name}: {str(e)}")

    await report("Khôi phục hoàn tất!", 100)
    return summary
