import sys
import os
from PySide2.QtUiTools import QUiLoader
from PySide2.QtXml import __loader__
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from telemethods import TeleCloudApp
from teleclouderrors import FolderMissingError, FileDuplicateError
from telecloudutils import resource_path
import gui.logo
import json
from login import Worker
from dbmethods import BaseFile, BaseFolder


def get_app_instance():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class EditFolder(QMainWindow):
    def __init__(self, ui_file, folder_name):
        super(EditFolder, self).__init__(parent=None)
        self.folder_name = folder_name
        ui_file = QFile(resource_path(ui_file))
        ui_file.open(QFile.ReadOnly)
        self.old_name = folder_name
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        self.line = self.window.findChild(QLineEdit, 'foldername_edit')
        self.line.setText(folder_name)
        self.line.textChanged.connect(self.validate)
        self.button_change = self.window.findChild(QPushButton, 'change_button')
        self.button_delete = self.window.findChild(QPushButton, 'delete_button')
        self.button_change.clicked.connect(self.change)
        self.button_delete.clicked.connect(self.delete)

        self.window.show()

    def validate(self):
        text = self.line.text().strip()
        if self.old_name == text or text in [f.name for f in connector.db_session.get_folders()]:
            self.button_change.setEnabled(False)
        else:
            self.button_change.setEnabled(True)

    def delete(self):
        connector.remove_folder(self.old_name)
        connector.upload_db()
        self.window.close()

    def change(self):
        connector.db_session.edit_folder(self.folder_name, self.line.text())
        connector.upload_db()
        self.window.close()


class EditFile(QMainWindow):
    def __init__(self, ui_file, file_name, file_tags, folder_name):
        super(EditFile, self).__init__(parent=None)
        self.file_name = file_name
        self.folder_name = folder_name
        ui_file = QFile(resource_path(ui_file))
        ui_file.open(QFile.ReadOnly)
        self.old_name = file_name
        self.old_tags = file_tags
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        self.line_name = self.window.findChild(QLineEdit, 'filename_edit')
        self.line_tags = self.window.findChild(QLineEdit, 'tags_edit')

        self.line_name.setText(file_name)
        self.line_tags.setText(', '.join(file_tags))
        self.line_name.textChanged.connect(self.validate_name)
        self.line_tags.textChanged.connect(self.validate_tags)
        self.button_change = self.window.findChild(QPushButton, 'change_button')
        self.button_delete = self.window.findChild(QPushButton, 'delete_button')
        self.button_change.clicked.connect(self.change)
        self.button_delete.clicked.connect(self.delete)

        self.window.show()

    def validate_name(self):
        text = self.line_name.text().strip()
        if (self.old_name == text or
                not text or
                text in [f.name for f in connector.db_session.get_folder(self.folder_name)]):
            self.button_change.setEnabled(False)
        else:
            self.button_change.setEnabled(True)

    def validate_tags(self):
        tags = [i.strip() for i in self.line_tags.text().split(',')]
        if tags == self.old_tags:
            self.button_change.setEnabled(False)
        else:
            self.button_change.setEnabled(True)

    def delete(self):
        connector.remove_file(self.old_name, self.folder_name)
        connector.upload_db()
        self.window.close()

    def change(self):
        tags = [i.strip() for i in self.line_tags.text().split(',')]
        connector.db_session.edit_file(self.old_name,
                                       self.folder_name,
                                       self.line_name.text(),
                                       tags)
        connector.upload_db()
        self.window.close()


class UploadForm(QMainWindow):
    def __init__(self, ui_file, file_path, filename):
        super(UploadForm, self).__init__(parent=None)
        self.file_path = file_path
        self.filename = filename
        ui_file = QFile(resource_path(ui_file))
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)

        ui_file.close()
        self.threadpool = QThreadPool()

        self.tags_line = self.window.findChild(QLineEdit, 'tagsEdit')
        self.upload_file = self.window.findChild(QCommandLinkButton, 'upload_file')
        self.upload_file.clicked.connect(self.handler)
        self.alert_label = self.window.findChild(QLabel, 'alertLabel')
        self.alert_label.setStyleSheet('QLabel {color: #FF0000;}')
        self.folders_list = self.window.findChild(QComboBox, 'folders_list')
        self.folders_list.addItems([str(i) for i in connector.db_session.get_folders()])
        self.filename_edit = self.window.findChild(QLineEdit, 'filename_edit')
        self.filename_edit.setText(filename)
        self.check_if_exists(filename)
        self.filename_edit.textChanged.connect(self.check_if_exists)
        self.progress_bar = self.window.findChild(QProgressBar, 'progressBar')
        self.worker = None
        self.ret = None
        self.client = None
        self.stop_needed = False
        self.window.show()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check)
        self.timer.setInterval(300)
        self.timer.start()

    def check_if_exists(self, cur):
        cur = cur.strip()
        if connector.db_session.check_file_exists(cur, self.folders_list.currentText()):
            self.alert_label.setText('Файл з такою назвою вже існує')
            self.upload_file.setEnabled(False)
        elif not cur:
            self.alert_label.setText('')
            self.upload_file.setEnabled(False)
        else:
            self.alert_label.setText('')
            self.upload_file.setEnabled(True)

    def check(self):
        thr = self.threadpool.activeThreadCount()
        if self.worker is not None and thr == 0:
            self.ret = self.worker.ret
            self.window.removeEventFilter(self)
            self.window.close()
            self.timer.stop()
        else:
            pass

    def handler(self):
        tags = []
        for i in self.tags_line.text().split(','):
            t = i.strip()
            if t:
                tags.append(t)
        print(42)
        try:
            self.upload_file.setEnabled(False)
            self.alert_label.setText('Зачекайте, йде підготовка файлу...')
            self.worker = Worker(connector.upload_file, self.file_path,
                                 self.filename_edit.text(),
                                 tags,
                                 self.folders_list.currentText(),
                                 self.upload_callback)

            self.threadpool.start(self.worker)
            self.window.installEventFilter(self)

        except FolderMissingError:
            pass
        except FileDuplicateError:
            self.alert_label.setText('Файл з такою назвою вже існує')

    def upload_callback(self, client, current, total):
        print(current, total, sep='/')
        if self.stop_needed:
            self.window.close()
            client.stop_transmission()

        if current == total:
            self.window.close()

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QEvent.Close:
            self.stop_needed = True
            event.ignore()
            return True
        return super(UploadForm, self).eventFilter(obj, event)


