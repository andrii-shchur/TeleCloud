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
        self.line.textChanged.connect(self.grey_in)
        self.line.returnPressed.connect(self.handler)
        self.enter_button = self.window.findChild(QPushButton, 'enter_button')
        self.enter_button.clicked.connect(self.handler)
        self.alert_label = self.window.findChild(QLabel, 'alertLabel')

        self.alert_label.setStyleSheet('QLabel {color: #FF0000;}')
        self.alert_label.setText(alert_messasge)

        self.window.show()

    def handler(self):
        self.user_input = self.line.text()
        if not self.user_input:
            return
        # self.window.close()

    def grey_in(self, cur):
        pass


class PhoneForm(BaseForm):

    def __init__(self, ui_file, alert_message='', predefined_number=''):
        super(PhoneForm, self).__init__(ui_file, alert_message)
        if predefined_number:
            self.line.setText(predefined_number)
        self.validate_check = QRegExpValidator(r'\+?\d{7,15}')
        self.line.setValidator(self.validate_check)

    def handler(self):
        if not self.validate_check.validate(self.line.text(), 0)[0] == self.validate_check.Acceptable:
            return
        else:
            self.user_input = self.line.text()
            self.user_input = '+{}'.format(self.user_input.lstrip('+'))
        self.window.close()

    def grey_in(self, cur):

        val = self.validate_check.validate(cur, 0)
        if val[0] == self.validate_check.Acceptable:
            self.enter_button.setEnabled(True)
        else:
            self.enter_button.setEnabled(False)


class CodeForm(BaseForm):

    def __init__(self, ui_file, alert_message=''):
        super(CodeForm, self).__init__(ui_file, alert_message)
        self.validate_check = QRegExpValidator(r'\d{5}')
        self.line.setValidator(self.validate_check)

    def handler(self):
        if not self.validate_check.validate(self.line.text(), 0)[0] == self.validate_check.Acceptable:
            return
        self.user_input = self.line.text()
        self.window.close()

    def grey_in(self, cur):
        val = self.validate_check.validate(cur, 0)
        if val[0] == self.validate_check.Acceptable:
            self.enter_button.setEnabled(True)
        else:
            self.enter_button.setEnabled(False)


class PasswordForm(BaseForm):

    def __init__(self, ui_file, alert_message=''):
        super(PasswordForm, self).__init__(ui_file, alert_message)

    def handler(self):
        if len(self.line.text()) < 1:
            return
        self.user_input = self.line.text()
        self.window.close()

    def grey_in(self, cur):
        if len(cur) > 0:
            self.enter_button.setEnabled(True)
        else:
            self.enter_button.setEnabled(False)


class PleaseWait():
    def __init__(self, ui_file):
        super(PleaseWait, self).__init__()
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()


def phone_number(alert_message='', predefined_number=''):
    app = get_app_instance()
    phoneval = PhoneForm('gui/login.ui', alert_message, predefined_number)
    app.exec_()
    if not hasattr(phoneval, 'user_input'):
        return False
    return phoneval.user_input


def telegram_code(phone_number, alert_message=''):
    app = get_app_instance()
    codeval = CodeForm('gui/confirm.ui', alert_message)
    app.exec_()
    if not hasattr(codeval, 'user_input'):
        return False
    return codeval.user_input


def two_factor_auth(password_hint, alert_message=''):
    app = get_app_instance()
    passval = PasswordForm('gui/2fa.ui', alert_message)
    app.exec_()
    if not hasattr(passval, 'user_input'):
        return False
    return passval.user_input
