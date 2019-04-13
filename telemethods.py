from pyrogram import Client, __version__
from pyrogram.api.functions import channels
from pyrogram.api.types import MessageMediaDocument
import pyrogram
import os
from dbmethods import Session
import platform


class PathMaker:
    def __init__(self, name, path=''):
        self.name = name
        self.path = os.path.join(path, name)

    def __enter__(self):
        if not os.path.exists(self.path) or not os.path.isdir(self.path):
            os.mkdir(self.path)
        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def find_cloud_by_name():
    total = client.get_dialogs(limit=0).total_count
    for x, i in enumerate(client.iter_dialogs()):
        print('{}/{}'.format(x, total))
        if i.chat.type == 'channel' and i.chat.description == chat_desc and i.chat.title == chat_title:
            load_db(i.chat.id)
            return db_session.get_channel()


def find_cloud_by_backup():
    total = client.get_dialogs(limit=0).total_count
    for x, i in enumerate(client.iter_dialogs()):
        print('{}/{}'.format(x, total))
        load_db(i.chat.id)
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
                    with PathMaker('.temp') as path:
                        filepath = '{}{}{}'.format(path, os.sep, '.temp.db')
                        m.download(filepath)
                        db_session.merge_db(filepath)
                        os.remove(path)
                    return db_session.get_channel()
    except Exception as E:
        print(E)
        return None



def upload_db():
    with PathMaker('.temp') as path:
        filepath = db_session.export_db('{}{}{}'.format(path, os.sep, 'temp.db'))
    while True:
        try:
            old_msg = db_session.get_last_backup_id()
            msg_id = client.send_document(db_session.get_channel()[0], filepath).message_id
            db_session.set_last_backup_id(msg_id)
        except pyrogram.RPCError:
            continue

        else:
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
    file = client.send_document(db_session.get_channel()[0], document=file, progress=upload_callback)
    db_session.add_file(
        file.document.file_id,
        file_name=file_name,
        file_tags=tags,
        folder_name=to_folder,
        message_id=file.message_id)
    upload_db()


def check_channel(channel_id):
    if channel_id is None:
        return False
    chat_id, access_hash = channel_id

    try:
        chat = client.get_chat(chat_id)
    except (ValueError, pyrogram.RPCError):
        return False
    if chat.title != chat_title or \
            chat.description != chat_desc:
        client.set_chat_description(chat_id, chat_desc)
        client.set_chat_title(chat_id, chat_title)
    return chat


def phone_handler():
    pass


def code_handler():
    pass


def password_handler():
    pass


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
    db_session.add_folder('testf')
    upload_file('testfile2', ['test1', 'kek', '42'], 'testf', 'D:/grief.wav')
    client.stop()  # on app exit


if __name__ == '__main__':
    api_id = 576793
    api_hash = '2458f89fda1ae88bed1ce71375a2a7cb'
    session_file = 'TeleCloud'
    client = Client(session_file,
                    device_model=platform.system(),
                    app_version=__version__,
                    api_id=api_id,
                    api_hash=api_hash,
                    test_mode=False)
    client.start()
    db_session = Session(session_file)
    chat_title = 'TelegramCloudApp'
    chat_desc = 'TelegramCloudApp of {}! Don\'t change name or description!'.format(client.get_me().id)
    chat_photo = 'logo.png'
    init_login()
