import os
import csv
import re
import sys
import traceback

# Конфигурация (проверьте пути!)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Автоматическое определение директории скрипта
TAG_MAPPING_FILE = os.path.join(BASE_DIR, 'tag_mapping.csv')
DIRS_TO_PROCESS = [
    os.path.join(BASE_DIR, 'history/states'),
    os.path.join(BASE_DIR, 'history/countries'),
    os.path.join(BASE_DIR, 'common/country_tags'),
    os.path.join(BASE_DIR, 'common/national_focus'),
    os.path.join(BASE_DIR, 'events'),
]
FILE_EXTENSIONS = ('.txt', '.yml', '.yaml', '.csv')

def load_tag_mapping():
    tag_map = {}
    try:
        with open(TAG_MAPPING_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_tag = row['OLD_TAG'].strip().upper()
                new_tag = row['NEW_TAG'].strip().upper()
                if old_tag and new_tag:
                    tag_map[old_tag] = new_tag
        print(f"Загружено {len(tag_map)} соответствий тегов")
        return tag_map
    except Exception as e:
        print(f"Ошибка загрузки tag_mapping.csv: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

def rename_country_files(tag_map):
    countries_dir = os.path.join(BASE_DIR, 'history/countries')
    if not os.path.exists(countries_dir):
        print(f"⚠️ Директория не найдена: {countries_dir}")
        return

    renamed_count = 0
    for filename in os.listdir(countries_dir):
        old_path = os.path.join(countries_dir, filename)
        if not os.path.isfile(old_path):
            continue
            
        for old_tag, new_tag in tag_map.items():
            if filename.upper().startswith(old_tag + '-'):
                new_name = new_tag + filename[len(old_tag):]
                new_path = os.path.join(countries_dir, new_name)
                
                try:
                    os.rename(old_path, new_path)
                    print(f"Переименован: {filename} -> {new_name}")
                    renamed_count += 1
                except Exception as e:
                    print(f"Ошибка переименования {filename}: {str(e)}")
                break
    print(f"Переименовано файлов: {renamed_count}/{len(tag_map)}")

def replace_in_file(file_path, tag_map):
    try:
        # Определение кодировки (HoI4 часто использует Windows-1252)
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
            
        # Создаем регулярное выражение с границами слов
        pattern = re.compile(r'\b(' + '|'.join(re.escape(tag) for tag in tag_map.keys()) + r')\b')
        new_content = pattern.sub(lambda m: tag_map[m.group(0)], content)
        
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
    print("HOI4 Tag Replacer v2.0")
    print("=" * 50)
    
    tag_map = load_tag_mapping()
    print("\nЭтап 1: Переименование файлов стран...")
    rename_country_files(tag_map)
    
    print("\nЭтап 2: Замена тегов в файлах...")
    process_directories(tag_map)
    
    print("\nГотово! Не забудьте проверить:")
    print("- Локализации (файлы .yml в /localisation)")
    print("- Графические файлы (флаги/эмблемы)")
    print("- Специальные скриптовые файлы (events/decisions)")

if __name__ == "__main__":
    main()