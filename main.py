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
import json
from login import Worker


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
    def __init__(self, ui_file, file_path, filename, main):
        super(UploadForm, self).__init__(parent=None)
        self.main = main
        self.file_path = file_path
        self.filename = filename
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)

        ui_file.close()
        self.threadpool = QThreadPool()

        self.filename_edit = self.window.findChild(QLineEdit, 'filename_edit')
        self.filename_edit.textChanged.connect(self.check_if_exists)
        self.tags_line = self.window.findChild(QLineEdit, 'tagsEdit')
        self.upload_file = self.window.findChild(QCommandLinkButton, 'upload_file')
        self.upload_file.clicked.connect(self.handler)
        self.alert_label = self.window.findChild(QLabel, 'alertLabel')
        self.alert_label.setStyleSheet('QLabel {color: #FF0000;}')
        self.folders_list = self.window.findChild(QComboBox, 'folders_list')
        self.folders_list.addItems([str(i) for i in connector.db_session.get_folders()])
        self.progress_bar = self.window.findChild(QProgressBar, 'progressBar')
        self.worker = None
        self.window.show()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check)
        self.timer.setInterval(300)
        self.timer.start()

    def check_if_exists(self, cur):
        if connector.db_session.check_file_exists(cur, self.folders_list.currentText()):
            self.alert_label.setText('Файл з такою назвою вже існує')
            self.upload_file.setEnabled(False)
        else:
            self.alert_label.setText('')
            self.upload_file.setEnabled(True)

    def check(self):
        thr = self.threadpool.activeThreadCount()
        print(thr)
        if self.worker is not None and thr == 0:
            print('close')
            self.ret = self.worker.ret
            self.window.removeEventFilter(self)
            self.window.close()
            self.main.upload_button.setEnabled(True)
            self.timer.stop()
        else:
            self.main.upload_button.setEnabled(False)


    def handler(self):
        tags = []
        for i in self.tags_line.text().split(','):
            t = list_strip(i, const_spaces_list)
            if t:
                tags.append(t)
        try:
            self.main.upload_button.setEnabled(False)
            self.alert_label.setText('Зачекайте, йде підготовка файлу...')
            self.worker = Worker(connector.upload_file, self.file_path,
                                 self.filename_edit.text(),
                                 tags,
                                 self.folders_list.currentText(),
                                 self.upload_callback)

            self.threadpool.start(self.worker)

        except FolderMissingError:
            self.main.upload_button.setEnabled(False)
        except FileDuplicateError:
            self.alert_label.setText('Файл з такою назвою вже існує')
            self.main.upload_button.setEnabled(False)

    def upload_callback(self, client, current, total):
        print(current, total, sep='/')
        self.progress_bar.setValue((current / total) * 100)
        if current == total:
            self.window.close()


