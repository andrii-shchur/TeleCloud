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
            connector.upload_file(self.file_path, self.filename, tags, self.folders_list.currentText())
        except FolderMissingError:
            pass
        except FileDuplicateError:
            self.alert_label.setText('Файл з такою назвою вже існує')


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

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Name', 'Size', 'Total elements'])
        self.tree_view = self.window.findChild(QTreeView, 'treeView')
        self.tree_view.setModel(self.model)
        self.tree_view.setUniformRowHeights(True)

        upload_button = self.window.findChild(QPushButton, 'upload_button')
        upload_button.clicked.connect(self.upload_handler)
        folder_create = self.window.findChild(QPushButton, 'folder_create')
        folder_create.clicked.connect(self.folder_handler)

        for folder in connector.db_session.get_folders():
            parent1 = QStandardItem(folder.name)
            parent2 = QStandardItem(str(folder.size) + ' bytes')
            parent3 = QStandardItem(str(folder.total))
            for file in folder:
                child1 = QStandardItem(file.name)
                child2 = QStandardItem(str(file.size) + ' bytes')
                child3 = QStandardItem('')
                parent1.appendRow([child1, child2, child3])
            self.model.appendRow([parent1, parent2, parent3])
            # self.tree_view.setFirstColumnSpanned(folder, self.tree_view.rootIndex(), True)
            index = self.model.indexFromItem(parent1)
            self.tree_view.expand(index)

        # selmod = self.tree_view.selectionModel()
        # index2 = self.model.indexFromItem(child3)
        # selmod.select(index2, QItemSelectionModel.Select | QItemSelectionModel.Rows)

        self.window.show()

    def upload_handler(self):
        self.dialog = QFileDialog()
        # self.dialog.show()
        self.file_path = self.dialog.getOpenFileName()
        filename = os.path.basename(self.file_path[0])
        self.uploadform = UploadForm('gui/file_upload.ui', self.file_path[0], filename)
        self.uploadform.filename_edit.setText(filename)

    def folder_handler(self):
        self.folderdialog = FolderDialog('gui/folder_dialog.ui')


def client_exit():
    connector.client.stop()
    sys.exit()


def new_channel():
    app = get_app_instance()
    newchannelform = NewChannelForm('gui/create_channel.ui')
    if not newchannelform.check:
        client_exit()
    app.exec_()


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
        print(True)
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
        if connector:
            try:
                connector.client.stop()
            except ConnectionError:
                pass