class FolderDialog(QMainWindow):
    def __init__(self, ui_file):
        super(FolderDialog, self).__init__(parent=None)
        ui_file = QFile(resource_path(ui_file))
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
        if not self.folder_name.text().strip():
            self.create_folder.setEnabled(False)
        else:
            self.create_folder.setEnabled(True)


class NewChannelForm(QMainWindow):
    def __init__(self, ui_file):
        super(NewChannelForm, self).__init__(parent=None)
        ui_file = QFile(resource_path(ui_file))
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
        ui_file = QFile(resource_path(ui_file))
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
        connector.check_channel(connector.db_session.get_channel())
        self.window.close()

    def create_handler(self):
        connector.create_and_set_channel()
        self.window.close()


class MainWindow(QMainWindow):
    def __init__(self, ui_file):
        super(MainWindow, self).__init__(parent=None)
        ui_file = QFile(resource_path(ui_file))
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        self.upload_button = self.window.findChild(QPushButton, 'upload_button')
        folder_create = self.window.findChild(QPushButton, 'folder_create')
        self.upload_button.clicked.connect(self.folders_exist)

        folder_create.clicked.connect(self.folder_handler)
        self.search_line = self.window.findChild(QLineEdit, 'search_line')
        self.search_line.textChanged.connect(self.search_handler)
        cancel_search_button = self.window.findChild(QToolButton, 'cancel_search_button')
        cancel_search_button.clicked.connect(self.cancel_search_handler)
        self.download_button = self.window.findChild(QPushButton, 'download_button')
        self.download_button.clicked.connect(self.download)
        self.change_button = self.window.findChild(QPushButton, 'change_button')
        self.change_button.clicked.connect(self.change_button_handler)
        self.folders_and_files_items = []
        self.selected_item = None
        self.latest_folders = connector.db_session.get_folders()
        self.latest_files = [i.ret() for i in self.latest_folders]
        self.refresh(first=True)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.setInterval(3000)
        self.refresh_timer.start()

        self.download_timer = QTimer(self)
        self.download_timer.timeout.connect(self.get_checked)
        self.download_timer.setInterval(100)
        self.download_timer.start()

        self.window.show()

    def folders_exist(self):
        if not connector.db_session.get_folders():
            self.folder_handler()
        else:
            self.upload_handler()

    def upload_handler(self):
        file_path = QFileDialog().getOpenFileName()
        filename = os.path.basename(file_path[0])
        if file_path[0] != '':
            self.__a = UploadForm('gui/file_upload.ui', file_path[0], filename)

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
            self.folders_and_files_items = []
            self.latest_folders = folders_list
            self.latest_files = latest_files
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Name', 'Tags', 'Size', 'Total files', 'Type'])

        self.tree_view = self.window.findChild(QTreeView, 'treeView')
        self.tree_view.clicked.connect(self.selection_changed)
        self.tree_view.setModel(self.model)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setColumnWidth(0, 300)
        self.tree_view.setColumnWidth(3, 60)
        for folder in folders_list:
            parent1 = QStandardItem(folder.name)
            self.folders_and_files_items.append(parent1)
            parent1.setEditable(False)
            parent1.setCheckable(True)
            parent1.setIcon(QIcon('gui/folder.ico'))
            parent2 = QStandardItem('')
            parent2.setEditable(False)
            parent3 = QStandardItem(str(round(folder.size / 1024, 3)) + ' KB')
            parent3.setEditable(False)
            parent4 = QStandardItem(str(folder.total))
            parent4.setEditable(False)
            parent5 = QStandardItem('Папка')
            parent5.setEditable(False)
            for file in folder:
                child1 = QStandardItem(file.name)
                child1.setEditable(False)
                child1.setCheckable(True)
                child1.setIcon(QIcon('gui/file.ico'))
                child2 = QStandardItem(', '.join(file.tags))
                child2.setEditable(False)
                child3 = QStandardItem(str(round(file.size / 1024, 3)) + ' KB')
                child3.setEditable(False)
                child4 = QStandardItem('')
                child4.setEditable(False)
                child5 = QStandardItem(os.path.splitext(file.name)[-1])
                child5.setEditable(False)

                parent1.appendRow([child1, child2, child3, child4, child5])
                self.folders_and_files_items.append(child1)
            self.model.appendRow([parent1, parent2, parent3, parent4])
            index = self.model.indexFromItem(parent1)
            self.tree_view.expand(index)

    def search_handler(self):
        if not self.search_line.text().strip():
            self.refresh(first=True)

            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self.refresh)
            self.refresh_timer.setInterval(3000)
            self.refresh_timer.start()

            return
        else:
            self.refresh_timer.stop()
            self.folders_and_files_items = []

        text = self.search_line.text()

        found_files = connector.db_session.search_file([i.strip() for i in text.split(',') if i.strip()])
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Name', 'Tags', 'Size', 'Total files', 'Type'])
        self.tree_view = self.window.findChild(QTreeView, 'treeView')

        self.tree_view.setModel(self.model)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setColumnWidth(0, 300)
        self.tree_view.setColumnWidth(3, 60)

        folders_list = set([i.folder for i in found_files])
        folders = []
        for folder_name in folders_list:
            files_list = []
            for file in found_files:
                if file.folder == folder_name:
                    files_list.append(file)
            folders.append(BaseFolder(folder_name, files_list))
        for folder in folders:
            parent1 = QStandardItem(folder.name)
            self.folders_and_files_items.append(parent1)
            parent1.setEditable(False)
            parent1.setCheckable(True)
            parent1.setIcon(QIcon('gui/folder.ico'))
            parent2 = QStandardItem('')
            parent3 = QStandardItem(str(round(folder.size / 1024, 3)) + ' KB')
            parent3.setEditable(False)
            parent4 = QStandardItem(str(folder.total))
            parent4.setEditable(False)
            parent5 = QStandardItem('Папка')
            parent5.setEditable(False)
            for file in folder:
                child1 = QStandardItem(file.name)
                child1.setEditable(False)
                child1.setCheckable(True)
                child1.setIcon(QIcon('gui/file.ico'))
                child2 = QStandardItem(', '.join(file.tags))
                child2.setEditable(False)
                child3 = QStandardItem(str(round(file.size / 1024, 3)) + ' KB')
                child3.setEditable(False)
                child4 = QStandardItem('')
                child4.setEditable(False)
                child5 = QStandardItem(os.path.splitext(file.name)[-1])
                child5.setEditable(False)
                parent1.appendRow([child1, child2, child3, child4, child5])
                self.folders_and_files_items.append(child1)

            self.model.appendRow([parent1, parent2, parent3, parent4])
            index = self.model.indexFromItem(parent1)
            self.tree_view.expand(index)

    def cancel_search_handler(self):
        self.search_line.setText('')
        self.refresh(first=True)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.setInterval(3000)
        self.refresh_timer.start()

    def get_checked(self):
        checked_items = []
        for item in self.folders_and_files_items:
            if item.checkState() == Qt.Checked:
                if item.parent() is not None:

                    checked_items.append([item.text(), item.parent().text(), item])
                else:
                    item.setCheckState(Qt.Unchecked)
                    items_count = item.rowCount()
                    c = 0
                    for i in range(items_count):
                        folder_item = item.child(i)
                        if folder_item.checkState() == Qt.Checked:
                            c += 1
                    if c == items_count:
                        for c in range(items_count):
                            folder_item = item.child(c)
                            folder_item.setCheckState(Qt.Unchecked)
                    else:
                        for i in range(items_count):
                            folder_item = item.child(i)
                            folder_item.setCheckState(Qt.Checked)
                            checked_items.append([folder_item.text(), folder_item.parent().text(), folder_item])

        self.download_button.setEnabled(True if len(checked_items) > 0 else False)
        return checked_items

    def download(self):
        for i in self.get_checked():
            file_name, file_folder, item = i
            item.setCheckState(Qt.Unchecked)
            connector.download_file(file_name, file_folder)

    def change_button_handler(self):
        if not self.selected_item.parent().data():
            self.__a = EditFolder('gui/folder_change.ui', self.selected_item.data())
        else:
            file = connector.db_session.get_file_by_folder(
                self.selected_item.data(),
                self.selected_item.parent().data()
            )
            self.__a = EditFile('gui/file_change.ui', file.name, file.tags, file.folder)

    def selection_changed(self, index):
        self.selected_item = index.sibling(index.row(), 0)
        self.change_button.setEnabled(True)


def client_exit():
    try:
        connector.client.stop()
    except (ConnectionError, AttributeError):
        pass
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
        pass
    finally:
        client_exit()
