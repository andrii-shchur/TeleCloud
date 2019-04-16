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


class BaseForm(QMainWindow):
    def __init__(self, ui_file, alert_messasge=''):
        super(BaseForm, self).__init__(parent=None)
        self.alert_message = alert_messasge
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        self.line = self.window.findChild(QLineEdit, 'user_input')
        self.line.returnPressed.connect(self.handler)
        enter_button = self.window.findChild(QPushButton, 'enter_button')
        enter_button.clicked.connect(self.handler)
        self.alert_label = self.window.findChild(QLabel, 'alertLabel')
        self.alert_label.setStyleSheet('QLabel {color: #FF0000;}')

        self.window.show()

    def handler(self):
        self.user_input = self.line.text()
        if not self.user_input:
            return
        # self.window.close()


class PhoneForm(BaseForm):

    def __init__(self, ui_file, alert_message=''):
        super(PhoneForm, self).__init__(ui_file, alert_message)
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

    def __init__(self, ui_file, alert_message=''):
        super(CodeForm, self).__init__(ui_file, alert_message)
        self.onlyCode = QRegExpValidator(r'\d{5}')
        self.line.setValidator(self.onlyCode)

    def handler(self):
        self.user_input = self.line.text()
        if not self.user_input or len(self.user_input) != 5:
            return
        self.window.close()


class PasswordForm(BaseForm):

    def __init__(self, ui_file, alert_message=''):
        super(PasswordForm, self).__init__(ui_file, alert_message)

    def existing_handler(self):
        self.window.close()

    def create_handler(self):
        self.window.close()


def phone_number(alert_message=''):
    app = get_app_instance()
    phoneval = PhoneForm('gui/login.ui', alert_message)
    app.exec_()
    if not hasattr(phoneval, 'user_input'):
        sys.exit()
    return phoneval.user_input


def telegram_code(phone_number, alert_message=''):
    app = get_app_instance()
    codeval = CodeForm('gui/confirm.ui', alert_message)
    app.exec_()
    if not hasattr(codeval, 'user_input'):
        sys.exit()
    return codeval.user_input


def two_factor_auth(password_hint, alert_message=''):
    app = get_app_instance()
    passval = PasswordForm('gui/2fa.ui', alert_message)
    app.exec_()
    if not hasattr(passval, 'user_input'):
        sys.exit()
    return passval.user_input
