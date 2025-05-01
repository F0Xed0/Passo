import pytest
import time
import pyperclip
from src.window_manager import WindowManager

@pytest.fixture
def window_manager():
    manager = WindowManager(clipboard_timeout=2)  # Короткий таймаут для тестов
    yield manager
    manager.clear_clipboard()

def test_clipboard_operations(window_manager):
    # Тест операций с буфером обмена
    original_content = pyperclip.paste()
    test_text = "test_password_123"
    
    # Копируем текст
    window_manager.copy_to_clipboard(test_text)
    assert pyperclip.paste() == test_text
    
    # Ждем таймаута
    time.sleep(3)
    
    # Проверяем очистку
    window_manager._check_clipboard_timeout()
    assert pyperclip.paste() == original_content

def test_manual_clipboard_clear(window_manager):
    # Тест ручной очистки буфера обмена
    test_text = "secret_password"
    original_content = "original_content"
    
    pyperclip.copy(original_content)
    window_manager.copy_to_clipboard(test_text)
    assert pyperclip.paste() == test_text
    
    window_manager.clear_clipboard()
    assert pyperclip.paste() == original_content

def test_window_info(window_manager):
    # Тест получения информации об окне
    info = window_manager.get_active_window_info()
    assert isinstance(info, dict)
    assert 'class' in info
    assert 'name' in info

def test_screen_capture(window_manager):
    # Тест захвата экрана
    # Захватываем маленькую область
    text = window_manager.capture_screen_region(0, 0, 100, 100)
    assert isinstance(text, str)

def test_keyboard_simulation(window_manager):
    # Тест эмуляции клавиатуры
    test_text = "test"
    window_manager.type_text(test_text)
    # Проверка успешности можно сделать только в интерактивном режиме

def test_hotkey_simulation(window_manager):
    # Тест эмуляции горячих клавиш
    window_manager.simulate_hotkey("Control_L", "c")
    # Проверка успешности можно сделать только в интерактивном режиме

def test_clipboard_timeout_update(window_manager):
    # Тест обновления таймаута буфера обмена
    original_timeout = window_manager.clipboard_timeout
    new_timeout = 5
    
    window_manager.clipboard_timeout = new_timeout
    assert window_manager.clipboard_timeout == new_timeout
    
    # Возвращаем исходное значение
    window_manager.clipboard_timeout = original_timeout

def test_multiple_clipboard_operations(window_manager):
    # Тест множественных операций с буфером обмена
    texts = ["password1", "password2", "password3"]
    
    for text in texts:
        window_manager.copy_to_clipboard(text)
        assert pyperclip.paste() == text
        window_manager.clear_clipboard()

def test_edge_cases(window_manager):
    # Тест с пустой строкой
    window_manager.copy_to_clipboard("")
    assert pyperclip.paste() == ""
    
    # Тест с очень длинной строкой
    long_text = "a" * 10000
    window_manager.copy_to_clipboard(long_text)
    assert pyperclip.paste() == long_text
    
    # Тест с юникодом
    unicode_text = "привет 你好 مرحبا"
    window_manager.copy_to_clipboard(unicode_text)
    assert pyperclip.paste() == unicode_text

def test_cleanup(window_manager):
    # Тест очистки при уничтожении объекта
    test_text = "cleanup_test"
    original_content = "original"
    
    pyperclip.copy(original_content)
    window_manager.copy_to_clipboard(test_text)
    
    # Эмулируем уничтожение объекта
    window_manager.__del__()
    
    # Проверяем, что буфер обмена очищен
    assert pyperclip.paste() == original_content 