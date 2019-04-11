import sqlite3
import threading
from typing import Sequence

CONST_DATABASE_DELIMITER = '\0'

_lock = threading.RLock()


class FolderMissingError(Exception):
    pass


class FileDuplicateError(Exception):
    pass


class BaseFolderDummy():
    def __init__(self, folder_name):
        self.name = str(folder_name)

    def __repr__(self):
        return '{}: {}'.format(self.__class__, self.name)

    def __str__(self):
        return self.name


class BaseFile():
    def __init__(self, file_id: str, file_name: str, file_tags: str, folder_name: str):
        self.file_id = file_id
        self.name = str(file_name)
        self.tags = file_tags.split(CONST_DATABASE_DELIMITER) if isinstance(file_tags, str) else file_tags
        self.folder = str(folder_name)

    def __repr__(self):
        return '{}: {}<{}> in {}'.format(self.__class__, self.name, ', '.join(self.tags), self.folder)


class BaseFileDummy():
    def __init__(self):
        pass

    def __str__(self):
        return str(self.__class__)


class BaseFolder(BaseFolderDummy):
    def __init__(self, folder_name: str, files_array: Sequence):
        super(BaseFolder, self).__init__(folder_name)
        self.storage = [i for i in files_array]

    def __iter__(self):
        return iter(self.storage)

    def __repr__(self):
        return '{}: {}[{}]'.format(self.__class__, self.name, ','.join(self.ret()))

    def ret(self):
        return self.storage.copy()


class Session():
    def __init__(self, session_name):
        self._conn: sqlite3.Connection = None
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
                    channelId INTEGER,
                    channelHash INTEGER 
                )
                """)
                cursor.execute('INSERT INTO userData VALUES((?), (?), (?))', (0.1, None, None))
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS Files(
                    fileId TEXT,
                    fileName TEXT,
                    fileTags TEXT,
                    folderName TEXT
                )
                """)

                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS Folders(
                    folderName TEXT
                )
                """)
                self._conn.commit()

    def _cursor(self):
        """Asserts that the connection is open and returns session cursor"""
        if self._conn is None:
            self._conn = sqlite3.connect('{}.db'.format(self.session_name), check_same_thread=False)
            self._conn.create_collation('ALLNOCASEIN',
                                        (lambda cell, string: 0 if string.lower() in cell.lower() else -1))
        return self._conn.cursor()

    def set_channel(self, channel_id, access_hash):
        cursor = self._cursor()
        with _lock:
            cursor.execute('UPDATE Userdata SET channelId = (?), channelHash = (?)',
                           (channel_id, access_hash,))
            self._conn.commit()

    def get_channel(self):
        cursor = self._cursor()
        cursor.execute('SELECT channelId, channelHash FROM Userdata')
        check = cursor.fetchall()
        return check[0] if check else None

    @staticmethod
    def search_builder(query: Sequence[str]) -> str:
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
                builder.append(' AND (fileName == (?) COLLATE ALLNOCASEIN OR fileTags == (?) COLLATE ALLNOCASEIN)\n')
        res = ''.join(builder) + ')'
        return res

    def merge_db(self, db_file: str):
        conn = sqlite3.connect(db_file)
        conn.backup(self._conn)
        self._conn.commit()
        conn.close()

    def get_folders(self):
        cursor = self._cursor()
        cursor.execute('SELECT DISTINCT folderName from Folders')
        return [BaseFolderDummy(f[0]) for f in cursor.fetchall()]

    def get_folder(self, folder_name: (str, BaseFolderDummy)):
        cursor = self._cursor()
        folder_name = str(folder_name)
        cursor.execute('SELECT DISTINCT folderName from Folders WHERE folderName == (?)', (folder_name,))
        check = cursor.fetchone()
        return BaseFolderDummy(check[0]) if check else None

    def get_folder_files(self, folder_name: (str, BaseFolderDummy), fetchmany: int = None):
        cursor = self._cursor()
        folder_name = str(folder_name)
        cursor.execute('SELECT * from Files WHERE folderName == (?)', (folder_name,))

        return BaseFolder(folder_name, [BaseFile(*i) for i in cursor.fetchall()]) if not fetchmany \
            else BaseFolder(folder_name, [BaseFile(*i) for i in cursor.fetchmany(fetchmany)])

    def add_folder(self, folder_name: (str, BaseFolderDummy)):
        cursor = self._cursor()
        folder_name = str(folder_name)
        check = self.get_folder(folder_name)
        if check:
            return False
        cursor.execute('INSERT INTO Folders VALUES(?)', (folder_name,))
        self._conn.commit()
        return BaseFolder(folder_name, [BaseFileDummy()])

    def get_file(self, file_id):
        cursor = self._cursor()
        cursor.execute('SELECT DISTINCT * FROM FILES WHERE fileId == (?)',
                       (file_id,))
        check = cursor.fetchone()
        return BaseFile(*check) if check else None

    def check_file_exists(self, file_name, folder_name):
        folder_name = str(folder_name)
        cursor = self._cursor()
        cursor.execute('SELECT DISTINCT * FROM FILES WHERE fileName == (?) AND folderName == (?)',
                       (file_name, folder_name))
        check = cursor.fetchone()
        return check

    def add_file(self, file_id, file_name, file_tags: (list, tuple), folder_name: (str, BaseFolderDummy)):
        cursor = self._cursor()
        folder_name = str(folder_name)

        if not self.get_folder(folder_name):
            raise FolderMissingError("Missing folder: '{}'".format(folder_name))
        if self.check_file_exists(file_name, folder_name):
            raise FileDuplicateError("File '{}' already exists in folder: '{}'".format(file_name, folder_name))

        cursor.execute('INSERT INTO Files VALUES(?, ?, ?, ?)',
                       (file_id, file_name, CONST_DATABASE_DELIMITER.join(file_tags), folder_name))
        self._conn.commit()
        return BaseFile(file_id, file_name, file_tags, folder_name)

    def search_file(self, query):
        cursor = self._cursor()
        search_query = []
        for i in query:
            search_query.append(i)
            search_query.append(i)
        cursor.execute(self.search_builder(query), (search_query))
        return cursor.fetchall()
