import sys
import sqlite3
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QListWidget, QMenu
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from cfg import BASE_URL, API_KEY, dark_theme, light_theme


class WeatherWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_theme = 'light'
        self.conn = sqlite3.connect('settings.db')
        self.setup_database()
        self.favorites = []  # Список избранных городов
        self.init_ui()

    def setup_database(self):
        """Create required tables if they do not exist."""
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
                            key TEXT PRIMARY KEY,
                            value TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS favorites (
                            city TEXT PRIMARY KEY)''')
        self.conn.commit()

    def init_ui(self):
        layout = QVBoxLayout()

        # Input for city name
        self.city_input = QLineEdit(self)
        self.city_input.setPlaceholderText("Введите название города")
        layout.addWidget(self.city_input)

        # Button to update weather
        self.update_button = QPushButton("Обновить", self)
        self.update_button.clicked.connect(self.get_weather)
        layout.addWidget(self.update_button)

        self.weather_icon = QLabel(self)
        layout.addWidget(self.weather_icon)

        # Weather info display
        self.weather_label = QLabel("Здесь будет показана погода", self)
        layout.addWidget(self.weather_label)

        # Favorites list
        self.favorites_list = QListWidget(self)
        layout.addWidget(self.favorites_list)

        # Add to favorites button
        self.add_favorite_button = QPushButton("Добавить в избранные", self)
        self.add_favorite_button.clicked.connect(self.add_to_favorites)
        layout.addWidget(self.add_favorite_button)

        self.favorites_list.itemDoubleClicked.connect(self.show_favorite_weather)
        self.favorites_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.favorites_list.customContextMenuRequested.connect(self.context_menu_event)
        layout.addWidget(self.favorites_list)

        # Theme toggle button
        self.theme_button = QPushButton("Сменить тему", self)
        self.theme_button.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_button)

        self.setLayout(layout)

        # Load settings after the UI is fully initialized
        self.load_settings()

    def add_to_favorites(self):
        city = self.city_input.text()

        if city and city not in self.favorites:
            # Add to favorites list in database
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO favorites (city) VALUES (?)", (city,))
            self.conn.commit()

            # Add to the in-memory favorites list and update UI
            self.favorites.append(city)
            self.favorites_list.addItem(city)
            self.city_input.clear()
        elif city in self.favorites:
            self.weather_label.setText("Город уже в избранных.")
        else:
            self.weather_label.setText("Не введён город.")

    def get_weather(self):
        city = self.city_input.text()
        if not city:
            self.weather_label.setText('Введите название города.')
            return

        params = {
            'q': city,
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'ru'
        }

        try:
            response = requests.get(BASE_URL, params=params)
            data = response.json()

            if data.get('cod') != 200:
                self.weather_label.setText('Город не найден. Попробуйте ещё раз.')
                return

            temperature = data['main']['temp']
            description = data['weather'][0]['description'].capitalize()
            icon_code = data['weather'][0]['icon']

            self.weather_label.setText(f'{city}: {temperature}°C, {description}')

            icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
            icon_data = requests.get(icon_url).content
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.weather_icon.setPixmap(pixmap)

        except Exception as e:
            self.weather_label.setText('Ошибка при получении данных о погоде.')
            self.weather_icon.clear()
            print(f'Ошибка: {e}')

    def show_favorite_weather(self, item):
        city = item.text()
        self.city_input.setText(city)
        self.get_weather()

    def closeEvent(self, event):
        self.save_settings()
        event.accept()

    def context_menu_event(self, pos):
        context_menu = QMenu(self)
        delete_action = context_menu.addAction("Удалить из избранных")
        action = context_menu.exec(self.favorites_list.mapToGlobal(pos))

        if action == delete_action:
            item = self.favorites_list.currentItem()
            if item:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM favorites WHERE city = ?", (item.text(),))
                self.conn.commit()

                # Remove from the in-memory favorites list and UI
                self.favorites.remove(item.text())
                self.favorites_list.takeItem(self.favorites_list.row(item))

    def toggle_theme(self):
        if self.current_theme == 'light':
            self.setStyleSheet(dark_theme)
            self.current_theme = 'dark'
            self.theme_button.setText("Сменить на светлую тему")
        else:
            self.setStyleSheet(light_theme)
            self.current_theme = 'light'
            self.theme_button.setText("Сменить на темную тему")

        self.save_settings()

    def load_settings(self):
        cursor = self.conn.cursor()

        # Load theme
        cursor.execute("SELECT value FROM settings WHERE key = 'theme'")
        theme = cursor.fetchone()
        if theme:
            self.current_theme = theme[0]
            self.setStyleSheet(light_theme if self.current_theme == "light" else dark_theme)

        # Load favorite cities
        cursor.execute("SELECT city FROM favorites")
        favorites = [row[0] for row in cursor.fetchall()]
        print("Загруженные избранные города:", favorites)

        # Populate the in-memory favorites list and UI
        self.favorites = favorites
        self.favorites_list.clear()
        self.favorites_list.addItems(favorites)

    def save_settings(self):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("theme", self.current_theme))
        self.conn.commit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = WeatherWidget()
    widget.setWindowTitle('Погода')
    widget.resize(400, 150)
    widget.show()
    sys.exit(app.exec())
