import sys
import os
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from telemethods import TeleCloudApp
import gui.logo


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


class FolderDialog(QMainWindow):
    def __init__(self, ui_file):
        super(FolderDialog, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        self.window.show()


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
        self.window.hide()
        connector.create_and_set_channel()
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
            #self.tree_view.setFirstColumnSpanned(folder, self.tree_view.rootIndex(), True)
        index = self.model.indexFromItem(parent1)
        self.tree_view.expand(index)
        # selmod = self.tree_view.selectionModel()
        # index2 = self.model.indexFromItem(child3)
        # selmod.select(index2, QItemSelectionModel.Select | QItemSelectionModel.Rows)

        self.window.show()

    def folder_handler(self):
        self.folderdialog = FolderDialog('gui/folder_dialog.ui')


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
        pass
    finally:
        if connector:
            connector.client.stop()
