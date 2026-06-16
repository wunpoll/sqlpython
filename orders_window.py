from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QMessageBox,
    QInputDialog, QComboBox, QLineEdit, QFormLayout,
    QDialogButtonBox, QLabel, QDateEdit
)
from PyQt6.QtCore import QDate
import database

class OrdersWindow(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Заказы")
        self.setGeometry(100, 100, 900, 500)
        
        layout = QVBoxLayout()
        
        # Таблица заказов
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Номер", "Дата заказа", "Дата доставки", "Адрес", "Клиент", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(4)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить")
        self.btn_add.clicked.connect(self.add_order)
        self.btn_edit = QPushButton("Редактировать")
        self.btn_edit.clicked.connect(self.edit_order)
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self.delete_order)
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.load_orders)
        
        # Для администратора и менеджера доступны все кнопки
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_refresh)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.load_orders()
    
    def load_orders(self):
        orders = database.get_orders()
        self.table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            self.table.setItem(row, 0, QTableWidgetItem(str(order['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(order['order_number']))
            self.table.setItem(row, 2, QTableWidgetItem(order['order_date']))
            self.table.setItem(row, 3, QTableWidgetItem(order['delivery_date']))
            self.table.setItem(row, 4, QTableWidgetItem(order['pickup_address']))
            self.table.setItem(row, 5, QTableWidgetItem(order['client_fio']))
            self.table.setItem(row, 6, QTableWidgetItem(order['status']))
    
    def add_order(self):
        # Простой диалог для добавления заказа
        dialog = OrderEditDialog(self, mode='add')
        if dialog.exec():
            data = dialog.get_data()
            try:
                database.add_order(data)
                QMessageBox.information(self, "Успех", "Заказ добавлен")
                self.load_orders()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить: {e}")
    
    def edit_order(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ для редактирования")
            return
        order_id = int(self.table.item(row, 0).text())
        order_data = database.get_order_by_id(order_id)
        if not order_data:
            QMessageBox.critical(self, "Ошибка", "Заказ не найден")
            return
        dialog = OrderEditDialog(self, mode='edit', data=order_data)
        if dialog.exec():
            data = dialog.get_data()
            try:
                database.update_order(order_id, data)
                QMessageBox.information(self, "Успех", "Заказ обновлён")
                self.load_orders()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось обновить: {e}")
    
    def delete_order(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ для удаления")
            return
        reply = QMessageBox.question(self, "Подтверждение", "Удалить заказ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            order_id = int(self.table.item(row, 0).text())
            try:
                database.delete_order(order_id)
                QMessageBox.information(self, "Успех", "Заказ удалён")
                self.load_orders()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить: {e}")


class OrderEditDialog(QDialog):
    def __init__(self, parent, mode='add', data=None):
        super().__init__(parent)
        self.mode = mode
        self.data = data
        self.setWindowTitle("Добавление заказа" if mode == 'add' else "Редактирование заказа")
        
        layout = QFormLayout()
        
        self.number_edit = QLineEdit()
        layout.addRow("Номер заказа:", self.number_edit)
        
        self.date_order = QDateEdit()
        self.date_order.setCalendarPopup(True)
        self.date_order.setDate(QDate.currentDate())
        layout.addRow("Дата заказа:", self.date_order)
        
        self.date_delivery = QDateEdit()
        self.date_delivery.setCalendarPopup(True)
        self.date_delivery.setDate(QDate.currentDate().addDays(7))
        layout.addRow("Дата доставки:", self.date_delivery)
        
        # Адрес пункта выдачи (можно просто текстом)
        self.address_edit = QLineEdit()
        layout.addRow("Адрес пункта выдачи:", self.address_edit)
        
        # Клиент (выпадающий список из БД)
        self.client_combo = QComboBox()
        self.client_combo.addItems(database.get_clients())
        self.client_combo.setEditable(True)
        layout.addRow("Клиент (ФИО):", self.client_combo)
        
        # Код получения
        self.code_edit = QLineEdit()
        layout.addRow("Код для получения:", self.code_edit)
        
        # Статус
        self.status_combo = QComboBox()
        self.status_combo.addItems(database.ORDER_STATUSES)
        layout.addRow("Статус:", self.status_combo)
        
        # Кнопки
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)
        
        self.setLayout(layout)
        
        if mode == 'edit' and data:
            self.load_data()
    
    def load_data(self):
        self.number_edit.setText(self.data.get('order_number', ''))
        # Преобразуем даты из строк
        try:
            self.date_order.setDate(QDate.fromString(self.data.get('order_date', ''), "yyyy-MM-dd"))
        except:
            pass
        try:
            self.date_delivery.setDate(QDate.fromString(self.data.get('delivery_date', ''), "yyyy-MM-dd"))
        except:
            pass
        self.address_edit.setText(self.data.get('pickup_address', ''))
        # Устанавливаем клиента
        client = self.data.get('client_fio', '')
        index = self.client_combo.findText(client)
        if index >= 0:
            self.client_combo.setCurrentIndex(index)
        else:
            self.client_combo.setEditText(client)
        self.code_edit.setText(self.data.get('pickup_code', ''))
        status = self.data.get('status', '')
        index = self.status_combo.findText(status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
    
    def get_data(self):
        return {
            'order_number': self.number_edit.text().strip(),
            'order_date': self.date_order.date().toString("yyyy-MM-dd"),
            'delivery_date': self.date_delivery.date().toString("yyyy-MM-dd"),
            'pickup_address': self.address_edit.text().strip(),
            'client_fio': self.client_combo.currentText().strip(),
            'pickup_code': self.code_edit.text().strip(),
            'status': self.status_combo.currentText()
        }