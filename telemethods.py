from pyrogram import Client, __version__
from pyrogram.api.functions import channels
import pyrogram

from dbmethods import Session
import platform
from login import phone_number, telegram_code, two_factor_auth
from telecloudutils import TempFileMaker, split_into_parts, rebuild_from_parts
from pyrogram.errors import FloodWait
from teleclouderrors import UploadingError, FileDuplicateError, FolderMissingError
from pyrewrite import TeleCloudClient


class TeleCloudApp:
    def __init__(self):
        api_id = 576793
        api_hash = '2458f89fda1ae88bed1ce71375a2a7cb'
        session_file = 'TeleCloud'
        self.client = TeleCloudClient(session_file,
                                      device_model=platform.system(),
                                      app_version=__version__,
                                      api_id=api_id,
                                      api_hash=api_hash,
                                      test_mode=False,
                                      phone_code=telegram_code,
                                      phone_number=phone_number,
                                      password=two_factor_auth)

        self.client.start()
        self.db_session = Session(session_file)
        self.chat_title = 'TelegramCloudApp'
        self.chat_desc = 'TelegramCloudApp of {}! Don\'t change name or description!'.format(self.client.get_me().id)
        self.chat_photo = 'gui/logo.png'
        self.ret_channel = self.init_login()

    def find_cloud_by_name(self):
        total = self.client.get_dialogs(limit=0).total_count
        for x, i in enumerate(self.client.iter_dialogs()):
            if i.chat.type == 'channel' and i.chat.title == self.chat_title:
                full_chat = self.client.get_chat(i.chat.id)
                if full_chat.description == self.chat_title:
                    if not self.load_db(i.chat.id):
                        peer = self.client.resolve_peer(i.chat.id)
                        self.db_session.set_channel(int('-100' + str(peer.channel_id)), peer.access_hash)
                    return self.db_session.get_channel()

    def find_cloud_by_backup(self):
        total = self.client.get_dialogs(limit=0).total_count
        for x, i in enumerate(self.client.iter_dialogs()):
            print(x, total, sep='/')
            if i.chat.type == 'channel':
                if self.load_db(i.chat.id):
                    return self.db_session.get_channel()

    def create_cloud_channel(self):
        channel = self.client.send(channels.CreateChannel(
            title=self.chat_title,
            about=self.chat_title, broadcast=True))
        chat = int('-100' + str(channel.chats[0].id))

        self.client.set_chat_photo(chat, self.chat_photo)
        self.client.get_messages(chat, message_ids=[2]).messages[0].delete()
        return channel

    def load_db(self, chat_id):
        try:
            for x, m in enumerate(self.client.iter_history(chat_id, limit=11)):
                if m.document:
                    if m.document.file_name.endswith('.tgdb'):
                        with TempFileMaker() as path:
                            m.download(path.name)
                            self.db_session.merge_db(path.name)
                        return self.db_session.get_channel()
        except Exception as E:
            print(E)
            return None

    def upload_db(self):
        with TempFileMaker() as path:
            self.db_session.export_db(path.name)
        while True:
            try:
                old_msg = self.db_session.get_last_backup_id()
                msg_id = self.client.send_document(self.db_session.get_channel()[0], path.name).message_id
                self.db_session.set_last_backup_id(msg_id)
            except pyrogram.RPCError:
                continue

            if old_msg is not None:
                m = self.client.get_messages(chat_id=self.db_session.get_channel()[0], message_ids=[old_msg])
                if m.messages:
                    m.messages[0].delete() if not m.messages[0].empty else None
            break

    def save_file(self, file_id: str, to_folder):
        self.client.download_media(message=file_id, file_name=to_folder)

    def upload_callback(self, client: Client, current, total):
        print('{}/{}'.format(current, total))

    def upload_file(self, file_name, tags, to_folder, file):
        file_ids = []
        message_ids = []
        try:
            file = self.client.send_named_document(
                self.db_session.get_channel()[0],
                file_name=file_name,
                document=file,
                progress=self.upload_callback)
            file_ids.append(file.document.file_id)
            message_ids.append(file.message_id)
        except FloodWait as err:
            print(err)
        else:
            try:
                self.db_session.add_file(
                    file_ids=file_ids,
                    file_name=file_name,
                    file_tags=tags,
                    folder_name=to_folder,
                    message_ids=message_ids)
            except (FolderMissingError, FileDuplicateError):
                pass
            self.upload_db()

    def check_channel(self, channel_id):
        if channel_id is None:
            return False
        chat_id, access_hash = channel_id

        try:
            chat = self.client.get_chat(chat_id)
        except (ValueError, pyrogram.RPCError, pyrogram.errors.exceptions.bad_request_400.PeerIdInvalid) as E:
            print(E)
            return False
        self.load_db(chat.id)
        if chat.title != self.chat_title or \
                chat.description != self.chat_title:
            self.client.set_chat_description(chat_id, self.chat_title)
            self.client.set_chat_title(chat_id, self.chat_title)
        return chat

    def init_login(self):
        channel_id = self.db_session.get_channel()
        ret = None
        back_executed = False
        while not self.check_channel(channel_id):
            channel_id = self.find_cloud_by_name()
            if channel_id:
                channel_id = self.db_session.get_channel()
                ret = 0
            elif not back_executed and self.find_cloud_by_backup():
                ret = 1
                break
            if not channel_id:
                ret = 2
                break
        return ret

    def create_and_set_channel(self):
        channel = self.create_cloud_channel().chats[0]
        self.db_session.set_channel(int('-100' + str(channel.id)), channel.access_hash)
