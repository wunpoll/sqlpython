import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
import database
from main_window import MainWindow

class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setGeometry(300, 300, 300, 200)
        layout = QVBoxLayout()

        self.label_login = QLabel("Логин:")
        layout.addWidget(self.label_login)
        self.edit_login = QLineEdit()
        layout.addWidget(self.edit_login)

        self.label_password = QLabel("Пароль:")
        layout.addWidget(self.label_password)
        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.edit_password)

        self.btn_login = QPushButton("Войти")
        self.btn_login.clicked.connect(self.handle_login)
        layout.addWidget(self.btn_login)

        self.btn_guest = QPushButton("Войти как гость")
        self.btn_guest.clicked.connect(self.guest_login)
        layout.addWidget(self.btn_guest)

        self.setLayout(layout)

    def handle_login(self):
        login = self.edit_login.text().strip()
        password = self.edit_password.text().strip()
        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return
        user = database.get_user(login, password)
        if user:
            self.open_main_window(user)
        else:
            QMessageBox.critical(self, "Ошибка", "Неверный логин или пароль")

    def guest_login(self):
        guest_user = {"role": "guest", "fio": "Гость"}
        self.open_main_window(guest_user)

    def open_main_window(self, user):
        self.main_window = MainWindow(user)   # <-- исправлено!
        self.main_window.show()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AuthWindow()
    window.show()
    sys.exit(app.exec())