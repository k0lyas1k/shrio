import csv
import json
import os
import re
from bs4 import BeautifulSoup
from const import session, headers


def save_to_csv(data, filename="oscar_data.csv"):
    try:
        if isinstance(data, dict):
            data = [data]

        fieldnames = set()
        for row in data:
            fieldnames.update(row.keys())
        fieldnames = list(fieldnames)

        file_exists = os.path.isfile(filename)

        with open(filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()

            for row in data:
                row_serialized = {}
                for k, v in row.items():
                    if isinstance(v, (dict, list)):
                        row_serialized[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        row_serialized[k] = v
                writer.writerow(row_serialized)

    except Exception as e:
        print("Ошибка при сохранении CSV:", e)


def parse_duration_to_minutes(text):
    text = text.lower()
    hours = re.search(r'(\d+)\s*час', text)
    minutes = re.search(r'(\d+)\s*мин', text)
    total = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    return total or None


def normalize_key(name):
    name = name.lower()
    name = re.sub(r'[^a-z0-9а-яё]+', '_', name)
    name = name.strip('_')
    return name or "unknown_field"


def parse_table(item):
    table = item.select_one('.newFilmInfo_infoDataTable table')
    if not table:
        return None

    rows = []
    for tr in table.select('tbody tr'):
        tds = [td.get_text(strip=True) for td in tr.select('td')]
        distributor_a = tr.select_one('td:nth-of-type(3) a')
        distributor = {
            'name': distributor_a.get_text(strip=True) if distributor_a else (tds[2] if len(tds) > 2 else None),
            'url': distributor_a.get('href') if distributor_a else None
        }
        row_data = {
            'date_raw': tds[0] if len(tds) > 0 else '',
            'country': tds[1] if len(tds) > 1 else '',
            'distributor': distributor,
            'rating': tds[3] if len(tds) > 3 else None
        }
        rows.append(row_data)
    return rows


def parse_film_info(html):
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.select_one('.newFilmInfo_info')
    if not container:
        return {}

    result = {}

    for item in container.select('.newFilmInfo_infoItem'):
        name_elem = item.select_one('.newFilmInfo_infoNameInner') or item.select_one('.newFilmInfo_infoName')
        if not name_elem:
            continue

        name_raw = name_elem.get_text(strip=True)
        key = normalize_key(name_raw)

        table_data = parse_table(item)
        if table_data:
            result[key] = table_data
            continue

        data_elem = item.select_one('.newFilmInfo_infoData')
        if not data_elem:
            result[key] = None
            continue

        text = data_elem.get_text(' ', strip=True)

        if 'продолжительность' in name_raw.lower():
            result[key] = {'raw': text, 'minutes': parse_duration_to_minutes(text)}
        elif 'год' in name_raw.lower():
            m = re.search(r'(\d{4})', text)
            result[key] = int(m.group(1)) if m else text
        elif 'другие названия' in name_raw.lower():
            variants = [t.strip() for t in re.split(r',|\n', text) if t.strip()]
            result[key] = variants
        else:
            result[key] = text

    return result


def get_category_oscar(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        categories_block = soup.find('div', class_='archiveColumnList_items')
        if not categories_block:
            raise Exception("Блок категорий не найден")

        categories = {}
        count = 1
        for cat_link in categories_block.find_all('a'):
            categories[count] = {"title": cat_link.text.strip(), "url": cat_link.get('href')}
            count += 1

        return categories
    except Exception as e:
        print("Ошибка в get_category_oscar:", e)
        return {}


def get_oscar(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')

        winner_link = soup.find('a', class_='movieItem_ref')
        if not winner_link:
            return {"type": "unknown"}

        winner_html = load_page(session, headers, winner_link.get('href'))
        if not winner_html:
            return "Не удалось загрузить страницу победителя"

        winner_soup = BeautifulSoup(winner_html, 'html.parser')

        if winner_soup.find('div', class_='filmSection filmSection-series page'):
            film_title_el = winner_soup.find('h1', class_='newFilmInfo_title')
            film_description_el = winner_soup.find('h1', class_='newFilmInfo_description')

            film_data = parse_film_info(winner_html)

            return {
                "type": "film",
                "title": film_title_el.get_text(strip=True) if film_title_el else None,
                "description": film_description_el.get_text(strip=True) if film_description_el else None,
                **film_data
            }
        else:
            return {"type": "unknown"}

    except Exception as e:
        print("Ошибка в get_oscar:", e)
        return str(e)


def load_page(session, headers, url):
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Ошибка при загрузке страницы: {e}")
        return None


def work_main_page(session, headers):
    html = load_page(session, headers, 'https://www.kinoafisha.info/awards/oscar/nominations/')
    if not html:
        raise Exception("Страница пуста")
    return get_category_oscar(html)


def work_oscar_page(session, headers, url):
    html = load_page(session, headers, url)
    if not html:
        raise Exception("Страница пуста")
    return get_oscar(html)


def main(session, headers):
    categories = work_main_page(session, headers)
    if not categories:
        raise Exception("Категорий нет")

    print("Выберите категорию:")
    for cat_id, cat in categories.items():
        print(f'{cat_id}. {cat["title"]}')

    while True:
        try:
            cat_id = int(input())
            if cat_id > len(categories) or cat_id <= 0:
                print("Такой категории нет")
            else:
                break
        except ValueError:
            print("Введите номер категории!")

    url = categories[cat_id]['url']
    data = work_oscar_page(session, headers, url)
    save_to_csv(data)


if __name__ == "__main__":
    main(session, headers)
