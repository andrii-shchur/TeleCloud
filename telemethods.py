import string
from pyrogram import Client, MessageHandler, __version__
from pyrogram.api.functions import channels
from pyrogram.api.errors import AuthKeyUnregistered, AuthKeyDuplicated
from pyrogram.api.types import InputPeerChannel, InputPeerChat, InputPeerUser, InputPeerSelf
import platform
import os
from time import sleep
from dbmethods import Session


def find_cloud_by_name(input_title):
    total = client.get_dialogs(limit=0).total_count
    for x, i in enumerate(client.iter_dialogs()):
        print('{}/{}'.format(x, total))
        if i.chat.title == input_title:
            if load_db(i.chat.id):
                return client.resolve_peer(i.chat.id)


def find_cloud_by_backup():
    total = client.get_dialogs(limit=0).total_count
    for x, i in enumerate(client.iter_dialogs()):
        print('{}/{}'.format(x, total))
        if load_db(i.chat.id):
            return client.resolve_peer(i.chat.id)


def create_cloud_channel(input_title):
    return client.send(channels.CreateChannel(title=input_title, about='', broadcast=True))


def manage_session():
    sessions = [os.path.splitext(file)[-2] for file in os.listdir(os.path.curdir) if
                os.path.splitext(file)[-1] == '.session']
    if len(sessions) > 0:
        print('choose existing session 1-{} (-1 for new one)'.format(len(sessions)))
        for x, i in enumerate(sessions, 1):
            print('[{}] {}'.format(x, os.path.splitext(i)[-2]))
        inp = int(input())
        session_file = sessions[inp - 1] if inp != -1 else input('new session name: ')
    else:
        session_file = input('new session name: ')
    return session_file


def load_db(chat_id):
    try:
        for m in client.iter_history(chat_id, limit=10):
            if m.document:
                if m.document.file_name.endswith('.tgdb'):
                    db_file = m.download('temp_db')
                    db_session.merge_db(db_file)
                    return channel_id
    except:
        return None


def upload_file(path):
    client.send_document(channel_id, path)


def check_channel(chat_id):
    if chat_id is None:
        return False
    try:
        return client.send(channels.GetChannels([InputPeerChannel(*chat_id)]))
    except:
        return False


def phone_handler():
    pass


def code_handler():
    pass


def password_handler():
    pass


if __name__ == '__main__':
    api_id = 576793
    api_hash = '2458f89fda1ae88bed1ce71375a2a7cb'
    # session_file = manage_session()
    session_file = 'test_session'
    client = Client(session_file, device_model=platform.system(), app_version=__version__, api_id=api_id,
                    api_hash=api_hash, test_mode=True)
    client.start()
    db_session = Session(session_file)
    channel_id = db_session.get_channel()
    while not check_channel(channel_id):
        channel_id = find_cloud_by_name('TeleCloud')
        if channel_id:
            channel_id = db_session.get_channel()
        else:
            if input('try to find latest files backup automatically? ') == 'y':
                channel_id = find_cloud_by_backup()
        if not channel_id:
            channel = create_cloud_channel(input('new channel name: ')).chats[0]
            db_session.set_channel(channel.id, channel.access_hash)
            channel_id = db_session.get_channel()

    client.stop()
