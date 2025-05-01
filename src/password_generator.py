import hashlib
import random
import string
from typing import List, Dict, Tuple

class PasswordGenerator:
    def __init__(self):
        self.special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        self.number_mapping = {
            'а': '4', 'о': '0', 'е': '3', 'и': '1',
            'з': '3', 'б': '6', 'т': '7', 'ч': '4'
        }
        self.similar_chars = {
            'а': '@', 'о': '0', 'и': '1', 'е': '3',
            's': '$', 'a': '@', 'i': '!', 'o': '0',
            'l': '1', 'e': '3', 't': '7', 'b': '8'
        }

    def generate_from_associations(
        self,
        words: List[str],
        min_length: int = 12,
        include_numbers: bool = True,
        include_special: bool = True,
        include_caps: bool = True
    ) -> Tuple[str, Dict[str, str]]:
        """
        Генерирует пароль на основе ассоциативных слов и возвращает его вместе с информацией о трансформации.
        """
        # Создаем уникальную строку из слов
        base = "".join(words).lower()
        
        # Создаем хеш для обеспечения уникальности
        word_hash = hashlib.sha256("".join(words).encode()).hexdigest()[:8]
        # Если цифры не разрешены, используем только буквенную часть хеша
        if not include_numbers:
            word_hash = ''.join(c for c in word_hash if not c.isdigit())
        
        # Начальное преобразование
        password = ""
        transformations = {}
        
        # Преобразуем каждое слово
        for word in words:
            word = word.lower()
            transformed = ""
            word_trans = {}
            
            for char in word:
                if include_numbers and char in self.number_mapping:
                    transformed += self.number_mapping[char]
                    word_trans[char] = self.number_mapping[char]
                elif include_special and char in self.similar_chars and (include_numbers or not self.similar_chars[char].isdigit()):
                    transformed += self.similar_chars[char]
                    word_trans[char] = self.similar_chars[char]
                else:
                    if include_caps and random.random() > 0.5:
                        transformed += char.upper()
                        word_trans[char] = char.upper()
                    else:
                        transformed += char
                        word_trans[char] = char
            
            password += transformed
            transformations[word] = word_trans
        
        # Добавляем часть хеша для уникальности
        if word_hash:  # добавляем только если есть не-цифровые символы
            password += word_hash[:4]
        
        # Добавляем как минимум один специальный символ, если требуется
        if include_special:
            password += random.choice(self.special_chars)
        
        # Добавляем как минимум одну цифру, если требуется
        if include_numbers:
            password += random.choice(string.digits)
        
        # Добавляем случайные символы, если пароль слишком короткий
        while len(password) < min_length:
            if include_special and random.random() > 0.7:
                password += random.choice(self.special_chars)
            elif include_numbers and random.random() > 0.5:
                password += random.choice(string.digits)
            else:
                password += random.choice(string.ascii_letters)
        
        # Перемешиваем пароль
        password_list = list(password)
        random.shuffle(password_list)
        final_password = "".join(password_list)
        
        return final_password, transformations

    def explain_transformation(self, words: List[str], transformations: Dict[str, Dict[str, str]]) -> str:
        """
        Создает понятное объяснение того, как был сформирован пароль.
        """
        explanation = "Пароль был сформирован следующим образом:\n\n"
        
        for word in words:
            if word in transformations:
                explanation += f"Слово '{word}':\n"
                for original, transformed in transformations[word].items():
                    if original != transformed:
                        explanation += f"  - '{original}' заменено на '{transformed}'\n"
            
        explanation += "\nДобавлен уникальный хеш и символы для усиления безопасности."
        return explanation

    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Проверяет силу пароля и возвращает результат с объяснением.
        """
        issues = []
        
        if len(password) < 12:
            issues.append("Длина пароля должна быть не менее 12 символов")
        
        if not any(c.isupper() for c in password):
            issues.append("Пароль должен содержать заглавные буквы")
            
        if not any(c.islower() for c in password):
            issues.append("Пароль должен содержать строчные буквы")
            
        if not any(c.isdigit() for c in password):
            issues.append("Пароль должен содержать цифры")
            
        if not any(c in self.special_chars for c in password):
            issues.append("Пароль должен содержать специальные символы")
        
        is_valid = len(issues) == 0
        message = "Пароль соответствует всем требованиям" if is_valid else "\n".join(issues)
        
        return is_valid, message 