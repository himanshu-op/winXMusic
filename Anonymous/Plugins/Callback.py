import asyncio
import os
import random
from asyncio import QueueEmpty

from config import get_queue
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import StreamType
from pytgcalls.types.input_stream import InputAudioStream, InputStream

from Anonymous import BOT_USERNAME, MUSIC_BOT_NAME, app, db_mem
from Anonymous.Core.PyTgCalls import Queues, Anonymous
from Anonymous.Core.PyTgCalls.Converter import convert
from Anonymous.Core.PyTgCalls.Downloader import download
from Anonymous.Database import (_get_playlists, delete_playlist, get_playlist,
                            get_playlist_names, is_active_chat, save_playlist)
from Anonymous.Database.queue import (add_active_chat, is_active_chat,
                                  is_music_playing, music_off, music_on,
                                  remove_active_chat)
from Anonymous.Decorators.admins import AdminRightsCheckCB
from Anonymous.Decorators.checker import checkerCB
from Anonymous.Inline import (audio_markup, audio_markup2, download_markup,
                          fetch_playlist, paste_queue_markup, primary_markup)
from Anonymous.Utilities.changers import time_to_seconds
from Anonymous.Utilities.chat import specialfont_to_normal
from Anonymous.Utilities.paste import isPreviewUp, paste_queue
from Anonymous.Utilities.theme import check_theme
from Anonymous.Utilities.thumbnails import gen_thumb
from Anonymous.Utilities.timer import start_timer
from Anonymous.Utilities.youtube import get_yt_info_id

loop = asyncio.get_event_loop()