class FolderDialog(QMainWindow):
    def __init__(self, ui_file):
        super(FolderDialog, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        self.folder_name = self.window.findChild(QLineEdit, 'folder_name')
        self.folder_name.textChanged.connect(self.empty_check)
        self.create_folder = self.window.findChild(QCommandLinkButton, 'create_folder')
        self.create_folder.clicked.connect(self.handler)

        self.window.show()

    def handler(self):
        connector.db_session.add_folder(self.folder_name.text())
        connector.upload_db()
        self.window.close()

    def empty_check(self):
        if self.folder_name.text() == '':
            self.create_folder.setEnabled(False)
        else:
            self.create_folder.setEnabled(True)


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

        self.upload_button = self.window.findChild(QPushButton, 'upload_button')
        folder_create = self.window.findChild(QPushButton, 'folder_create')
        print(connector.db_session.get_folders())
        self.upload_button.clicked.connect(self.folders_exist)

        folder_create.clicked.connect(self.folder_handler)
        search_button = self.window.findChild(QPushButton, 'search_button')
        search_button.clicked.connect(self.search_handler)
        self.search_line = self.window.findChild(QLineEdit, 'search_line')
        cancel_search_button = self.window.findChild(QToolButton, 'cancel_search_button')
        cancel_search_button.clicked.connect(self.cancel_search_handler)
        self.download_button = self.window.findChild(QPushButton, 'download_button')
        self.download_button.clicked.connect(self.download)
        self.items = []

        self.latest_folders = connector.db_session.get_folders()
        self.latest_files = [i.ret() for i in self.latest_folders]
        self.refresh(first=True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.setInterval(3000)
        self.timer.start()

        self.timer_check = QTimer(self)
        self.timer_check.timeout.connect(self.get_checked)
        self.timer_check.setInterval(100)
        self.timer_check.start()

        self.timer_select = QTimer(self)
        self.timer_select.timeout.connect(self.get_selected)
        self.timer_select.setInterval(1000)
        self.timer_select.start()

        self.window.show()

    def folders_exist(self):
        if not connector.db_session.get_folders():
            self.folder_handler()
        else:
            self.upload_handler()

    def upload_handler(self):
        self.dialog = QFileDialog()
        self.file_path = self.dialog.getOpenFileName()
        filename = os.path.basename(self.file_path[0])
        if self.file_path[0] != '':
            self.uploadform = UploadForm('gui/file_upload.ui', self.file_path[0], filename, self)
            self.uploadform.filename_edit.setText(filename)

    def folder_handler(self):
        self.folderdialog = FolderDialog('gui/folder_dialog.ui')
        if connector.db_session.get_folders():
            self.upload_button.clicked.connect(self.upload_handler)

    def refresh(self, first=False):
        folders_list = connector.db_session.get_folders()
        latest_files = [i.ret() for i in folders_list]
        if not first and (
                [str(i) for i in folders_list] == [str(i) for i in self.latest_folders] and
                ''.join(str(i) for i in latest_files) == ''.join(str(i) for i in self.latest_files)):
            return
        else:
            self.items = []
            self.latest_folders = folders_list
            self.latest_files = latest_files
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Name', 'Size', 'Total elements', 'Type'])
        self.tree_view = self.window.findChild(QTreeView, 'treeView')
        self.tree_view.setModel(self.model)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setColumnWidth(0, 300)
        for folder in folders_list:
            parent1 = QStandardItem(folder.name)
            parent1.setEditable(False)
            parent1.setCheckable(True)
            parent1.setIcon(QIcon('gui/folder.ico'))
            parent2 = QStandardItem(str(round(folder.size / 1024, 3)) + ' KB')
            parent2.setEditable(False)
            parent3 = QStandardItem(str(folder.total))
            parent3.setEditable(False)
            parent4 = QStandardItem('Папка')
            parent4.setEditable(False)
            for file in folder:
                child1 = QStandardItem(file.name)
                child1.setEditable(False)
                child1.setCheckable(True)
                child1.setIcon(QIcon('gui/file.ico'))
                self.items.append(child1)
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
        self.timer_check.stop()

    def cancel_search_handler(self):
        self.search_line.setText('')
        self.refresh(first=True)
        self.dialog = QFileDialog()
        self.timer.timeout.connect(self.refresh)
        self.timer.setInterval(3000)
        self.timer.start()
        self.timer_check.start()

    def get_selected(self):
        # if self.tree_view.selectedIndexes() != []:
        #     row = self.tree_view.selectedIndexes()[0].row()
        #     print(self.tree_view.selectedIndexes()[0].model().item(row).parent().text())
        #     if self.tree_view.selectedIndexes()[0].model().item(row).parent() != -1:
        #         print(self.tree_view.selectedIndexes()[0].model().item(row).text())
        #         #print(self.tree_view.selectedIndexes()[0].parent().model().text())
        pass

    def get_checked(self):
        checked_items = []
        for i in self.items:
            if i.checkState() == Qt.Checked:
                checked_items.append([str(i.text()), str(i.parent().text()), i])
        self.download_button.setEnabled(True if len(checked_items) > 0 else False)
        return checked_items

    def download(self):
        for i in self.get_checked():
            i[2].setCheckState(Qt.Unchecked)
            connector.download_file(i[0], i[1])


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
        try:
            connector = TeleCloudApp()
        except json.JSONDecodeError:
            os.remove('TeleCloud.session')
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
