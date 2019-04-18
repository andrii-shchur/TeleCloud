import sqlite3
import threading
from typing import List, Sequence, Tuple
from teleclouderrors import FolderMissingError, FolderDuplicateError, FileDuplicateError, FileMissingError

CONST_DATABASE_DELIMITER = '\0'

_lock = threading.RLock()


class BaseFile:
    def __init__(self, file_ids: Sequence[str], file_name: str, file_tags: Sequence[str], size: int, folder_name: str,
                 message_ids: Sequence[int], ):
        self.file_ids = file_ids.split(CONST_DATABASE_DELIMITER) if isinstance(file_ids, str) else file_ids
        self.name = str(file_name)
        self.tags = file_tags.split(CONST_DATABASE_DELIMITER) if isinstance(file_tags, str) else file_tags
        self.size = int(size)
        self.folder = str(folder_name)
        self.message_ids = [
            int(i) for i in
            (message_ids.split(CONST_DATABASE_DELIMITER) if isinstance(message_ids, str) else message_ids)
        ]

    def __repr__(self):
        return '{}: {}<{}> in {}'.format(self.__class__, self.name, ', '.join(self.tags), self.folder)

    def __iter__(self):
        return iter((self.file_ids, self.name, self.tags, self.size, self.folder, self.message_ids))


class BaseFolder:
    def __init__(self, folder_name: str, files_array: Sequence):
        self.name = folder_name
        self.storage = [f for f in files_array]
        self.total = len(self.storage)
        self.size = sum((f.size for f in self.storage))

    def __iter__(self):
        return iter(self.storage)

    def __repr__(self):
        return '{}: {}{{{}}}'.format(self.__class__, self.name, ','.join([str(f) for f in self.ret()]))

    def __str__(self):
        return self.name

    def ret(self):
        return self.storage.copy()


