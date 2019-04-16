import sys
import os
from typing import Sequence
import re
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from telemethods import TeleCloudApp
from teleclouderrors import FolderMissingError, FileDuplicateError
import gui.logo


def list_lstrip(s: str, args: Sequence[str]) -> str:
    match = re.finditer(r'|'.join(re.escape(i) for i in args), s)
    start = 0
    for i in match:
        if i.span()[0] == start:
            start = i.span()[1]
        else:
            break
    return s[start:]


def list_rstrip(s: str, args: Sequence[str]) -> str:
    match = re.finditer(r'|'.join(re.escape(i[::-1]) for i in args), s[::-1])
    end = 0
    for i in match:
        if i.span()[0] == end:
            end = i.span()[1]
        else:
            break
    return s[:-end] if end != 0 else s


def list_strip(s: str, args: Sequence[str]) -> str:
    return list_rstrip(list_lstrip(s, args), args)


const_spaces_list = (
    '\n', ' ', '\xa0', '\u180e', '\u2000',
    '\u2001', '\u2002', '\u2003',
    '\u2004', '\u2005', '\u2006',
    '\u2007', '\u2008', '\u2009',
    '\u200a', '\u200b', '\u202f',
    '\u205f', '\u2063', '\u3000',
    'ㅤ', '\ufeff'
)


def get_app_instance():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# def load_project_structure(startpath, tree):
#     for element in os.listdir(startpath):
#         path_info = startpath + "/" + element
#         parent_itm = QTreeWidgetItem(tree, [os.path.basename(element)])
#         if os.path.isdir(path_info):
#             load_project_structure(path_info, parent_itm)
#             parent_itm.setIcon(0, QIcon('assets/folder.ico'))
#         else:
#             parent_itm.setIcon(0, QIcon('assets/file.ico'))


class UploadForm(QMainWindow):
    def __init__(self, ui_file, file_path, filename):
        super(UploadForm, self).__init__(parent=None)
        self.file_path = file_path
        self.filename = filename
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        self.filename_edit = self.window.findChild(QLineEdit, 'filename_edit')
        self.tags_line = self.window.findChild(QLineEdit, 'tagsEdit')
        upload_file = self.window.findChild(QCommandLinkButton, 'upload_file')
        upload_file.clicked.connect(self.handler)
        self.alert_label = self.window.findChild(QLabel, 'alertLabel')
        self.alert_label.setStyleSheet('QLabel {color: #FF0000;}')
        self.folders_list = self.window.findChild(QComboBox, 'folders_list')
        self.folders = [str(i) for i in connector.db_session.get_folders()]
        self.folders_list.addItems(self.folders)

        self.window.show()

    def handler(self):
        tags = []
        for i in self.tags_line.text().split(','):
            t = list_strip(i, const_spaces_list)
            if t:
                tags.append(t)
        try:
            self.connector.upload_file(self.file_path,
                                  self.filename,
                                  tags,
                                  self.folders_list.currentText(),
                                  self.upload_callback)
        except FolderMissingError:
            pass
        except FileDuplicateError:
            self.alert_label.setText('Файл з такою назвою вже існує')
        self.window.close()

    def upload_callback(self, client, current, total):
        self.alert_label('{} завершено з {}'.format(round(current / 1024, 3), round(total / 1024, 3)))


