import sys
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
    def __init__(self, ui_file):
        super(BaseForm, self).__init__(parent=None)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        self.line = self.window.findChild(QLineEdit, 'user_input')
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


def phone_number():
    app = get_app_instance()
    phoneval = PhoneForm('gui/login.ui')
    app.exec_()
    if not hasattr(phoneval, 'user_input'):
        sys.exit()
    return str(phoneval.user_input)


def telegram_code(phone_number=None):
    app = get_app_instance()
    codeval = CodeForm('gui/confirm.ui')
    app.exec_()
    if not hasattr(codeval, 'user_input'):
        sys.exit()
    return int(codeval.user_input)


def two_factor_auth(password_hint=None):
    app = get_app_instance()
    passval = PasswordForm('gui/2fa.ui')
    app.exec_()
    if not hasattr(passval, 'user_input'):
        sys.exit()
    return str(passval.user_input)