class Session:
    def __init__(self, session_name: str, user_id: int):
        self.session_name = session_name
        cursor = self._cursor()
        cursor.execute("SELECT NAME FROM sqlite_master WHERE TYPE='table'")
        check = cursor.fetchone()
        if not check:
            with _lock:
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS Userdata(
                    versionId INTEGER,
                    userId INTEGER,
                    channelId INTEGER,
                    channelHash INTEGER,
                    lastBackupMsgId INTEGER 
                )
                """)

                cursor.execute('INSERT INTO userData VALUES((?), (?), (?), (?), (?))', (0.1, user_id, None, None, None))

                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS Files(
                    fileId TEXT,
                    fileName TEXT,
                    fileTags TEXT,
                    fileSize INTEGER,
                    folderName TEXT,
                    messageId TEXT
                )
                """)

                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS Folders(
                    folderName TEXT
                )
                """)
                self._conn.commit()

        f = self._cursor().execute('SELECT userId FROM Userdata').fetchone()
        f = int(f[0]) if f is not None else None
        if f != user_id:
            self.merge_db(':memory:')
            self.__init__(session_name, user_id)

    def _cursor(self) -> sqlite3.Cursor:
        """Asserts that the connection is open and returns session cursor"""
        if not hasattr(self, '_conn') or self._conn is None:
            self._conn = sqlite3.connect('{}.tgdb'.format(self.session_name), check_same_thread=False)
            self._conn.create_collation('ALLNOCASEIN',
                                        (lambda cell, string: 0 if string.lower() in cell.lower() else -1))
        return self._conn.cursor()

    def set_channel(self, channel_id: int, access_hash: int):
        cursor = self._cursor()
        with _lock:
            cursor.execute('UPDATE Userdata SET channelId = (?), channelHash = (?)',
                           (channel_id, access_hash,))
            self._conn.commit()

    def get_channel(self) -> Tuple[int, int]:
        cursor = self._cursor()
        cursor.execute('SELECT channelId, channelHash FROM Userdata')
        check = cursor.fetchone()
        return check if check is not None and check != (None, None) else None

    @staticmethod
    def _search_builder(query: Sequence[str]) -> str:
        builder = []
        c = True
        if len(query) < 1:
            raise ValueError
        for _ in query:
            if c:
                builder.append(
                    'SELECT * FROM Files '
                    'WHERE ((fileName == (?) COLLATE ALLNOCASEIN OR fileTags == (?) COLLATE ALLNOCASEIN)'
                )
                c = False
            else:
                builder.append(' OR (fileName == (?) COLLATE ALLNOCASEIN OR fileTags == (?) COLLATE ALLNOCASEIN)\n')
        res = ''.join(builder) + ')'
        return res

    def merge_db(self, db_file: str):
        with _lock:
            with sqlite3.connect(db_file) as conn:
                conn.backup(self._conn)
                self._conn.commit()

    def get_last_backup_id(self):
        cursor = self._cursor()
        cursor.execute('SELECT lastBackupMsgId FROM Userdata')
        check = cursor.fetchone()
        return check[0] if check is not None else check

    def set_last_backup_id(self, msg_id):

        cursor = self._cursor()
        with _lock:
            cursor.execute('UPDATE Userdata SET lastBackupMsgId = (?)',
                           (msg_id,))
            self._conn.commit()

    def export_db(self, db_file):
        with _lock:
            with sqlite3.connect(db_file) as conn:
                self._conn.backup(conn)
                conn.commit()
        return db_file

    def get_folders(self) -> List[BaseFolder]:
        cursor = self._cursor()
        cursor.execute('SELECT DISTINCT folderName from Folders')
        return [self.get_folder(f[0]) for f in cursor.fetchall()]

    def check_folder_exists(self, folder_name: (str, BaseFolder)) -> bool:
        cursor = self._cursor()
        folder_name = str(folder_name)
        cursor.execute('SELECT DISTINCT folderName from Folders WHERE folderName == (?)', (folder_name,))
        check = cursor.fetchone()
        return True if check else False

    def get_folder(self, folder_name: (str, BaseFolder), fetchmany: int = None) -> BaseFolder:
        cursor = self._cursor()
        folder_name = str(folder_name)
        if not self.check_folder_exists(folder_name):
            raise FolderMissingError
        cursor.execute('SELECT * from Files WHERE folderName == (?)', (folder_name,))
        return BaseFolder(folder_name, [BaseFile(*i) for i in cursor.fetchall()]) if not fetchmany \
            else BaseFolder(folder_name, [BaseFile(*i) for i in cursor.fetchmany(fetchmany)])

    def add_folder(self, folder_name: (str, BaseFolder)):
        cursor = self._cursor()
        folder_name = str(folder_name)
        check = self.check_folder_exists(folder_name)
        if check:
            raise FolderDuplicateError
        with _lock:
            cursor.execute('INSERT INTO Folders VALUES(?)', (folder_name,))
            self._conn.commit()
        return BaseFolder(folder_name, [])

    def get_file_by_id(self, file_ids: Sequence[int]) -> BaseFile:
        cursor = self._cursor()
        file_ids = CONST_DATABASE_DELIMITER.join([str(i) for i in file_ids])
        cursor.execute('SELECT DISTINCT * FROM FILES WHERE fileId == (?)',
                       (file_ids,))
        check = cursor.fetchone()
        return BaseFile(*check) if check else None

    def get_file_by_folder(self, file_name, folder_name):
        cursor = self._cursor()
        file_name = str(file_name)
        folder_name = str(folder_name)
        if not self.check_file_exists(file_name, folder_name):
            raise FileMissingError('')
        cursor.execute('SELECT DISTINCT * FROM FILES WHERE fileName == (?) AND folderName == (?)',
                       (file_name, folder_name))
        return BaseFile(*cursor.fetchone())

    def check_file_exists(self, file_name: str, folder_name: (str, BaseFolder)) -> bool:
        folder_name = str(folder_name)
        cursor = self._cursor()
        cursor.execute('SELECT DISTINCT * FROM FILES WHERE fileName == (?) AND folderName == (?)',
                       (file_name, folder_name))
        check = cursor.fetchone()
        return check

    def add_file(self, file_ids: Sequence[str], file_name: str, file_tags: Sequence[str], file_size: int,
                 folder_name: (str, BaseFolder), message_ids: Sequence[int]) -> BaseFile:
        cursor = self._cursor()
        folder_name = str(folder_name)

        if not self.check_folder_exists(folder_name):
            raise FolderMissingError("Missing folder: '{}'".format(folder_name))
        if self.check_file_exists(file_name, folder_name):
            raise FileDuplicateError("File '{}' already exists in folder: '{}'".format(file_name, folder_name))
        with _lock:
            cursor.execute('INSERT INTO Files VALUES(?, ?, ?, ?, ?, ?)',
                           (CONST_DATABASE_DELIMITER.join(file_ids),
                            file_name,
                            CONST_DATABASE_DELIMITER.join(file_tags),
                            file_size,
                            folder_name,
                            CONST_DATABASE_DELIMITER.join((str(i) for i in message_ids)),
                            ))
            self._conn.commit()
        return BaseFile(file_ids, file_name, file_tags, file_size, folder_name, message_ids)

    def copy_file(self, file_name, from_folder, to_folder, rewrite=False):
        cursor = self._cursor()
        from_folder = str(from_folder)
        to_folder = str(to_folder)
        file_name = str(file_name)
        if not self.check_folder_exists(from_folder):
            raise FolderMissingError("Missing folder: '{}'".format(from_folder))
        if not self.check_folder_exists(to_folder):
            raise FolderMissingError("Missing folder: '{}'".format(to_folder))
        if not self.check_file_exists(file_name, from_folder):
            raise FileMissingError("Missing file: '{}' in folder: '{}'".format(file_name, from_folder))
        target_file_exists = self.check_file_exists(file_name, to_folder)
        file = self.get_file_by_folder(file_name, from_folder)
        if rewrite and target_file_exists:
            with _lock:
                cursor.execute(
                    'UPDATE Files SET fileId = ?, fileName = ?, fileTags = ?, messageId = ?, fileSize = ? '
                    'WHERE fileName == ? AND folderName == ?',
                    (CONST_DATABASE_DELIMITER.join(file.file_ids),
                     file.name,
                     CONST_DATABASE_DELIMITER.join(file.tags),
                     CONST_DATABASE_DELIMITER.join([str(m) for m in file.message_ids]),
                     file.size,

                     file_name,
                     to_folder
                     )
                )
        elif not rewrite and target_file_exists:
            raise FileDuplicateError("File '{}' already exists in folder: '{}'".format(file_name, to_folder))
        else:
            file.folder = to_folder
            self.add_file(*file)

    def edit_file(self, file_name, folder_name, new_file_name, new_file_tags):
        cursor = self._cursor()
        with _lock:
            cursor.execute(
                'UPDATE Files SET fileName = (?), fileTags = (?) '
                'WHERE fileName == (?) AND folderName == (?)',
                (new_file_name, CONST_DATABASE_DELIMITER.join(new_file_tags), file_name, folder_name))
            self._conn.commit()

    def remove_file(self, file_name, folder_name):
        cursor = self._cursor()
        if not self.check_file_exists(file_name, folder_name):
            raise FileMissingError
        with _lock:
            cursor.execute(
                'DELETE FROM Files '
                'WHERE fileName == (?) AND folderName == (?)',
                (file_name, folder_name))
            self._conn.commit()

    def delete_file(self, file_id):
        cursor = self._cursor()
        with _lock:
            cursor.execute(
                'DELETE FROM Files'
                'WHERE fileId == (?)',
                (file_id,))
            self._conn.commit()

    def edit_folder(self, folder_name, new_folder_name):
        cursor = self._cursor()
        with _lock:
            cursor.execute(
                'UPDATE Files SET folderName = (?) '
                'WHERE folderName == (?)',
                (new_folder_name, folder_name))
            cursor.execute(
                'UPDATE Folders SET folderName = (?) '
                'WHERE folderName == (?)',
                (new_folder_name, folder_name)
            )
            self._conn.commit()

    def remove_folder(self, folder_name):
        cursor = self._cursor()
        with _lock:
            cursor.execute(
                'DELETE FROM Folders '
                'WHERE folderName == (?)',
                (folder_name,))

            cursor.execute(
                'DELETE FROM Files '
                'WHERE folderName == (?)',
                (folder_name,))

            self._conn.commit()

    def move_file(self, file_name, from_folder, to_folder, rewrite=False):
        self.copy_file(file_name, from_folder, to_folder, rewrite)
        self.remove_file(file_name, from_folder)

    def search_file(self, query):
        cursor = self._cursor()
        search_query = []
        for i in query:
            search_query.append(i)
            search_query.append(i)
        cursor.execute(
            self._search_builder(query),
            (*search_query,))
        return [BaseFile(*f) for f in cursor.fetchall()]
