import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import discord
import config

def get_guild_backup_dir(guild_id: int) -> Path:
    guild_dir = config.BACKUP_DIR / str(guild_id)
    guild_dir.mkdir(parents=True, exist_ok=True)
    return guild_dir

def serialize_overwrites(channel: discord.abc.GuildChannel) -> List[Dict[str, Any]]:
    overwrites_data = []
    for target, overwrite in channel.overwrites.items():
        allow, deny = overwrite.pair()
        if isinstance(target, discord.Role):
            overwrites_data.append({
                "type": "role",
                "target_id": target.id,
                "is_everyone": target.id == channel.guild.id,
                "allow": allow.value,
                "deny": deny.value
            })
        elif isinstance(target, discord.Member):
            overwrites_data.append({
                "type": "member",
                "target_id": target.id,
                "is_everyone": False,
                "allow": allow.value,
                "deny": deny.value
            })
    return overwrites_data

async def create_backup_data(guild: discord.Guild, author_id: int, author_name: str, note: str = "") -> Dict[str, Any]:
    timestamp = int(time.time())
    iso_time = datetime.utcnow().isoformat()
    backup_id = f"{guild.id}_{timestamp}"

    # 1. Guild Settings
    guild_settings = {
        "name": guild.name,
        "description": guild.description,
        "verification_level": guild.verification_level.value,
        "default_notifications": guild.default_notifications.value,
        "explicit_content_filter": guild.explicit_content_filter.value,
        "afk_timeout": guild.afk_timeout,
        "icon_url": str(guild.icon.url) if guild.icon else None,
        "banner_url": str(guild.banner.url) if guild.banner else None,
        "splash_url": str(guild.splash.url) if guild.splash else None,
    }

    # 2. Roles (bỏ qua managed roles và @everyone)
    roles_data = []
    everyone_role = guild.default_role
    for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
        if role.is_default() or role.managed:
            continue
        roles_data.append({
            "id": role.id,
            "name": role.name,
            "color": role.color.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "permissions": role.permissions.value,
            "position": role.position
        })

    # 3. Categories
    categories_data = []
    for cat in sorted(guild.categories, key=lambda c: c.position):
        categories_data.append({
            "id": cat.id,
            "name": cat.name,
            "position": cat.position,
            "overwrites": serialize_overwrites(cat)
        })

    # 4. Channels (Text, Voice, Stage, Forum)
    channels_data = []
    for channel in sorted(guild.channels, key=lambda c: c.position):
        if isinstance(channel, discord.CategoryChannel):
            continue

        c_type = "text"
        if isinstance(channel, discord.VoiceChannel):
            c_type = "voice"
        elif isinstance(channel, discord.StageChannel):
            c_type = "stage"
        elif isinstance(channel, discord.ForumChannel):
            c_type = "forum"

        chan_dict = {
            "id": channel.id,
            "name": channel.name,
            "type": c_type,
            "category_id": channel.category_id,
            "position": channel.position,
            "overwrites": serialize_overwrites(channel)
        }

        if hasattr(channel, "topic"):
            chan_dict["topic"] = channel.topic
        if hasattr(channel, "nsfw"):
            chan_dict["nsfw"] = channel.nsfw
        if hasattr(channel, "slowmode_delay"):
            chan_dict["slowmode_delay"] = channel.slowmode_delay
        if hasattr(channel, "bitrate"):
            chan_dict["bitrate"] = channel.bitrate
        if hasattr(channel, "user_limit"):
            chan_dict["user_limit"] = channel.user_limit

        channels_data.append(chan_dict)

    # 5. Emojis
    emojis_data = []
    for emoji in guild.emojis:
        emojis_data.append({
            "name": emoji.name,
            "url": str(emoji.url),
            "id": emoji.id
        })

    data = {
        "version": "1.0",
        "backup_id": backup_id,
        "created_at": iso_time,
        "created_timestamp": timestamp,
        "created_by": {
            "id": author_id,
            "name": author_name
        },
        "note": note,
        "guild_id": guild.id,
        "guild_name": guild.name,
        "settings": guild_settings,
        "everyone_permissions": everyone_role.permissions.value,
        "roles": roles_data,
        "categories": categories_data,
        "channels": channels_data,
        "emojis": emojis_data,
        "stats": {
            "role_count": len(roles_data),
            "category_count": len(categories_data),
            "channel_count": len(channels_data),
            "emoji_count": len(emojis_data)
        }
    }
    return data

def save_backup_file(data: Dict[str, Any]) -> Path:
    guild_id = data["guild_id"]
    backup_id = data["backup_id"]
    dest_dir = get_guild_backup_dir(guild_id)
    dest_file = dest_dir / f"{backup_id}.json"

    with open(dest_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    prune_old_backups(guild_id)
    return dest_file

def load_backup_data(backup_id: str, guild_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    # Nếu có guild_id, tìm trực tiếp trong thư mục guild
    if guild_id:
        target = get_guild_backup_dir(guild_id) / f"{backup_id}.json"
        if target.exists():
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)

    # Tìm quét toàn bộ thư mục backups
    for file in config.BACKUP_DIR.glob(f"**/{backup_id}.json"):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)

    return None

def list_backups_for_guild(guild_id: int) -> List[Dict[str, Any]]:
    guild_dir = get_guild_backup_dir(guild_id)
    backups = []
    for file in guild_dir.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                backups.append({
                    "backup_id": data.get("backup_id", file.stem),
                    "created_at": data.get("created_at", "N/A"),
                    "created_timestamp": data.get("created_timestamp", 0),
                    "created_by": data.get("created_by", {}).get("name", "Unknown"),
                    "note": data.get("note", ""),
                    "stats": data.get("stats", {}),
                    "file_path": str(file),
                    "file_size": file.stat().st_size
                })
        except Exception:
            continue

    # Sắp xếp mới nhất lên đầu
    backups.sort(key=lambda x: x["created_timestamp"], reverse=True)
    return backups

def delete_backup_file(backup_id: str, guild_id: Optional[int] = None) -> bool:
    if guild_id:
        target = get_guild_backup_dir(guild_id) / f"{backup_id}.json"
        if target.exists():
            target.unlink()
            return True

    for file in config.BACKUP_DIR.glob(f"**/{backup_id}.json"):
        file.unlink()
        return True

    return False

def prune_old_backups(guild_id: int):
    """Giữ lại tối đa MAX_BACKUPS_PER_GUILD bản sao lưu mới nhất."""
    backups = list_backups_for_guild(guild_id)
    if len(backups) > config.MAX_BACKUPS_PER_GUILD:
        to_delete = backups[config.MAX_BACKUPS_PER_GUILD:]
        for item in to_delete:
            p = Path(item["file_path"])
            if p.exists():
                p.unlink()
