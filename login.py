import sys
import os
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import gui.logo
from threading import RLock

_lock = RLock()

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


class FileDialog(QMainWindow):
    def __init__(self, ui_file):
        super(FileDialog, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        self.window.show()


class FolderDialog(QMainWindow):
    def __init__(self, ui_file):
        super(FolderDialog, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        self.window.show()


class BaseForm(QMainWindow):
    def __init__(self, ui_file):
        super(BaseForm, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        self.line = self.window.findChild(QLineEdit, 'user_input')
        self.line.returnPressed.connect(self.handler)
        enter_button = self.window.findChild(QPushButton, 'enter_button')
        enter_button.clicked.connect(self.handler)
        self.window.show()

    def handler(self):
        self.user_input = self.line.text()
        if not self.user_input:
            return

        self.window.close()


class PhoneForm(BaseForm):

    def __init__(self, ui_file):
        super(PhoneForm, self).__init__(ui_file)
        self.onlyPhone = QRegExpValidator(r'\+?\d{7,15}')
        self.line.setValidator(self.onlyPhone)

    def handler(self):
        self.user_input = self.line.text()
        if not self.user_input:
            return
        else:
            self.user_input = '+{}'.format(self.user_input.lstrip('+'))
        self.window.close()


class CodeForm(BaseForm):

    def __init__(self, ui_file):
        super(CodeForm, self).__init__(ui_file)
        self.onlyCode = QRegExpValidator(r'\d{5}')
        self.line.setValidator(self.onlyCode)

    def handler(self):
        self.user_input = self.line.text()
        if not self.user_input or len(self.user_input) != 5:
            return
        self.window.close()


class PasswordForm(BaseForm):

    def __init__(self, ui_file):
        super(PasswordForm, self).__init__(ui_file)


class NewChannelForm(QMainWindow):
    def __init__(self, ui_file):
        super(NewChannelForm, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        create_channel_button = self.window.findChild(QCommandLinkButton, 'create_channel')
        create_channel_button.clicked.connect(self.handler)
        self.window.show()

    def handler(self):
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
        self.model.setHorizontalHeaderLabels(['Name', 'Date', 'Type', 'Total elements'])
        self.tree_view = self.window.findChild(QTreeView, 'treeView')
        self.tree_view.setModel(self.model)
        self.tree_view.setUniformRowHeights(True)

        upload_button = self.window.findChild(QPushButton, 'upload_button')
        upload_button.clicked.connect(self.upload_handler)
        folder_create = self.window.findChild(QPushButton, 'folder_create')
        folder_create.clicked.connect(self.folder_handler)

        # for i in range(3):
        #     parent1 = QStandardItem('Family {}. Some long status text for sp'.format(i))
        #     for j in range(3):
        #         child1 = QStandardItem('Child {}'.format(i * 3 + j))
        #         child2 = QStandardItem('row: {}, col: {}'.format(i, j + 1))
        #         child3 = QStandardItem('ze komanda'.format(i, j + 2))
        #         parent1.appendRow([child1, child2, child3])
        #     self.model.appendRow(parent1)
        #     self.tree_view.setFirstColumnSpanned(i, self.tree_view.rootIndex(), True)
        # index = self.model.indexFromItem(parent1)
        # self.tree_view.expand(index)
        # selmod = self.tree_view.selectionModel()
        # index2 = self.model.indexFromItem(child3)
        # selmod.select(index2, QItemSelectionModel.Select | QItemSelectionModel.Rows)

        self.window.show()

    def upload_handler(self):
        #self.filedialog = FileDialog('gui/file_dialog.ui')
        pass

    def folder_handler(self):
        self.folderdialog = FolderDialog('gui/folder_dialog.ui')

def phone_number():
    app = get_app_instance()
    phoneval = PhoneForm('gui/login.ui')
    app.exec_()
    if not hasattr(phoneval, 'user_input'):
        sys.exit()
    return phoneval.user_input


def telegram_code(phone_number):
    app = get_app_instance()
    codeval = CodeForm('gui/confirm.ui')
    app.exec_()
    if not hasattr(codeval, 'user_input'):
        sys.exit()
    return codeval.user_input


def two_factor_auth(password_hint):
    app = get_app_instance()
    passval = PasswordForm('gui/2fa.ui')
    app.exec_()
    if not hasattr(passval, 'user_input'):
        sys.exit()
    return passval.user_input


def new_channel():
    app = get_app_instance()
    newchannelform = NewChannelForm('gui/create_channel.ui')
    app.exec_()


def existing_channel():
    app = get_app_instance()
    existingchannelform = NewOrExistingChannelForm('gui/existing_channel.ui')
    app.exec_()

def main_window():
    app = get_app_instance()
    mainwindow = MainWindow('gui/main.ui')
    app.exec_()
