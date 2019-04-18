from pyrogram import __version__
from pyrogram.api.functions import channels
import pyrogram

from dbmethods import Session
import platform
from login import phone_number, telegram_code, two_factor_auth, please_wait
from telecloudutils import split_into_parts, const_max_size
from teleclouderrors import FileDuplicateError, FolderMissingError
from pyrewrite import TeleCloudClient
import os, tempfile, time, shutil
from tempfile import TemporaryDirectory


class TeleCloudApp:
    def __init__(self):
        api_id = 576793
        api_hash = '2458f89fda1ae88bed1ce71375a2a7cb'
        session_file = 'TeleClouda'
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
        self.db_session: Session = Session(session_file, self.client.get_me().id)
        self.chat_title = 'TelegramCloudApp'
        self.chat_desc = 'TelegramCloudApp of {}! Don\'t change this description!'.format(self.client.get_me().id)
        self.chat_photo = 'gui/logo.png'
        self.local_dir = 'TeleCloudFolders/'
        self.ret_channel = please_wait(self.init_login)

    def find_cloud_by_name(self):
        total = self.client.get_dialogs(limit=0).total_count
        for x, i in enumerate(self.client.iter_dialogs()):
            while True:
                try:
                    if i.chat.type == 'channel':
                        try:
                            i = self.client.get_chat(i.chat.id)
                        except pyrogram.errors.ChannelPrivate:
                            break
                        if i.description == self.chat_desc:

                            if not self.load_db(i.id):
                                peer = self.client.resolve_peer(i.id)
                                self.db_session.set_channel(int('-100' + str(peer.channel_id)), peer.access_hash)
                            return self.db_session.get_channel()
                    break
                except pyrogram.errors.FloodWait as e:
                    time.sleep(e.x)
                    continue

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
                            res = self.client.download_media([m], file_name=os.path.join(path, 'db_instance.tgdb'))
                            self.db_session.merge_db(res)
                        return self.db_session.get_channel()

        except Exception:
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

        msg_objs = self.client.get_messages(
            chat_id=self.db_session.get_channel()[0],
            message_ids=files.message_ids
        ).messages
        self.client.download_media(
            messages=msg_objs,
            file_name=os.path.join(self.local_dir, file_folder, file_name),
            progress=self.download_callback,
            block=False)

    def download_callback(self, client, done, total):
        pass

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

            file = self.client.send_named_document(
                self.db_session.get_channel()[0],
                file_name=os.path.basename(file_name),
                documents=file_parts,
                progress=callback)

            for i in file:
                file_ids.append(i.document.file_id)
                message_ids.append(i.message_id)

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

    def remove_folder(self, folder_name):
        files = self.db_session.get_folder(folder_name)
        self.db_session.remove_folder(folder_name)
        for i in files:
            while True:
                try:
                    self.client.delete_messages(self.db_session.get_channel()[0], i.message_ids)
                    break
                except pyrogram.errors.FloodWait as e:
                    time.sleep(e.x)
                    continue

    def check_channel(self, channel_data):
        if channel_data is None:
            return False
        chat_id, access_hash = channel_data
        try:
            chat = self.client.get_chat(chat_id)
        except (ValueError, pyrogram.RPCError, pyrogram.errors.PeerIdInvalid,
                KeyError, pyrogram.errors.ChannelPrivate) as e:
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
        self.db_session.clear()
        self.db_session.set_channel(int('-100' + str(channel.id)), channel.access_hash)

    def check_connection(self):
        try:
            self.client.get_me()
            return True
        except ConnectionError:
            return False
