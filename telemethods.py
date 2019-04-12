from pyrogram import Client, __version__
from pyrogram.api.functions import channels
from pyrogram.api.types import MessageMediaDocument
import os
from dbmethods import Session
import platform


def find_cloud_by_name(input_title):
    total = client.get_dialogs(limit=0).total_count
    for x, i in enumerate(client.iter_dialogs()):
        print('{}/{}'.format(x, total))
        if i.chat.title == input_title:
            if load_db(i.chat.id):
                return db_session.get_channel()


def find_cloud_by_backup():
    total = client.get_dialogs(limit=0).total_count
    for x, i in enumerate(client.iter_dialogs()):
        print('{}/{}'.format(x, total))
        if load_db(i.chat.id):
            return db_session.get_channel()


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
        session_filename = sessions[inp - 1] if inp != -1 else input('new session name: ')
    else:
        session_filename = input('new session name: ')
    return session_filename


def load_db(chat_id):
    try:
        for x, m in enumerate(client.iter_history(chat_id, limit=11)):
            if m.document:
                if m.document.file_name.endswith('.tgdb'):
                    m.download('temp_db')
                    db_session.merge_db('temp.db')
                    return db_session.get_channel()
    except:
        return None


def upload_callback(client: Client, current, total):
    pass


def upload_file(path):
    return client.send_document(db_session.get_channel()[0], path, progress=upload_callback).document


def save_file(document: MessageMediaDocument.document, tags, to_folder):
    db_session.add_file(document.file_id, document.file_name, file_tags=tags, folder_name=to_folder)


def check_channel(channel_id):
    if channel_id is None:
        return False
    chat_id, access_hash = channel_id
    try:

        a = client.send(channels.GetFullChannel(channel=client.resolve_peer(chat_id)))
        return a
    except:
        return False

def phone_handler():
    pass


def code_handler():
    pass


def password_handler():
    pass


def init_login():
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
            db_session.set_channel(int('-100' + str(channel.id)), channel.access_hash)

        channel_id = db_session.get_channel()


    upload_file('.gitignore')
    client.stop()  # on app exit


if __name__ == '__main__':
    api_id = 576793
    api_hash = '2458f89fda1ae88bed1ce71375a2a7cb'
    session_file = manage_session()
    client = Client(session_file,
                    device_model=platform.system(),
                    app_version=__version__,
                    api_id=api_id,
                    api_hash=api_hash,
                    test_mode=False)
    client.start()
    db_session = Session(session_file)
    init_login()
