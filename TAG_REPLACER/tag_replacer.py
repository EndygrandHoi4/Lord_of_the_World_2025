import os
import csv
import re
import sys
import traceback

# Конфигурация
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COUNTRY_TAGS_FILE = os.path.join(BASE_DIR, 'common', 'country_tags', '00_countries.txt')
TAG_MAPPING_FILE = os.path.join(BASE_DIR, 'tag_mapping.csv')
DIRS_TO_PROCESS = [
    os.path.join(BASE_DIR, 'history', 'states'),
    os.path.join(BASE_DIR, 'history', 'countries'),
    os.path.join(BASE_DIR, 'common', 'country_tags'),
    os.path.join(BASE_DIR, 'common', 'national_focus'),
    os.path.join(BASE_DIR, 'events'),
    os.path.join(BASE_DIR, 'common', 'state_category'),
]
FILE_EXTENSIONS = ('.txt', '.yml', '.yaml', '.csv')

def parse_country_tags():
    """Парсинг 00_countries.txt для извлечения старых и новых тегов"""
    tag_map = {}
    current_old_tag = None
    
    if not os.path.exists(COUNTRY_TAGS_FILE):
        print(f"⛔ Файл не найден: {COUNTRY_TAGS_FILE}")
        sys.exit(1)
    
    try:
        with open(COUNTRY_TAGS_FILE, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            
            # Ищем старый тег в комментарии
            if line.startswith('#'):
                # Извлекаем тег после решетки
                possible_tag = line[1:].strip().split()[0]
                if len(possible_tag) == 3:
                    current_old_tag = possible_tag.upper()
            
            # Ищем строку с новым тегом
            elif current_old_tag and '=' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    new_tag = parts[0].strip().upper()
                    # Проверяем что new_tag выглядит как тег (A01, B02 и т.д.)
                    if len(new_tag) == 3 and new_tag[0].isalpha() and new_tag[1:].isdigit():
                        tag_map[current_old_tag] = new_tag
                        current_old_tag = None
    
        print(f"Найдено соответствий тегов: {len(tag_map)}")
        return tag_map
    
    except Exception as e:
        print(f"Ошибка парсинга {COUNTRY_TAGS_FILE}: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

def save_tag_mapping(tag_map):
    """Сохранение соответствий тегов в CSV файл"""
    try:
        with open(TAG_MAPPING_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['OLD_TAG', 'NEW_TAG'])
            for old_tag, new_tag in tag_map.items():
                writer.writerow([old_tag, new_tag])
        print(f"Файл соответствий сохранен: {TAG_MAPPING_FILE}")
    except Exception as e:
        print(f"Ошибка сохранения CSV: {str(e)}")
        sys.exit(1)

def rename_country_files(tag_map):
    countries_dir = os.path.join(BASE_DIR, 'history', 'countries')
    if not os.path.exists(countries_dir):
        print(f"⚠️ Директория не найдена: {countries_dir}")
        return

    renamed_count = 0
    for filename in os.listdir(countries_dir):
        old_path = os.path.join(countries_dir, filename)
        if not os.path.isfile(old_path):
            continue
            
        # Ищем старый тег в начале имени файла
        base_name = os.path.splitext(filename)[0]
        if '-' in base_name:
            file_tag = base_name.split('-')[0].upper()
            
            if file_tag in tag_map:
                new_name = tag_map[file_tag] + filename[len(file_tag):]
                new_path = os.path.join(countries_dir, new_name)
                
                try:
                    os.rename(old_path, new_path)
                    print(f"Переименован: {filename} -> {new_name}")
                    renamed_count += 1
                except Exception as e:
                    print(f"Ошибка переименования {filename}: {str(e)}")
    
    print(f"Переименовано файлов: {renamed_count}/{len(tag_map)}")

def replace_in_file(file_path, tag_map):
    try:
        # Пропускаем сам файл тегов
        if os.path.basename(file_path) == '00_countries.txt':
            return False
            
        # Определение кодировки
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        content = None
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            print(f"⚠️ Не удалось прочитать файл: {file_path}")
            return False
            
        # Создаем регулярное выражение для точной замены тегов
        pattern = re.compile(r'\b(' + '|'.join(re.escape(tag) for tag in tag_map.keys()) + r')\b')
        new_content = pattern.sub(lambda m: tag_map[m.group(0)], content)
        
        # Дополнительная обработка для файлов истории государств
        if 'history/states' in file_path:
            # Замена в строках owner = TAG и controller = TAG
            for old_tag, new_tag in tag_map.items():
                new_content = re.sub(
                    r'owner\s*=\s*' + re.escape(old_tag), 
                    f'owner = {new_tag}', 
                    new_content, 
                    flags=re.IGNORECASE
                )
                new_content = re.sub(
                    r'controller\s*=\s*' + re.escape(old_tag), 
                    f'controller = {new_tag}', 
                    new_content, 
                    flags=re.IGNORECASE
                )
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False
    except Exception as e:
        print(f"⛔ Ошибка обработки {file_path}: {str(e)}")
        traceback.print_exc()
        return False

def process_directories(tag_map):
    processed_files = 0
    changed_files = 0
    
    for dir_path in DIRS_TO_PROCESS:
        if not os.path.exists(dir_path):
            print(f"⚠️ Директория не найдена: {dir_path}")
            continue
            
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.lower().endswith(FILE_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    processed_files += 1
                    if replace_in_file(file_path, tag_map):
                        changed_files += 1
                        print(f"Обновлен: {file_path}")
    
    print(f"\nОбработано файлов: {processed_files}")
    print(f"Изменено файлов: {changed_files}")

def main():
    print("=" * 50)
    print("HOI4 Advanced Tag Replacer v3.0")
    print("=" * 50)
    
    # Шаг 1: Парсинг 00_countries.txt
    print("\nЭтап 1: Анализ файла тегов стран...")
    tag_map = parse_country_tags()
    
    # Шаг 2: Сохранение в CSV
    print("\nЭтап 2: Создание файла соответствий...")
    save_tag_mapping(tag_map)
    
    # Шаг 3: Переименование файлов
    print("\nЭтап 3: Переименование файлов стран...")
    rename_country_files(tag_map)
    
    # Шаг 4: Замена тегов в содержимом
    print("\nЭтап 4: Обновление тегов в файлах...")
    process_directories(tag_map)
    
    print("\n" + "=" * 50)
    print("Готово! Обязательно проверьте:")
    print("- Файл common/country_tags/00_countries.txt")
    print("- Границы государств в history/states")
    print("- Национальные фокусы и решения")
    print("- Локализацию (может потребоваться ручная правка)")
    print("=" * 50)

if __name__ == "__main__":
    main()