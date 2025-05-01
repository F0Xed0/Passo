import os
import time
import pyperclip
from typing import Optional, Tuple, Dict
from PIL import ImageGrab
import pytesseract
from pynput import keyboard, mouse
from Xlib import X, display, XK
from Xlib.protocol import event

class WindowManager:
    def __init__(self, clipboard_timeout: int = 30):
        """
        Инициализация менеджера окон.
        
        :param clipboard_timeout: Время в секундах, после которого пароль удаляется из буфера обмена
        """
        self.display = display.Display()
        self.root = self.display.screen().root
        self.clipboard_timeout = clipboard_timeout
        self.last_clipboard_time = 0
        self.last_clipboard_content = None
        self._setup_listeners()

    def _setup_listeners(self):
        """
        Настройка слушателей клавиатуры и мыши.
        """
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click
        )
        
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def _on_key_press(self, key):
        """
        Обработчик нажатий клавиш.
        """
        try:
            # Проверяем комбинации клавиш
            if hasattr(key, 'vk') and key.vk == 65535:  # Escape
                self.clear_clipboard()
        except AttributeError:
            pass

    def _on_key_release(self, key):
        """
        Обработчик отпускания клавиш.
        """
        pass

    def _on_mouse_click(self, x, y, button, pressed):
        """
        Обработчик кликов мыши.
        """
        if pressed:
            self._check_clipboard_timeout()

    def get_active_window_info(self) -> Dict[str, str]:
        """
        Получение информации об активном окне.
        """
        try:
            window = self.display.get_input_focus().focus
            if isinstance(window, int):
                window = self.display.create_resource_object('window', window)
            window_class = window.get_wm_class()
            window_name = window.get_wm_name()
            
            return {
                'class': window_class[1] if window_class else 'Unknown',
                'name': window_name if window_name else 'Unknown'
            }
        except Exception:
            return {
                'class': 'Unknown',
                'name': 'Unknown'
            }

    def capture_screen_region(self, x: int, y: int, width: int, height: int) -> str:
        """
        Захват области экрана и распознавание текста.
        """
        screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        return pytesseract.image_to_string(screenshot)

    def type_text(self, text: str):
        """
        Эмуляция ввода текста с клавиатуры.
        """
        for char in text:
            # Получаем keycode для символа
            keysym = XK.string_to_keysym(char)
            keycode = self.display.keysym_to_keycode(keysym)
            
            # Отправляем события нажатия и отпускания клавиши
            key_press = event.KeyPress(
                time=int(time.time()),
                root=self.root,
                window=self.root,
                same_screen=0,
                child=X.NONE,
                root_x=0,
                root_y=0,
                event_x=0,
                event_y=0,
                state=0,
                detail=keycode
            )
            
            key_release = event.KeyRelease(
                time=int(time.time()),
                root=self.root,
                window=self.root,
                same_screen=0,
                child=X.NONE,
                root_x=0,
                root_y=0,
                event_x=0,
                event_y=0,
                state=0,
                detail=keycode
            )
            
            self.root.send_event(key_press)
            self.root.send_event(key_release)
            self.display.sync()
            time.sleep(0.01)  # Небольшая задержка между символами

    def copy_to_clipboard(self, text: str, timeout: Optional[int] = None):
        """
        Копирование текста в буфер обмена с таймером на удаление.
        Если text пустой, буфер обмена очищается.
        """
        # Сохраняем текущее содержимое буфера обмена
        current_content = pyperclip.paste()
        
        # Копируем новый текст или очищаем буфер
        if text == '':
            self.clear_clipboard()
        else:
            pyperclip.copy(text)
            self.last_clipboard_content = current_content
        
        # Обновляем время и таймаут
        self.last_clipboard_time = time.time()
        if timeout is not None:
            self.clipboard_timeout = timeout

    def clear_clipboard(self):
        """
        Очистка буфера обмена и восстановление предыдущего содержимого.
        """
        # Сначала очищаем буфер
        pyperclip.copy('')
        
        # Если есть предыдущее содержимое и оно не пустое, восстанавливаем его
        if self.last_clipboard_content:
            pyperclip.copy(self.last_clipboard_content)
        
        self.last_clipboard_time = 0
        self.last_clipboard_content = None

    def _check_clipboard_timeout(self):
        """
        Проверка таймаута буфера обмена.
        """
        if (self.last_clipboard_time > 0 and
            time.time() - self.last_clipboard_time > self.clipboard_timeout):
            self.clear_clipboard()

    def simulate_hotkey(self, *keys):
        """
        Эмуляция нажатия горячих клавиш.
        """
        for key in keys:
            keycode = self.display.keysym_to_keycode(
                XK.string_to_keysym(key)
            )
            
            self.root.send_event(
                event.KeyPress(
                    time=int(time.time()),
                    root=self.root,
                    window=self.root,
                    same_screen=0,
                    child=X.NONE,
                    root_x=0,
                    root_y=0,
                    event_x=0,
                    event_y=0,
                    state=0,
                    detail=keycode
                )
            )
        
        # Отпускаем клавиши в обратном порядке
        for key in reversed(keys):
            keycode = self.display.keysym_to_keycode(
                XK.string_to_keysym(key)
            )
            
            self.root.send_event(
                event.KeyRelease(
                    time=int(time.time()),
                    root=self.root,
                    window=self.root,
                    same_screen=0,
                    child=X.NONE,
                    root_x=0,
                    root_y=0,
                    event_x=0,
                    event_y=0,
                    state=0,
                    detail=keycode
                )
            )
        
        self.display.sync()

    def __del__(self):
        """
        Очистка при уничтожении объекта.
        """
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.clear_clipboard()
        self.display.close() 