@app.on_callback_query(filters.regex("forceclose"))
async def forceclose(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    query, user_id = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        return await CallbackQuery.answer(
            "ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀʟʟᴏᴡᴇᴅ ᴛᴏ ᴄʟᴏsᴇ ᴛʜɪs ʙᴀʙʏ.", show_alert=True
        )
    await CallbackQuery.message.delete()
    await CallbackQuery.answer()


@app.on_callback_query(
    filters.regex(pattern=r"^(pausecb|skipcb|stopcb|resumecb)$")
)
@AdminRightsCheckCB
@checkerCB
async def admin_risghts(_, CallbackQuery):
    global get_queue
    command = CallbackQuery.matches[0].group(1)
    if not await is_active_chat(CallbackQuery.message.chat.id):
        return await CallbackQuery.answer(
            "ɴᴏᴛʜɪɴɢ ɪs ᴘʟᴀʏɪɴɢ ᴏɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ʙᴀʙʏ.", show_alert=True
        )
    chat_id = CallbackQuery.message.chat.id
    if command == "pausecb":
        if not await is_music_playing(chat_id):
            return await CallbackQuery.answer(
                "ᴍᴜsɪᴄ ɪs ᴀʟʀᴇᴀᴅʏ ᴘᴀᴜsᴇᴅ ʙᴀʙʏ", show_alert=True
            )
        await music_off(chat_id)
        await Anonymous.pytgcalls.pause_stream(chat_id)
        await CallbackQuery.message.reply_text(
            f"😭 ᴠᴏɪᴄᴇᴄʜᴀᴛ ᴘᴀᴜsᴇᴅ ʙʏ {CallbackQuery.from_user.mention} ʙᴀʙʏ !",
            reply_markup=audio_markup2,
        )
        await CallbackQuery.message.delete()
        await CallbackQuery.answer("Paused", show_alert=True)
    if command == "resumecb":
        if await is_music_playing(chat_id):
            return await CallbackQuery.answer(
                "ᴍᴜsɪᴄ ɪs ᴀʟʀᴇᴀᴅʏ ʀᴇsᴜᴍᴇᴅ​.", show_alert=True
            )
        await music_on(chat_id)
        await Anonymous.pytgcalls.resume_stream(chat_id)
        await CallbackQuery.message.reply_text(
            f"😘 ᴠᴏɪᴄᴇᴄʜᴀᴛ ʀᴇsᴜᴍᴇᴅ​ ʙʏ {CallbackQuery.from_user.mention} ʙᴀʙʏ !",
            reply_markup=audio_markup2,
        )
        await CallbackQuery.message.delete()
        await CallbackQuery.answer("Resumed", show_alert=True)
    if command == "stopcb":
        try:
            Queues.clear(chat_id)
        except QueueEmpty:
            pass
        await remove_active_chat(chat_id)
        await Anonymous.pytgcalls.leave_group_call(chat_id)
        await CallbackQuery.message.reply_text(
            f"😭 ᴠᴏɪᴄᴇᴄʜᴀᴛ ᴇɴᴅ/sᴛᴏᴘᴘᴇᴅ​ ʙʏ {CallbackQuery.from_user.mention} ʙᴀʙʏ !",
            reply_markup=audio_markup2,
        )
        await CallbackQuery.message.delete()
        await CallbackQuery.answer("Stopped", show_alert=True)
    if command == "skipcb":
        Queues.task_done(chat_id)
        if Queues.is_empty(chat_id):
            await remove_active_chat(chat_id)
            await CallbackQuery.message.reply_text(
                f"ɴᴏ ᴍᴏʀᴇ ᴍᴜsɪᴄ ɪɴ __ǫᴜᴇᴜᴇ__ \n\nʟᴇᴀᴠɪɴɢ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ...ʙᴜᴛᴛᴏɴ ᴜsᴇᴅ ʙʏ :- {CallbackQuery.from_user.mention} ʙᴀʙʏ"
            )
            await Anonymous.pytgcalls.leave_group_call(chat_id)
            await CallbackQuery.message.delete()
            await CallbackQuery.answer(
                "sᴋɪᴘᴘᴇᴅ ʙᴀʙʏ. ɴᴏ ᴍᴏʀᴇ ᴍᴜsɪᴄ ɪɴ ǫᴜᴇᴜᴇ", show_alert=True
            )
            return
        else:
            videoid = Queues.get(chat_id)["file"]
            got_queue = get_queue.get(CallbackQuery.message.chat.id)
            if got_queue:
                got_queue.pop(0)
            finxx = f"{videoid[0]}{videoid[1]}{videoid[2]}"
            aud = 0
            if str(finxx) != "raw":
                await CallbackQuery.message.delete()
                await CallbackQuery.answer(
                    "sᴋɪᴘᴘᴇᴅ! ᴘʟᴀʏʟɪsᴛ ᴘʟᴀʏɪɴɢ​....", show_alert=True
                )
                mystic = await CallbackQuery.message.reply_text(
                    f"**{MUSIC_BOT_NAME} ᴘʟᴀʏʟɪsᴛ ꜰᴜɴᴄᴛɪᴏɴ**\n\n__ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ɴᴇxᴛ ᴍᴜsɪᴄ ꜰʀᴏᴍ ᴘʟᴀʏʟɪsᴛ​....__\n\nʙᴜᴛᴛᴏɴ ᴜsᴇᴅ ʙʏ :- {CallbackQuery.from_user.mention} ʙᴀʙʏ"
                )
                (
                    title,
                    duration_min,
                    duration_sec,
                    thumbnail,
                ) = get_yt_info_id(videoid)
                await mystic.edit(
                    f"**{MUSIC_BOT_NAME} ᴅᴏᴡɴʟᴏᴀᴅᴇʀ**\n\n**Title:** {title[:50]}\n\n0% â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“ 100%"
                )
                downloaded_file = await loop.run_in_executor(
                    None, download, videoid, mystic, title
                )
                raw_path = await convert(downloaded_file)
                await Anonymous.pytgcalls.change_stream(
                    chat_id,
                    InputStream(
                        InputAudioStream(
                            raw_path,
                        ),
                    ),
                )
                theme = await check_theme(chat_id)
                chat_title = await specialfont_to_normal(
                    CallbackQuery.message.chat.title
                )
                thumb = await gen_thumb(
                    thumbnail,
                    title,
                    CallbackQuery.from_user.id,
                    theme,
                    chat_title,
                )
                buttons = primary_markup(
                    videoid,
                    CallbackQuery.from_user.id,
                    duration_min,
                    duration_min,
                )
                await mystic.delete()
                mention = db_mem[videoid]["username"]
                final_output = await CallbackQuery.message.reply_photo(
                    photo=thumb,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    caption=(
                        f"<b>__sᴋɪᴘᴘᴇᴅ ᴠᴏɪᴄᴇᴄʜᴀᴛ ʙᴀʙʏ__</b>\n\n😫<b>__sᴛᴀʀᴛᴇᴅ ᴘʟᴀʏɪɴɢ:__ </b>[{title[:25]}](https://www.youtube.com/watch?v={videoid}) \n<b>__ᴅᴜʀᴀᴛɪᴏɴ:__</b> {duration_min} Mins\n**__ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ:__** {mention} ʙᴀʙʏ"
                    ),
                )
                os.remove(thumb)

            else:
                await CallbackQuery.message.delete()
                await CallbackQuery.answer("Skipped!", show_alert=True)
                await Anonymous.pytgcalls.change_stream(
                    chat_id,
                    InputStream(
                        InputAudioStream(
                            videoid,
                        ),
                    ),
                )
                afk = videoid
                title = db_mem[videoid]["title"]
                duration_min = db_mem[videoid]["duration"]
                duration_sec = int(time_to_seconds(duration_min))
                mention = db_mem[videoid]["username"]
                videoid = db_mem[videoid]["videoid"]
                if str(videoid) == "smex1":
                    buttons = buttons = audio_markup(
                        videoid,
                        CallbackQuery.from_user.id,
                        duration_min,
                        duration_min,
                    )
                    thumb = "Utils/Telegram.jpeg"
                    aud = 1
                else:
                    _path_ = _path_ = (
                        (str(afk))
                        .replace("_", "", 1)
                        .replace("/", "", 1)
                        .replace(".", "", 1)
                    )
                    thumb = f"cache/{_path_}final.png"
                    buttons = primary_markup(
                        videoid,
                        CallbackQuery.from_user.id,
                        duration_min,
                        duration_min,
                    )
                final_output = await CallbackQuery.message.reply_photo(
                    photo=thumb,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    caption=f"<b>__sᴋɪᴘᴘᴇᴅ ᴠᴏɪᴄᴇᴄʜᴀᴛ ʙᴀʙʏ__</b>\n\n😫<b>__sᴛᴀʀᴛᴇᴅ ᴘʟᴀʏɪɴɢ:__</b> {title} \n<b>__ᴅᴜʀᴀᴛɪᴏɴ:__</b> {duration_min} \n<b>__ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ:__ </b> {mention} ʙᴀʙʏ",
                )
            await start_timer(
                videoid,
                duration_min,
                duration_sec,
                final_output,
                CallbackQuery.message.chat.id,
                CallbackQuery.message.from_user.id,
                aud,
            )


@app.on_callback_query(filters.regex("play_playlist"))
async def play_playlist(_, CallbackQuery):
    global get_queue
    loop = asyncio.get_event_loop()
    callback_data = CallbackQuery.data.strip()
    chat_id = CallbackQuery.message.chat.id
    callback_request = callback_data.split(None, 1)[1]
    user_id, smex, type = callback_request.split("|")
    chat_title = CallbackQuery.message.chat.title
    user_id = int(user_id)
    if chat_id not in db_mem:
        db_mem[chat_id] = {}
    if smex == "third":
        _playlist = await get_playlist_names(user_id, type)
        try:
            user = await app.get_users(user_id)
            third_name = user.first_name
        except:
            third_name = "Deleted Account"
    elif smex == "Personal":
        if CallbackQuery.from_user.id != int(user_id):
            return await CallbackQuery.answer(
                "ᴛʜɪs ɪs ɴᴏᴛ ꜰᴏʀ ʏᴏᴜ ʙᴀʙʏ! ᴘʟᴀʏ ʏᴏᴜʀ ᴏᴡɴ ᴘʟᴀʏʟɪsᴛ​ ʙᴀʙʏ", show_alert=True
            )
        _playlist = await get_playlist_names(user_id, type)
        third_name = CallbackQuery.from_user.first_name
    elif smex == "Group":
        _playlist = await get_playlist_names(
            CallbackQuery.message.chat.id, type
        )
        user_id = CallbackQuery.message.chat.id
        third_name = chat_title
    else:
        return await CallbackQuery.answer("ᴇʀʀᴏʀ ɪɴ ᴘʟᴀʏʟɪsᴛ ʙᴀʙʏ.")
    if not _playlist:
        return await CallbackQuery.answer(
            f"ᴛʜɪs ᴜsᴇʀ ʜᴀs ɴᴏ ᴘʟᴀʏʟɪsᴛ ᴏɴ sᴇʀᴠᴇʀs.​", show_alert=True
        )
    else:
        await CallbackQuery.message.delete()
        mystic = await CallbackQuery.message.reply_text(
            f"sᴛᴀʀᴛᴇᴅ ᴘʟᴀʏʟɪsᴛ ᴏꜰ​ {third_name}.\n\nʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ :- {CallbackQuery.from_user.first_name} ʙᴀʙʏ"
        )
        msg = f"ᴘʟᴀʏʟɪsᴛ ǫᴜᴇᴜᴇᴅ ʙᴀʙʏ:\n\n"
        j = 0
        for_t = 0
        for_p = 0
        for shikhar in _playlist:
            _note = await get_playlist(user_id, shikhar, type)
            title = _note["title"]
            videoid = _note["videoid"]
            url = f"https://www.youtube.com/watch?v={videoid}"
            duration = _note["duration"]
            if await is_active_chat(chat_id):
                position = await Queues.put(chat_id, file=videoid)
                j += 1
                for_p = 1
                msg += f"{j}- {title[:50]}\n"
                msg += f"ǫᴜᴇᴜᴇᴅ ᴘᴏsɪᴛɪᴏɴ​- {position}\n\n"
                if videoid not in db_mem:
                    db_mem[videoid] = {}
                db_mem[videoid]["username"] = CallbackQuery.from_user.mention
                db_mem[videoid]["chat_title"] = chat_title
                db_mem[videoid]["user_id"] = user_id
                got_queue = get_queue.get(CallbackQuery.message.chat.id)
                title = title
                user = CallbackQuery.from_user.first_name
                duration = duration
                to_append = [title, user, duration]
                got_queue.append(to_append)
            else:
                loop = asyncio.get_event_loop()
                send_video = videoid
                for_t = 1
                (
                    title,
                    duration_min,
                    duration_sec,
                    thumbnail,
                ) = get_yt_info_id(videoid)
                mystic = await mystic.edit(
                    f"**{MUSIC_BOT_NAME} ᴅᴏᴡɴʟᴏᴀᴅᴇʀ**\n\n**Title:** {title[:50]}\n\n0% â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“ 100%"
                )
                downloaded_file = await loop.run_in_executor(
                    None, download, videoid, mystic, title
                )
                raw_path = await convert(downloaded_file)
                try:
                    await Anonymous.pytgcalls.join_group_call(
                        chat_id,
                        InputStream(
                            InputAudioStream(
                                raw_path,
                            ),
                        ),
                        stream_type=StreamType().local_stream,
                    )
                except Exception as e:
                    return await mystic.edit(
                        "ᴇʀʀᴏʀ ᴊᴏɪɴɪɴɢ ᴠᴏɪᴄᴇᴄʜᴀᴛ​. ᴍᴀᴋᴇ sᴜʀᴇ ᴠᴏɪᴄᴇᴄʜᴀᴛ ɪs ᴇɴᴀʙʟᴇᴅ​."
                    )
                theme = await check_theme(chat_id)
                chat_title = await specialfont_to_normal(chat_title)
                thumb = await gen_thumb(
                    thumbnail,
                    title,
                    CallbackQuery.from_user.id,
                    theme,
                    chat_title,
                )
                buttons = primary_markup(
                    videoid,
                    CallbackQuery.from_user.id,
                    duration_min,
                    duration_min,
                )
                await mystic.delete()
                get_queue[CallbackQuery.message.chat.id] = []
                got_queue = get_queue.get(CallbackQuery.message.chat.id)
                title = title
                user = CallbackQuery.from_user.first_name
                duration = duration_min
                to_append = [title, user, duration]
                got_queue.append(to_append)
                await music_on(chat_id)
                await add_active_chat(chat_id)
                cap = f"😫<b>__ᴘʟᴀʏɪɴɢ:__ </b>[{title[:25]}](https://www.youtube.com/watch?v={videoid}) \n’¡<b>__ɪɴꜰᴏ:__</b> [ɢᴇᴛ ᴀᴅᴅɪᴛɪᴏɴᴀʟ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ](https://t.me/{BOT_USERNAME}?start=info_{videoid})\n**__ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ:__** {CallbackQuery.from_user.mention} ʙᴀʙʏ"
                final_output = await CallbackQuery.message.reply_photo(
                    photo=thumb,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    caption=cap,
                )
                os.remove(thumb)
        await mystic.delete()
        if for_p == 1:
            m = await CallbackQuery.message.reply_text(
                "ᴘᴀsᴛɪɴɢ ǫᴜᴇᴜᴇᴅ ᴘʟᴀʏʟɪsᴛ ᴛᴏ ʙɪɴ​ ʙᴀʙʏ"
            )
            link = await paste_queue(msg)
            preview = link + "/preview.png"
            url = link + "/index.txt"
            buttons = paste_queue_markup(url)
            if await isPreviewUp(preview):
                await CallbackQuery.message.reply_photo(
                    photo=preview,
                    caption=f"ᴛʜɪs ɪs ᴛʜᴇ ǫᴜᴇᴜᴇᴅ ᴘʟᴀʏʟɪsᴛ ᴏꜰ {third_name} ʙᴀʙʏ.\n\nᴘʟᴀʏᴇᴅ ʙʏ​ :- {CallbackQuery.from_user.mention} ʙᴀʙʏ",
                    quote=False,
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                await m.delete()
            else:
                await CallbackQuery.message.reply_text(
                    text=msg, reply_markup=audio_markup2
                )
                await m.delete()
        else:
            await CallbackQuery.message.reply_text(
                "ᴏɴʟʏ 1 ᴍᴏʀᴇ ᴍᴜsɪᴄ ɪɴ ᴘʟᴀʏʟɪsᴛ... ɴᴏ ᴍᴏʀᴇ ᴍᴜsɪᴄ ᴛᴏ ᴀᴅᴅ ɪɴ ǫᴜᴇᴜᴇ​."
            )
        if for_t == 1:
            await start_timer(
                send_video,
                duration_min,
                duration_sec,
                final_output,
                CallbackQuery.message.chat.id,
                CallbackQuery.message.from_user.id,
                0,
            )


@app.on_callback_query(filters.regex("add_playlist"))
async def group_playlist(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    videoid, type, genre = callback_request.split("|")
    if type == "Personal":
        user_id = CallbackQuery.from_user.id
    elif type == "Group":
        a = await app.get_chat_member(
            CallbackQuery.message.chat.id, CallbackQuery.from_user.id
        )
        if not a.can_manage_voice_chats:
            return await CallbackQuery.answer(
                "ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ᴘᴇʀᴍɪssɪᴏɴ​ ʙᴀʙʏ.\nʏᴏᴜ ɴᴇᴇᴅ ᴛʜᴇ ᴄᴀɴ ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏ ᴄʜᴀᴛs ᴘᴇʀᴍɪssɪᴏɴs.",
                show_alert=True,
            )
        user_id = CallbackQuery.message.chat.id
    _count = await get_playlist_names(user_id, genre)
    if not _count:
        sex = await CallbackQuery.message.reply_text(
            f"ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ  {MUSIC_BOT_NAME}'s ᴘʟᴀʏʟɪsᴛ ꜰᴇᴀᴛᴜʀᴇ​.\n\nɢᴇɴᴇʀᴀᴛɪɴɢ ʏᴏᴜʀ ᴘʟᴀʏʟɪsᴛ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ...ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ​ ʙᴀʙʏ.\n\nɢᴇɴʀᴇ​:- {genre}"
        )
        await asyncio.sleep(2)
        await sex.delete()
        count = len(_count)
    else:
        count = len(_count)
    count = int(count)
    if count == 50:
        return await CallbackQuery.answer(
            "sᴏʀʀʏ! ʏᴏᴜ ᴄᴀɴ ᴏɴʟʏ ʜᴀᴠᴇ 50 ᴍᴜsɪᴄ ɪɴ ᴀ ᴘʟᴀʏʟɪsᴛ​ ʙᴀʙʏ.",
            show_alert=True,
        )
    loop = asyncio.get_event_loop()
    await CallbackQuery.answer()
    title, duration_min, duration_sec, thumbnail = get_yt_info_id(videoid)
    _check = await get_playlist(user_id, videoid, genre)
    title = title[:50]
    if _check:
        return await CallbackQuery.message.reply_text(
            f"{CallbackQuery.from_user.mention}, ɪᴛs ᴀʟʀᴇᴀᴅʏ ɪɴ ᴛʜᴇ ᴘʟᴀʏʟɪsᴛ​ ʙᴀʙʏ!"
        )
    assis = {
        "videoid": videoid,
        "title": title,
        "duration": duration_min,
    }
    await save_playlist(user_id, videoid, assis, genre)
    Name = CallbackQuery.from_user.first_name
    return await CallbackQuery.message.reply_text(
        f"ᴀᴅᴅᴇᴅ ᴛᴏ {type}'s {genre} ᴘʟᴀʏʟɪsᴛ ʙʏ​ {CallbackQuery.from_user.mention} ʙᴀʙʏ"
    )


@app.on_callback_query(filters.regex("check_playlist"))
async def check_playlist(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    type, genre = callback_request.split("|")
    if type == "Personal":
        user_id = CallbackQuery.from_user.id
        user_name = CallbackQuery.from_user.first_name
    elif type == "Group":
        user_id = CallbackQuery.message.chat.id
        user_name = CallbackQuery.message.chat.title
    _playlist = await get_playlist_names(user_id, genre)
    if not _playlist:
        return await CallbackQuery.answer(
            f"ɴᴏ {genre} ᴘʟᴀʏʟɪsᴛ ᴏɴ sᴇʀᴠᴇʀs ʙᴀʙʏ. ᴛʀʏ ᴀᴅᴅɪɴɢ ᴍᴜsɪᴄ ɪɴ ᴘʟᴀʏʟɪsᴛ.",
            show_alert=True,
        )
    else:
        j = 0
        await CallbackQuery.answer()
        await CallbackQuery.message.delete()
        msg = f"ꜰᴇᴛᴄʜᴇᴅ ᴘʟᴀʏʟɪsᴛ​:\n\n"
        for Anonymous in _playlist:
            j += 1
            _note = await get_playlist(user_id, anonymous, genre)
            title = _note["title"]
            duration = _note["duration"]
            msg += f"{j}- {title[:60]}\n"
            msg += f"  ᴅᴜʀᴀᴛɪᴏɴ - {duration} Min(s)\n\n"
        m = await CallbackQuery.message.reply_text("ᴘʟᴀsᴛɪɴɢ ᴘʟᴀʏʟɪsᴛ ᴛᴏ ʙɪɴ​ ʙᴀʙʏ")
        link = await paste_queue(msg)
        preview = link + "/preview.png"
        url = link + "/index.txt"
        buttons = fetch_playlist(
            user_name, type, genre, CallbackQuery.from_user.id, url
        )
        if await isPreviewUp(preview):
            await CallbackQuery.message.reply_photo(
                photo=preview,
                caption=f"ᴛʜɪs ɪs ᴛʜᴇ ᴘʟᴀʏʟɪsᴛ ᴏꜰ​ {user_name} ʙᴀʙʏ.",
                quote=False,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            await m.delete()
        else:
            await CallbackQuery.message.reply_text(
                text=msg, reply_markup=audio_markup2
            )
            await m.delete()


@app.on_callback_query(filters.regex("delete_playlist"))
async def del_playlist(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    type, genre = callback_request.split("|")
    if str(type) == "Personal":
        user_id = CallbackQuery.from_user.id
        user_name = CallbackQuery.from_user.first_name
    elif str(type) == "Group":
        a = await app.get_chat_member(
            CallbackQuery.message.chat.id, CallbackQuery.from_user.id
        )
        if not a.can_manage_voice_chats:
            return await CallbackQuery.answer(
                "ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ᴘᴇʀᴍɪssɪᴏɴ​ ʙᴀʙʏ.\nʏᴏᴜ ɴᴇᴇᴅ ᴛʜᴇ ᴄᴀɴ ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏ ᴄʜᴀᴛs ᴘᴇʀᴍɪssɪᴏɴs.",
                show_alert=True,
            )
        user_id = CallbackQuery.message.chat.id
        user_name = CallbackQuery.message.chat.title
    _playlist = await get_playlist_names(user_id, genre)
    if not _playlist:
        return await CallbackQuery.answer(
            "ᴛʜɪs ɢʀᴏᴜᴘ ʜᴀs ɴᴏ ᴘʟᴀʏʟɪsᴛ ᴏɴ ᴍʏ sᴇʀᴠᴇʀ​", show_alert=True
        )
    else:
        await CallbackQuery.message.delete()
        await CallbackQuery.answer()
        for shikhar in _playlist:
            await delete_playlist(user_id, shikhar, genre)
    await CallbackQuery.message.reply_text(
        f"sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {type}'s {genre} ᴡʜᴏʟᴇ ᴘʟᴀʏʟɪsᴛ​\n\nʙʏ :- {CallbackQuery.from_user.mention}"
    )


@app.on_callback_query(filters.regex("audio_video_download"))
async def down_playlisyts(_, CallbackQuery):
    await CallbackQuery.answer()
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    userid = CallbackQuery.from_user.id
    videoid, user_id = callback_request.split("|")
    buttons = download_markup(videoid, user_id)
    await CallbackQuery.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(pattern=r"good"))
async def good(_, CallbackQuery):
    await CallbackQuery.answer()
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    userid = CallbackQuery.from_user.id
    videoid, user_id = callback_request.split("|")
    buttons = download_markup(videoid, user_id)
    await CallbackQuery.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )
