from pyrogram import Client, __version__
from pyrogram.api.functions import channels
import pyrogram

from dbmethods import Session
import platform
from login import phone_number, telegram_code, two_factor_auth, PleaseWait, get_app_instance
from telecloudutils import split_into_parts, rebuild_from_parts, const_max_size
from pyrogram.errors import FloodWait
from teleclouderrors import UploadingError, FileDuplicateError, FileMissingError, FolderMissingError, \
    FolderDuplicateError
from pyrewrite import TeleCloudClient
import os, tempfile, time, shutil
from tempfile import TemporaryDirectory


class TeleCloudApp:
    def __init__(self):
        api_id = 576793
        api_hash = '2458f89fda1ae88bed1ce71375a2a7cb'
        session_file = 'TeleCloud'
        self.client = TeleCloudClient(
            session_file,
            device_model=platform.system(),
            app_version=__version__,
            api_id=api_id,
            api_hash=api_hash,
            test_mode=False,
            phone_code=telegram_code,
            phone_number=phone_number,
            password=two_factor_auth)
        try:
            self.client.start()
        except pyrogram.errors.AuthKeyUnregistered:
            import sys
            sys.exit()
        self.db_session: Session = Session(session_file)
        self.chat_title = 'TelegramCloudApp'
        self.chat_desc = 'TelegramCloudApp of {}! Don\'t change name or description!'.format(self.client.get_me().id)
        self.chat_photo = 'gui/logo.png'
        self.local_dir = 'TeleCloudFolders/'
        app = get_app_instance()
        self.pleasewait = PleaseWait('gui/please_wait.ui')
        self.pleasewait.window.show()
        self.ret_channel = self.init_login()
        self.pleasewait.window.close()
        app.exec_()

    def find_cloud_by_name(self):
        total = self.client.get_dialogs(limit=0).total_count
        for x, i in enumerate(self.client.iter_dialogs()):
            if i.chat.type == 'channel' and i.chat.description == self.chat_desc:
                if not self.load_db(i.chat.id):
                    peer = self.client.resolve_peer(i.chat.id)
                    self.db_session.set_channel(int('-100' + str(peer.channel_id)), peer.access_hash)
                return self.db_session.get_channel()

    def find_cloud_by_backup(self):
        total = self.client.get_dialogs(limit=0).total_count
        for x, i in enumerate(self.client.iter_dialogs()):
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
                        with tempfile.TemporaryDirectory() as path:
                            res = self.client.download_media(m, file_name=os.path.join(path, 'db_instance.tgdb'))
                            self.db_session.merge_db(res)
                        return self.db_session.get_channel()

        except Exception as e:
            return None

    def upload_db(self):
        while True:
            path = TemporaryDirectory()
            try:
                db_path = os.path.join(path.name, 'DATABASE_BACKUP.tgdb')
                self.db_session.export_db(db_path)
                try:
                    old_msg = None
                    for x, m in enumerate(self.client.iter_history(self.db_session.get_channel()[0], limit=11)):
                        if m.document:
                            if m.document.file_name.endswith('.tgdb'):
                                old_msg = m.message_id
                                break
                    while True:
                        try:
                            self.client.send_document(self.db_session.get_channel()[0], db_path)
                            break
                        except PermissionError:
                            time.sleep(1)
                except pyrogram.errors.FloodWait as e:
                    time.sleep(e.x)
                    continue

                if old_msg is not None:
                    m = self.client.get_messages(chat_id=self.db_session.get_channel()[0], message_ids=[old_msg])
                    if m.messages:
                        m.messages[0].delete() if not m.messages[0].empty else None
                break
            finally:
                try:
                    path.cleanup()
                except PermissionError:
                    pass

    def download_file(self, file_name, file_folder):
        files = self.db_session.get_file_by_folder(file_name, file_folder)

        parts_list = []
        with tempfile.TemporaryDirectory() as temp_dir:
            for x, msg in enumerate(files.message_ids):
                part = os.path.join(temp_dir, '{0}{0}.part'.format(x))
                msg_obj = self.client.get_messages(
                    chat_id=self.db_session.get_channel()[0],
                    message_ids=[msg]
                ).messages[0]
                self.client.download_media(
                    message=msg_obj,
                    file_name=part,
                    progress=self.upload_callback,
                    block=False)
                parts_list.append(part)
            if len(files.message_ids) > 1:
                rebuild_from_parts(os.path.join(self.local_dir, file_folder, file_name), parts_list)
            else:
                shutil.move(parts_list[0], os.path.join(self.local_dir, file_folder, file_name))

    def upload_callback(self, client: Client, current, total):
        print('{}/{}'.format(current, total))

    def upload_file(self, path, file_name, tags, to_folder, callback):
        if not self.db_session.check_folder_exists(to_folder):
            raise FolderMissingError("Missing folder: '{}'".format(to_folder))
        if self.db_session.check_file_exists(file_name, to_folder):
            raise FileDuplicateError("File '{}' already exists in folder: '{}'".format(file_name, to_folder))
        file_ids = []
        message_ids = []
        filesize = os.path.getsize(path)
        temp_dir = tempfile.TemporaryDirectory()
        try:
            if filesize <= const_max_size:

                file_cp = shutil.copy(path, temp_dir.name)
                file_parts = [file_cp]
            else:
                file_cp = shutil.copy(path, temp_dir.name)
                file_parts = split_into_parts(file_cp)

            for file_part in file_parts:
                try:
                    file = self.client.send_named_document(
                        self.db_session.get_channel()[0],
                        file_name=os.path.basename(file_part),
                        document=file_part,
                        progress=callback )
                    file_ids.append(file.document.file_id)
                    message_ids.append(file.message_id)
                except FloodWait as e:
                    print(e.x)
                    time.sleep(e.x)

            self.db_session.add_file(
                file_ids=file_ids,
                file_name=file_name,
                file_tags=tags,
                file_size=filesize,
                folder_name=to_folder,
                message_ids=message_ids)

            self.upload_db()
        finally:
            temp_dir.cleanup()

    def remove_file(self, file_name, folder_name):
        file = self.db_session.get_file_by_folder(file_name, folder_name)
        self.db_session.remove_file(file_name, folder_name)
        if not self.db_session.get_file_by_id(file.file_ids):
            self.client.delete_messages(self.db_session.get_channel()[0], file.message_ids)

    def check_channel(self, channel_data):
        if channel_data is None:
            return False
        chat_id, access_hash = channel_data
        try:
            chat = self.client.get_chat(chat_id)
        except (ValueError, pyrogram.RPCError, pyrogram.errors.PeerIdInvalid) as e:
            print(e)
            return False
        self.load_db(chat.id)
        if chat.description != self.chat_desc:
            self.client.set_chat_description(chat_id, self.chat_desc)

        return chat

    def init_login(self):
        channel_id = self.db_session.get_channel()
        ret = 0
        while not self.check_channel(channel_id):
            if self.find_cloud_by_name():
                ret = 0
                break
            elif self.find_cloud_by_backup():
                ret = 1
                break
            else:
                ret = 2
                break
        return ret

    def create_and_set_channel(self):
        channel = self.create_cloud_channel().chats[0]
        self.db_session.set_channel(int('-100' + str(channel.id)), channel.access_hash)

    def check_connection(self):
        try:
            self.client.get_me()
            return True
        except ConnectionError:
            return False
