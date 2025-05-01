#!/bin/bash

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 не установлен. Устанавливаем..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
fi

# Проверяем наличие tesseract-ocr
if ! command -v tesseract &> /dev/null; then
    echo "Tesseract OCR не установлен. Устанавливаем..."
    sudo apt-get install -y tesseract-ocr tesseract-ocr-rus
fi

# Создаем виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Создаем директорию для данных
mkdir -p data

# Создаем ярлык для запуска
cat > passo.desktop << EOL
[Desktop Entry]
Name=Passo
Comment=Менеджер паролей с ассоциативной генерацией
Exec=$(pwd)/venv/bin/python3 $(pwd)/src/main.py
Icon=password-manager
Terminal=false
Type=Application
Categories=Utility;Security;
EOL

# Копируем ярлык в системное меню
mkdir -p ~/.local/share/applications
cp passo.desktop ~/.local/share/applications/

# Делаем скрипт запуска исполняемым
chmod +x src/main.py

echo "Установка завершена!"
echo "Вы можете запустить Passo через меню приложений или командой:"
echo "$(pwd)/venv/bin/python3 $(pwd)/src/main.py" 