class FolderDialog(QMainWindow):
    def __init__(self, ui_file):
        super(FolderDialog, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        self.folder_name = self.window.findChild(QLineEdit, 'folder_name')
        create_folder = self.window.findChild(QCommandLinkButton, 'create_folder')
        create_folder.clicked.connect(self.handler)

        self.window.show()

    def handler(self):
        connector.db_session.add_folder(self.folder_name.text())
        connector.upload_db()
        self.window.close()


class NewChannelForm(QMainWindow):
    def __init__(self, ui_file):
        super(NewChannelForm, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        self.check = False

        create_channel = self.window.findChild(QCommandLinkButton, 'create_channel')
        create_channel.clicked.connect(self.handler)

        self.window.show()

    def handler(self):
        connector.create_and_set_channel()
        self.check = True
        self.window.close()


class NewOrExistingChannelForm(QMainWindow):
    def __init__(self, ui_file):
        super(NewOrExistingChannelForm, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        existing_channel_button = self.window.findChild(QCommandLinkButton, 'existing_channel')
        existing_channel_button.clicked.connect(self.existing_handler)
        create_channel_button = self.window.findChild(QCommandLinkButton, 'create_channel')
        create_channel_button.clicked.connect(self.create_handler)
        self.window.show()

        def existing_handler(self):
            self.window.close()

        def create_handler(self):
            self.window.hide()
            connector.create_and_set_channel()
            self.window.close()


class MainWindow(QMainWindow):
    def __init__(self, ui_file):
        super(MainWindow, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        upload_button = self.window.findChild(QPushButton, 'upload_button')
        upload_button.clicked.connect(self.upload_handler)
        folder_create = self.window.findChild(QPushButton, 'folder_create')
        folder_create.clicked.connect(self.folder_handler)
        search_button = self.window.findChild(QPushButton, 'search_button')
        search_button.clicked.connect(self.search_handler)
        self.search_line = self.window.findChild(QLineEdit, 'search_line')
        cancel_search_button = self.window.findChild(QToolButton, 'cancel_search_button')
        cancel_search_button.clicked.connect(self.cancel_search_handler)

        self.latest_folders = connector.db_session.get_folders()
        self.latest_files = [i.ret() for i in self.latest_folders]
        self.refresh(first=True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.setInterval(3000)
        self.timer.start()

        self.window.show()

    def upload_handler(self):
        self.dialog = QFileDialog()
        self.file_path = self.dialog.getOpenFileName()
        filename = os.path.basename(self.file_path[0])
        if self.file_path[0] != '':
            self.uploadform = UploadForm('gui/file_upload.ui', self.file_path[0], filename)
            self.uploadform.filename_edit.setText(filename)

    def folder_handler(self):
        self.folderdialog = FolderDialog('gui/folder_dialog.ui')

    def refresh(self, first=False):
        folders_list = connector.db_session.get_folders()
        latest_files = [i.ret() for i in folders_list]
        if not first and (
                [str(i) for i in folders_list] == [str(i) for i in self.latest_folders] and
                ''.join(str(i) for i in latest_files) == ''.join(str(i) for i in self.latest_files)):
            return
        else:
            self.latest_folders = folders_list
            self.latest_files = latest_files
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Name', 'Size', 'Total elements', 'Type'])
        self.tree_view = self.window.findChild(QTreeView, 'treeView')
        self.tree_view.setModel(self.model)
        self.tree_view.setUniformRowHeights(True)
        for folder in folders_list:
            parent1 = QStandardItem(folder.name)
            parent1.setEditable(False)
            parent2 = QStandardItem(str(round(folder.size / 1024, 3)) + ' KB')
            parent2.setEditable(False)
            parent3 = QStandardItem(str(folder.total))
            parent3.setEditable(False)
            parent4 = QStandardItem('Папка')
            parent4.setEditable(False)
            for file in folder:
                child1 = QStandardItem(file.name)
                child1.setEditable(False)
                child2 = QStandardItem(str(round(file.size / 1024, 3)) + ' KB')
                child2.setEditable(False)
                child3 = QStandardItem('')
                child3.setEditable(False)
                child4 = QStandardItem(os.path.splitext(file.name)[-1])
                child4.setEditable(False)
                parent1.appendRow([child1, child2, child3, child4])
            self.model.appendRow([parent1, parent2, parent3, parent4])
            index = self.model.indexFromItem(parent1)
            self.tree_view.expand(index)

    def search_handler(self):
        text = self.search_line.text()
        found_files = connector.db_session.search_file(text.split())
        print(found_files)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Name', 'Size', 'Total elements', 'Type'])
        self.tree_view = self.window.findChild(QTreeView, 'treeView')
        self.tree_view.setModel(self.model)
        self.tree_view.setUniformRowHeights(True)
        for file in found_files:
            parent1 = QStandardItem(file.name)
            parent1.setEditable(False)
            parent2 = QStandardItem(str(round(file.size / 1024, 3)) + ' KB')
            parent2.setEditable(False)
            parent3 = QStandardItem('')
            parent3.setEditable(False)
            parent4 = QStandardItem(os.path.splitext(file.name)[-1])
            parent4.setEditable(False)
            self.model.appendRow([parent1, parent2, parent3, parent4])
            index = self.model.indexFromItem(parent1)
            self.tree_view.expand(index)
        self.timer.stop()

    def cancel_search_handler(self):
        self.search_line.setText('')
        self.refresh(first=True)
        self.dialog = QFileDialog()
        self.timer.timeout.connect(self.refresh)
        self.timer.setInterval(3000)
        self.timer.start()


def client_exit():
    connector.client.stop()
    sys.exit()


def new_channel():
    app = get_app_instance()
    newchannelform = NewChannelForm('gui/create_channel.ui')
    app.exec_()
    if not newchannelform.check:
        client_exit()


def existing_channel():
    app = get_app_instance()
    existingchannelform = NewOrExistingChannelForm('gui/existing_channel.ui')
    app.exec_()


def main_window():
    app = get_app_instance()
    mainwindow = MainWindow('gui/main.ui')
    app.exec_()


if __name__ == "__main__":
    connector = None
    try:
        connector = TeleCloudApp()
        if connector.ret_channel == 0:
            pass
        elif connector.ret_channel == 1:
            existing_channel()
        elif connector.ret_channel == 2:
            new_channel()
        main_window()
    except Exception as e:
        raise e
    finally:
        client_exit()
