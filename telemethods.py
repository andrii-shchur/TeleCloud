from pyrogram import Client, __version__
from pyrogram.api.functions import channels
import pyrogram

from dbmethods import Session
import platform
from login import phone_number, telegram_code, two_factor_auth
from telecloudutils import TempFileMaker, split_into_parts, rebuild_from_parts
from pyrogram.errors import FloodWait
from teleclouderrors import UploadingError, FileDuplicateError, FolderMissingError


def find_cloud_by_name():
    total = client.get_dialogs(limit=0).total_count
    for x, i in enumerate(client.iter_dialogs()):
        print('{}/{}'.format(x, total))
        if i.chat.type == 'channel' and i.chat.title == chat_title:
            full_chat = client.get_chat(i.chat.id)
            if full_chat.description == chat_desc:
                if not load_db(i.chat.id):
                    peer = client.resolve_peer(i.chat.id)
                    db_session.set_channel(int('-100' + str(peer.channel_id)), peer.access_hash)
                return db_session.get_channel()


def find_cloud_by_backup():
    for x, i in enumerate(client.iter_dialogs()):
        if i.chat.type == 'channel':
            if load_db(i.chat.id):
                return db_session.get_channel()


def create_cloud_channel():
    channel = client.send(channels.CreateChannel(
        title=chat_title,
        about=chat_desc, broadcast=True))
    chat = int('-100' + str(channel.chats[0].id))

    client.set_chat_photo(chat, chat_photo)
    client.get_messages(chat, message_ids=[2]).messages[0].delete()
    return channel


def load_db(chat_id):
    try:
        for x, m in enumerate(client.iter_history(chat_id, limit=11)):
            if m.document:
                if m.document.file_name.endswith('.tgdb'):
                    with TempFileMaker() as path:
                        m.download(path.name)
                        db_session.merge_db(path.name)
                    return db_session.get_channel()
    except Exception as E:
        print(E)
        return None


def upload_db():
    with TempFileMaker() as path:
        db_session.export_db(path.name)
    while True:
        try:
            old_msg = db_session.get_last_backup_id()
            msg_id = client.send_document(db_session.get_channel()[0], path.name).message_id
            db_session.set_last_backup_id(msg_id)
        except pyrogram.RPCError:
            continue

        if old_msg is not None:
            m = client.get_messages(chat_id=db_session.get_channel()[0], message_ids=[old_msg])
            if m.messages:
                m.messages[0].delete() if not m.messages[0].empty else None
        break


def save_file(file_id: str, to_folder):
    client.download_media(message=file_id, file_name=to_folder)


def upload_callback(client: Client, current, total):
    print('{}/{}'.format(current, total))


def upload_file(file_name, tags, to_folder, file):
    file_ids = []
    message_ids = []
    try:
        file = client.send_document(db_session.get_channel()[0], document=file, progress=upload_callback)
        file_ids.append(file.document.file_id)
        message_ids.append(file.message_id)
    except FloodWait as err:
        print(err)
    else:
        try:
            db_session.add_file(
                file_ids=file_ids,
                file_name=file_name,
                file_tags=tags,
                folder_name=to_folder,
                message_ids=message_ids)
        except (FolderMissingError, FileDuplicateError):
            pass
        upload_db()


def check_channel(channel_id):
    if channel_id is None:
        return False
    chat_id, access_hash = channel_id

    try:
        chat = client.get_chat(chat_id)
    except (ValueError, pyrogram.RPCError, pyrogram.errors.exceptions.bad_request_400.PeerIdInvalid) as E:
        print(E)
        return False
    if chat.title != chat_title or \
            chat.description != chat_desc:
        client.set_chat_description(chat_id, chat_desc)
        client.set_chat_title(chat_id, chat_title)
    return chat


def init_login():
    channel_id = db_session.get_channel()

    while not check_channel(channel_id):
        channel_id = find_cloud_by_name()
        if channel_id:
            channel_id = db_session.get_channel()
        elif input('try to find latest files backup automatically? (On name or description change)') == 'y':
            channel_id = find_cloud_by_backup()
        if not channel_id:
            channel = create_cloud_channel().chats[0]
            db_session.set_channel(int('-100' + str(channel.id)), channel.access_hash)

        channel_id = db_session.get_channel()

    client.stop()  # on app exit
    print('end')


if __name__ == '__main__':
    api_id = 576793
    api_hash = '2458f89fda1ae88bed1ce71375a2a7cb'
    session_file = 'Wirtos_new'
    client = Client(session_file,
                    device_model=platform.system(),
                    app_version=__version__,
                    api_id=api_id,
                    api_hash=api_hash,
                    test_mode=False,
                    phone_code=telegram_code,
                    phone_number=phone_number,
                    password=two_factor_auth)
    client.start()
    db_session = Session(session_file)
    chat_title = 'TelegramCloudApp'
    chat_desc = 'TelegramCloudApp of {}! Don\'t change name or description!'.format(client.get_me().id)
    chat_photo = 'gui/logo.png'
    init_login()
