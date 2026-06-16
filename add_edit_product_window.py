import os
import shutil
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import database

class AddEditProductWindow(QDialog):
    def __init__(self, parent, mode='add', product_id=None):
        super().__init__(parent)
        self.parent = parent
        self.mode = mode  # 'add' или 'edit'
        self.product_id = product_id
        self.photo_path = None  # путь к текущему выбранному фото
        self.old_photo = None   # для удаления при замене (в режиме edit)
        
        self.setWindowTitle("Добавление товара" if mode == 'add' else "Редактирование товара")
        self.setGeometry(200, 200, 600, 500)
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # Поля
        self.article_edit = QLineEdit()
        form_layout.addRow("Артикул:", self.article_edit)
        
        self.name_edit = QLineEdit()
        form_layout.addRow("Наименование:", self.name_edit)
        
        self.price_edit = QDoubleSpinBox()
        self.price_edit.setRange(0, 1000000)
        self.price_edit.setPrefix("₽ ")
        form_layout.addRow("Цена:", self.price_edit)
        
        self.supplier_combo = QComboBox()
        self.supplier_combo.setEditable(True)
        # Загружаем существующих поставщиков
        self.supplier_combo.addItems(database.get_suppliers())
        form_layout.addRow("Поставщик:", self.supplier_combo)
        
        self.manufacturer_combo = QComboBox()
        self.manufacturer_combo.setEditable(True)
        self.manufacturer_combo.addItems(database.get_manufacturers())
        form_layout.addRow("Производитель:", self.manufacturer_combo)
        
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(database.get_categories())
        form_layout.addRow("Категория:", self.category_combo)
        
        self.discount_edit = QDoubleSpinBox()
        self.discount_edit.setRange(0, 100)
        self.discount_edit.setSuffix(" %")
        form_layout.addRow("Скидка (%):", self.discount_edit)
        
        self.quantity_edit = QSpinBox()
        self.quantity_edit.setRange(0, 9999)
        form_layout.addRow("Количество на складе:", self.quantity_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Описание:", self.description_edit)
        
        # Фото
        photo_layout = QHBoxLayout()
        self.photo_label = QLabel("Фото не выбрано")
        self.photo_label.setFixedSize(150, 150)
        self.photo_label.setStyleSheet("border: 1px solid gray;")
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_photo = QPushButton("Выбрать фото")
        self.btn_photo.clicked.connect(self.select_photo)
        photo_layout.addWidget(self.photo_label)
        photo_layout.addWidget(self.btn_photo)
        form_layout.addRow("Фото:", photo_layout)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self.save_product)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Если редактирование, загружаем данные
        if mode == 'edit' and product_id:
            self.load_product_data()
    
    def load_product_data(self):
        product = database.get_product_by_id(self.product_id)
        if not product:
            QMessageBox.critical(self, "Ошибка", "Товар не найден")
            self.reject()
            return
        self.article_edit.setText(product['article'])
        self.name_edit.setText(product['name'])
        self.price_edit.setValue(product['price'])
        # Устанавливаем значения в комбобоксах (если есть, иначе добавляем)
        self.set_combo_value(self.supplier_combo, product['supplier'])
        self.set_combo_value(self.manufacturer_combo, product['manufacturer'])
        self.set_combo_value(self.category_combo, product['category'])
        self.discount_edit.setValue(product['discount'])
        self.quantity_edit.setValue(product['quantity'])
        self.description_edit.setText(product['description'] or "")
        # Фото
        if product['photo'] and os.path.exists(product['photo']):
            self.old_photo = product['photo']
            self.photo_path = product['photo']
            pixmap = QPixmap(product['photo'])
            if not pixmap.isNull():
                self.photo_label.setPixmap(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))
                self.photo_label.setText("")
            else:
                self.photo_label.setText("Фото повреждено")
        else:
            self.photo_label.setText("Фото не выбрано")
    
    def set_combo_value(self, combo, value):
        if not value:
            return
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.addItem(value)
            combo.setCurrentText(value)
    
    def select_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not file_path:
            return
        # Сохраняем фото в папку images (создаём, если нет)
        images_dir = "images"
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        # Генерируем имя файла (артикул или временное)
        article = self.article_edit.text().strip()
        if not article:
            # Если артикул ещё не введён, используем временное имя
            import time
            article = f"temp_{int(time.time())}"
        ext = os.path.splitext(file_path)[1]
        new_filename = f"{article}{ext}"
        dest_path = os.path.join(images_dir, new_filename)
        
        # Если файл с таким именем уже существует, добавляем суффикс
        counter = 1
        base, ext2 = os.path.splitext(new_filename)
        while os.path.exists(dest_path):
            new_filename = f"{base}_{counter}{ext2}"
            dest_path = os.path.join(images_dir, new_filename)
            counter += 1
        
        # Копируем файл
        try:
            shutil.copy2(file_path, dest_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить фото: {e}")
            return
        
        # Удаляем старое фото, если оно было и отличается от нового
        if self.old_photo and os.path.exists(self.old_photo) and self.old_photo != dest_path:
            try:
                os.remove(self.old_photo)
            except:
                pass
        
        self.photo_path = dest_path
        # Отображаем
        pixmap = QPixmap(dest_path)
        if not pixmap.isNull():
            self.photo_label.setPixmap(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))
            self.photo_label.setText("")
        else:
            self.photo_label.setText("Фото повреждено")
    
    def save_product(self):
        # Проверка обязательных полей
        article = self.article_edit.text().strip()
        name = self.name_edit.text().strip()
        if not article or not name:
            QMessageBox.warning(self, "Ошибка", "Артикул и наименование обязательны")
            return
        
        # Собираем данные
        data = {
            'article': article,
            'name': name,
            'unit': 'шт.',  # фиксировано
            'price': self.price_edit.value(),
            'supplier': self.supplier_combo.currentText().strip(),
            'manufacturer': self.manufacturer_combo.currentText().strip(),
            'category': self.category_combo.currentText().strip(),
            'discount': self.discount_edit.value(),
            'quantity': self.quantity_edit.value(),
            'description': self.description_edit.toPlainText().strip(),
            'photo': self.photo_path or ''
        }
        
        try:
            if self.mode == 'add':
                new_id = database.add_product(data)
                QMessageBox.information(self, "Успех", f"Товар добавлен с ID {new_id}")
            else:
                database.update_product(self.product_id, data)
                QMessageBox.information(self, "Успех", "Товар обновлён")
            self.accept()
            self.parent.load_products()  # обновляем таблицу в главном окне
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить товар: {e}")