import sqlite3
import threading
from typing import List, Sequence, Tuple

CONST_DATABASE_DELIMITER = '\0'

_lock = threading.RLock()


class FolderMissingError(Exception):
    pass


class FileDuplicateError(Exception):
    pass


class BaseFile:
    def __init__(self, file_id: str, file_name: str, file_tags: (str, Sequence[str]), folder_name: str):
        self.file_id = file_id
        self.name = str(file_name)
        self.tags = file_tags.split(CONST_DATABASE_DELIMITER) if isinstance(file_tags, str) else file_tags
        self.folder = str(folder_name)

    def __repr__(self):
        return '{}: {}<{}> in {}'.format(self.__class__, self.name, ', '.join(self.tags), self.folder)


class BaseFolder:
    def __init__(self, folder_name: str, files_array: Sequence):
        self.name = folder_name
        self.storage = [i for i in files_array]

    def __iter__(self):
        return iter(self.storage)

    def __repr__(self):
        return '{}: {}{{{}}}'.format(self.__class__, self.name, ','.join([str(f) for f in self.ret()]))

    def __str__(self):
        return self.name

    def ret(self):
        return self.storage.copy()


class Session:
    def __init__(self, session_name: str):
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

    def _cursor(self) -> sqlite3.Cursor:
        """Asserts that the connection is open and returns session cursor"""
        if not hasattr(self, '_conn') or self._conn is None:
            self._conn = sqlite3.connect('{}.db'.format(self.session_name), check_same_thread=False)
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
        check = cursor.fetchall()
        return check[0] if check != (None, None) else None

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
                builder.append(' AND (fileName == (?) COLLATE ALLNOCASEIN OR fileTags == (?) COLLATE ALLNOCASEIN)\n')
        res = ''.join(builder) + ')'
        return res

    def merge_db(self, db_file: str):
        conn = sqlite3.connect(db_file)
        conn.backup(self._conn)
        self._conn.commit()
        conn.close()

    def get_folders(self) -> List[BaseFolder]:
        cursor = self._cursor()
        cursor.execute('SELECT DISTINCT folderName from Folders')
        return [self.get_folder(f[0]) for f in cursor.fetchall()]

    def _check_folder_exists(self, folder_name: (str, BaseFolder)) -> bool:
        cursor = self._cursor()
        folder_name = str(folder_name)
        cursor.execute('SELECT DISTINCT folderName from Folders WHERE folderName == (?)', (folder_name,))
        check = cursor.fetchone()
        return True if check else False

    def get_folder(self, folder_name: (str, BaseFolder), fetchmany: int = None) -> BaseFolder:
        cursor = self._cursor()
        folder_name = str(folder_name)
        cursor.execute('SELECT * from Files WHERE folderName == (?)', (folder_name,))
        if not self._check_folder_exists(folder_name):
            raise FolderMissingError
        return BaseFolder(folder_name, [BaseFile(*i) for i in cursor.fetchall()]) if not fetchmany \
            else BaseFolder(folder_name, [BaseFile(*i) for i in cursor.fetchmany(fetchmany)])

    def add_folder(self, folder_name: (str, BaseFolder)):
        cursor = self._cursor()
        folder_name = str(folder_name)
        check = self._check_folder_exists(folder_name)
        if check:
            return False
        cursor.execute('INSERT INTO Folders VALUES(?)', (folder_name,))
        self._conn.commit()
        return BaseFolder(folder_name, [])

    def get_file(self, file_id: int) -> BaseFile:
        cursor = self._cursor()
        cursor.execute('SELECT DISTINCT * FROM FILES WHERE fileId == (?)',
                       (file_id,))
        check = cursor.fetchone()
        return BaseFile(*check) if check else None

    def _check_file_exists(self, file_name: str, folder_name: (str, BaseFolder)) -> bool:
        folder_name = str(folder_name)
        cursor = self._cursor()
        cursor.execute('SELECT DISTINCT * FROM FILES WHERE fileName == (?) AND folderName == (?)',
                       (file_name, folder_name))
        check = cursor.fetchone()
        return check

    def add_file(self, file_id, file_name, file_tags: (list, tuple), folder_name: (str, BaseFolder)) -> BaseFile:
        cursor = self._cursor()
        folder_name = str(folder_name)

        if not self._check_folder_exists(folder_name):
            raise FolderMissingError("Missing folder: '{}'".format(folder_name))
        if self._check_file_exists(file_name, folder_name):
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
        cursor.execute(
            self._search_builder(query),
            (*search_query,))
        return [BaseFile(*f) for f in cursor.fetchall()]
