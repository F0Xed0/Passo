from setuptools import setup, find_packages

setup(
    name="passo",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "cryptography>=41.0.7",
        "PyQt6>=6.6.1",
        "python-dotenv>=1.0.0",
        "pynput>=1.7.6",
        "pyperclip>=1.8.2",
        "pillow>=10.2.0",
        "pytesseract>=0.3.10",
        "python-xlib>=0.33",
        "pyotp>=2.9.0",
        "sqlalchemy>=2.0.25"
    ],
    extras_require={
        'test': [
            'pytest>=8.0.0',
            'pytest-qt>=4.4.0',
            'pytest-cov>=4.1.0',
            'pytest-xvfb>=3.0.0'
        ]
    }
) 