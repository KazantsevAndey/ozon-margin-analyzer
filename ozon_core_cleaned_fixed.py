def calculate_all(api_key, perf_key, perf_client_id, price, client_id):  
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta
    import requests
    import io

 
    """Загрузили прайс с себестоимостью или взяли его с гугл диска."""
    
    #price.head()
    
    url_create = "https://api-seller.ozon.ru/v1/report/create"
    
    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    url = "https://api-seller.ozon.ru/v3/finance/transaction/list"
    
    def fetch_transactions_and_show_nachislen(start_date, end_date, period_name):
        payload = {
            "filter": {
                "date": {"from": start_date, "to": end_date},
                "operation_type": [],
                "posting_number": "",
                "transaction_type": "all"
            },
            "page": 1,
            "page_size": 1000
        }
    
        all_transactions = []
        while True:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                operations = data.get("result", {}).get("operations", [])
                all_transactions.extend(operations)
                print(f"🔄 {period_name}: Страница {payload['page']} загружена, записей: {len(operations)}")
                if len(operations) < 1000:
                    break
                payload["page"] += 1
            else:
                print(f"❌ {period_name}: Ошибка: {response.status_code}")
                print("Ответ сервера:", response.text)
                break
    
    
        transactions_df = pd.DataFrame(all_transactions)
        print(f"✅ {period_name}: Всего записей: {len(transactions_df)}")
    
        nachislen = transactions_df.groupby('operation_type_name', as_index=False)['amount'].sum()
    
        total_sum = nachislen['amount'].sum()
    
        total_row = pd.DataFrame([{"operation_type_name": "Общая сумма", "amount": total_sum}])
        nachislen = pd.concat([nachislen, total_row], ignore_index=True)
    
        print(f"📊 Итоговая таблица начислений ({period_name}):")
        print(nachislen)
    
        return transactions_df, nachislen
    
    
    def process_items(transactions_df, period_name):
    
        filtered_df = transactions_df[transactions_df['operation_type_name'] == "Доставка покупателю"]
    
        if 'items' in filtered_df.columns:
            # Разворачиваем поле items
            items_data = filtered_df['items'].explode()
    
            # Преобразуем каждую строку (JSON) в отдельные строки DataFrame
            items_expanded = pd.json_normalize(items_data)
    
            # Проверяем, есть ли поля name и sku
            if 'name' in items_expanded.columns and 'sku' in items_expanded.columns:
                # Извлекаем название и SKU
                result = items_expanded[['name', 'sku']].copy()
    
                # Консолидация: считаем количество по name и sku
                consolidated_result = result.value_counts(['name', 'sku']).reset_index()
                consolidated_result.columns = ['name', 'sku', 'count']
    
                # Вывод таблицы для проверки
                print(f"📊 Таблица товаров ({period_name}):")
                print(consolidated_result)
    
                return consolidated_result
            else:
                print(f"⚠ {period_name}: Поля 'name' или 'sku' отсутствуют в items.")
                return pd.DataFrame()
        else:
            print(f"⚠ {period_name}: Поле 'items' отсутствует в данных.")
            return pd.DataFrame()
    
    # --- Даты для двух периодов ---
    # Вчера
    yesterday = datetime.now() - timedelta(days=1)
    date_from_yesterday = yesterday.strftime("%Y-%m-%dT00:00:00.000Z")
    date_to_yesterday = yesterday.strftime("%Y-%m-%dT23:59:59.000Z")
    
    # С начала месяца до вчера
    start_of_month = datetime.now().replace(day=1)
    date_from_month = start_of_month.strftime("%Y-%m-%dT00:00:00.000Z")
    date_to_today = yesterday.strftime("%Y-%m-%dT23:59:59.000Z")
    
    # --- Обработка данных ---
    print("🔄 Обработка данных за вчера...")
    transactions_yesterday, nachislen_yesterday = fetch_transactions_and_show_nachislen(
        date_from_yesterday, date_to_yesterday, "За вчера"
    )
    
    print("\n🔄 Обработка данных с начала месяца...")
    transactions_month, nachislen_month = fetch_transactions_and_show_nachislen(
        date_from_month, date_to_today, "С начала месяца"
    )
    
    # --- Обработка "Доставка покупателю" ---
    print("\n🔄 Разворачивание items за вчера...")
    items_yesterday = process_items(transactions_yesterday, "За вчера")
    
    print("\n🔄 Разворачивание items с начала месяца...")
    items_month = process_items(transactions_month, "С начала месяца")
    
    # --- Сохранение результатов ---
    #nachislen_yesterday.to_excel("nachislen_yesterday.xlsx", index=False)
    #nachislen_month.to_excel("nachislen_month.xlsx", index=False)
    
    #if not items_yesterday.empty:
    #    items_yesterday.to_excel("items_yesterday.xlsx", index=False)
    #    print("✅ Таблица товаров за вчера сохранена: items_yesterday.xlsx")
    
    #if not items_month.empty:
    #    items_month.to_excel("items_month.xlsx", index=False)
    #    print("✅ Таблица товаров с начала месяца сохранена: items_month.xlsx")
    
    """# Ozon. Финансы. Начисления. Товары.
    
    ##  Что делаем?
    
    Стягиваем по API данные о продажах.  
    Берём два периода:
    - **С начала текущего месяца**
    - **За вчерашний день**
    
    Смотрим информацию о **фактических начислениях**: сколько начислено, за что именно, какие операции проходят в отчётах Ozon.
    
    ---
    
    ##  Как это работает
    
    ### 1. Получаем транзакции через API
    Обращаемся к `https://api-seller.ozon.ru/v3/finance/transaction/list`  
    Поддерживается постраничная загрузка (`page_size = 1000`), так что стягиваем всё, пока не кончится список.
    
    ### 2. Фильтруем и группируем
    Создаём датафрейм, группируем данные по `operation_type_name`.  
    Результат — таблица начислений по типам операций:
    - Доставка
    - Комиссия
    - Возврат и т.д.
    
    В конец добавляем строку **“Общая сумма”**, чтобы видеть итог по периоду.
    
    ---
    
    ##  Что с товарами?
    
    Из операций типа `"Доставка покупателю"` достаём поле `items`, где лежат конкретные товары.  
    Далее:
    1. **Разворачиваем JSON**
    2. Достаём `name` и `sku`
    3. Считаем количество повторений по каждой паре
    
    Результат: уже на этом этапе мы можем контролировать начисление и комиссии по категориям.
    ---
    
    ##  Выгрузка
    
    Если есть данные — сохраняем:
    - `items_yesterday.xlsx` — доставка по товарам за вчера
    - `items_month.xlsx` — доставка по товарам за месяц
    
    (Начисления тоже можно выгружать — строки с `to_excel` закомментированы и готовы к использованию)
    
    
    ## Зачем это нужно?
    
    - Видим, какие товары реально отгружаются
    - Контролируем начисления и удержания по категориям
    - Сравниваем динамику дня и месяца
    - Используем как базу для отчётов, анализа SKU, дальше подтянем себестоимость и получим расчет маржи за вчерашний день и с начала месяца. Сначала общую по акаунту, потом пойдем к каждой SKU.
    
    """
    
    if 'Ozon SKU ID' in price.columns:
        # Объединяем итоговый DataFrame (items_yesterday и items_month) с price
        final_yesterday = items_yesterday.merge(price[['Ozon SKU ID', 'Цена в рублях']],
                                                left_on='sku', right_on='Ozon SKU ID',
                                                how='left')
    
        final_month = items_month.merge(price[['Ozon SKU ID', 'Цена в рублях']],
                                        left_on='sku', right_on='Ozon SKU ID',
                                        how='left')
    
        # Переименовываем и упорядочиваем колонки
        final_yesterday.rename(columns={'Цена в рублях': 'Себестоимость'}, inplace=True)
        final_month.rename(columns={'Цена в рублях': 'Себестоимость'}, inplace=True)
    
        final_yesterday = final_yesterday[['name', 'sku', 'count', 'Себестоимость']]
        final_month = final_month[['name', 'sku', 'count', 'Себестоимость']]
    
        # Вывод для проверки
        #print("📊 Итоговая таблица за вчера с себестоимостью:")
        #print(final_yesterday)
    
        #print("\n📊 Итоговая таблица с начала месяца с себестоимостью:")
        #print(final_month)
    else:
        print("⚠ Колонка 'Ozon SKU ID' отсутствует в price. Проверьте данные.")
    
    """## Объединяем с прайс-листом
    
    Если в прайс-листе (`price`) есть колонка `Ozon SKU ID`,  
    то добавляем **себестоимость** к таблицам продаж за вчера и месяц.
    
    - Используем `merge()` по `sku`
    - Подтягиваем поле `Цена в рублях`
    - Переименовываем колонку в `Себестоимость`
    - Формируем финальные таблицы:
    Если нужной колонки нет — скрипт сообщает об этом.  
    Это нужно для расчёта маржи и более точной аналитики по SKU.
    """
    
    if 'count' in final_yesterday.columns and 'Себестоимость' in final_yesterday.columns:
        final_yesterday['Сумма себестоимости'] = final_yesterday['count'] * final_yesterday['Себестоимость']
        #print("📊 Итоговая таблица за вчера с расчетом суммы себестоимости:")
        #print(final_yesterday)
    else:
        print("⚠ Не найдены колонки 'count' или 'Себестоимость' в итоговой таблице за вчера.")
    
    if 'count' in final_month.columns and 'Себестоимость' in final_month.columns:
        final_month['Сумма себестоимости'] = final_month['count'] * final_month['Себестоимость']
        #print("\n📊 Итоговая таблица с начала месяца с расчетом суммы себестоимости:")
        #print(final_month)
    else:
        print("⚠ Не найдены колонки 'count' или 'Себестоимость' в итоговой таблице с начала месяца.")
    
    """## Расчёт суммы себестоимости
    
    Если в таблицах за вчера и за месяц есть нужные колонки (`count` и `Себестоимость`),  
    добавляем новую колонку
    Это даёт понимание общей закупочной стоимости отгруженных товаров за период.  
    Если колонок нет — скрипт уведомит.
    """
    
    if 'operation_type_name' in nachislen_yesterday.columns and 'amount' in nachislen_yesterday.columns:
        total_otgruzka_yesterday = round(
            nachislen_yesterday.loc[nachislen_yesterday['operation_type_name'] == 'Общая сумма', 'amount'].values[0], 2
        )
        total_sebestoimost_yesterday = round(final_yesterday['Сумма себестоимости'].sum(), 2)
        sebestoimost_ratio_yesterday = round((total_sebestoimost_yesterday / total_otgruzka_yesterday) * 100, 2)
        marzha_percentage_yesterday = round(100 - sebestoimost_ratio_yesterday, 2)
    
    
        print("📊 Итоги за вчера:")
        print(f"Общая себестоимость: {total_sebestoimost_yesterday} руб.")
        print(f"Общая сумма отгрузки: {total_otgruzka_yesterday} руб.")
        print(f"Доля себестоимости: {sebestoimost_ratio_yesterday}%")
        print(f"Маржинальность: {marzha_percentage_yesterday}%")
    else:
        print("⚠ Не найдены необходимые колонки в данных за вчера.")
    
    if 'operation_type_name' in nachislen_month.columns and 'amount' in nachislen_month.columns:
    
        total_otgruzka_month = round(
            nachislen_month.loc[nachislen_month['operation_type_name'] == 'Общая сумма', 'amount'].values[0], 2
        )
        total_sebestoimost_month = round(final_month['Сумма себестоимости'].sum(), 2)
        sebestoimost_ratio_month = round((total_sebestoimost_month / total_otgruzka_month) * 100, 2)
    
        marzha_percentage_month = round(100 - sebestoimost_ratio_month, 2)
    
    
        print("\n📊 Итоги с начала месяца:")
        print(f"Общая себестоимость: {total_sebestoimost_month} руб.")
        print(f"Общая сумма отгрузки: {total_otgruzka_month} руб.")
        print(f"Доля себестоимости: {sebestoimost_ratio_month}%")
        print(f"Маржинальность: {marzha_percentage_month}%")
    else:
        print("⚠ Не найдены необходимые колонки в данных с начала месяца.")
    
    """## Расчёт Маржинальности
    
    Если в таблицах начислений (`nachislen`) и финальных таблицах с себестоимостью есть нужные колонки,  
    считаем следующие показатели:
    
    ###  Для каждого периода:
    - **Общая сумма отгрузки** — по строке `"Общая сумма"` в начислениях
    - **Общая себестоимость** — сумма по колонке `"Сумма себестоимости"` в финальной таблице
    - **Доля себестоимости** от выручки (в %)
    - **Маржа** (в %), как разница между выручкой и себестоимостью
    
    """
    
    def expand_items_with_amount(transactions_df, period_name):
    
        filtered_transactions = transactions_df[transactions_df['operation_type_name'] == "Доставка покупателю"]
    
        items_expanded = []
        for idx, row in filtered_transactions.iterrows():
            if isinstance(row['items'], list) and len(row['items']) > 0:
                num_items = len(row['items'])
                amount_per_item = row['amount'] / num_items
                for item in row['items']:
                    item_row = {
                        'name': item.get('name', 'Неизвестное название'),
                        'sku': item.get('sku', 'Неизвестный SKU'),
                        'amount': amount_per_item
                    }
                    items_expanded.append(item_row)
    
    
        result_table = pd.DataFrame(items_expanded)
        total_original = filtered_transactions['amount'].sum()
        total_expanded = result_table['amount'].sum()
    
        print(f"📊 {period_name}:")
        print(f"Сумма из исходного DataFrame: {total_original}")
        print(f"Сумма после развёртки: {total_expanded}")
    
        if total_original == total_expanded:
            print("✅ Суммы совпадают. Всё работает корректно.")
        else:
            print("⚠️ Суммы не совпадают! Нужно проверить данные.")
    
        return result_table
    
    # --- Развёртка данных за два периода ---
    print("🔄 Разворачивание товаров за вчера...")
    expanded_yesterday = expand_items_with_amount(transactions_yesterday, "За вчера")
    
    print("\n🔄 Разворачивание товаров с начала месяца...")
    expanded_month = expand_items_with_amount(transactions_month, "С начала месяца")
    
    # --- Сохранение результатов ---
    #expanded_yesterday.to_excel("expanded_yesterday.xlsx", index=False)
    #expanded_month.to_excel("expanded_month.xlsx", index=False)
    
    #print("\n✅ Итоговые таблицы сохранены:")
    #print(" - Товары за вчера: expanded_yesterday.xlsx")
    #print(" - Товары с начала месяца: expanded_month.xlsx")
    
    """## Развёртка товаров и распределение сумм
    
    Функция `expand_items_with_amount()` предназначена для **глубокой детализации отгрузок**.  
    Мы не просто смотрим, сколько раз продавался товар,  
    а **распределяем сумму отгрузки по каждому конкретному SKU**.
    
    ---
    
    ###  Что происходит:
    
    1. Фильтруем транзакции по типу `"Доставка покупателю"`
    2. Для каждой отгрузки:
       - Проверяем, есть ли поле `items`
       - Считаем, сколько товаров было в отгрузке
       - **Распределяем сумму `amount` поровну между ними**
    3. Формируем таблицу, где:
    
    Каждая строка — отдельный товар, с привязанной частью суммы.
    
    ---
    
    ###  Проверка корректности:
    
    - Суммируем `amount` в оригинальных транзакциях
    - Сравниваем с суммой в развернутой таблице
    - Если суммы **совпадают** — считаем, что распределение корректно
    
    ---
    
    ###  Выгрузка:
    - `expanded_yesterday.xlsx` — развёртка за вчера
    - `expanded_month.xlsx` — развёртка с начала месяца
    
    ---
    
    Эта таблица пригодится для расчёта точной выручки по каждому SKU,  
    ведь нам нужен отчёт на уровне товара, а не только по операциям.
    """
    
    # Подсчёт NaN в колонке 'name'
    nan_count_yesterday = expanded_yesterday['name'].isna().sum()
    nan_count_month = expanded_month['name'].isna().sum()
    
    print(f"Количество NaN в колонке 'name' за вчера: {nan_count_yesterday}")
    print(f"Количество NaN в колонке 'name' с начала месяца: {nan_count_month}")
    
    """##  Проверка на пустые названия товаров (NaN в `name`)
    
    После развёртки бывает, что в колонке `name` попадаются пустые значения.  
    Это может говорить о том, что:
    - В `items` пришёл товар без названия
    - Либо поле `name` не передано в API
    
    Проверяем количество таких случаев отдельно:
    - За вчера
    - С начала месяца
    
    Выводим:
     Это важно, чтобы **не потерять позиции в отчётах** и понимать, где нужно уточнить данные (например, по SKU).
    """
    
    aggregated_yesterday = expanded_yesterday.groupby('name', as_index=False).agg({'amount': 'sum'})
    aggregated_yesterday = aggregated_yesterday.sort_values(by='amount', ascending=False)
    
    aggregated_month = expanded_month.groupby('name', as_index=False).agg({'amount': 'sum'})
    aggregated_month = aggregated_month.sort_values(by='amount', ascending=False)
    total_amount_yesterday = aggregated_yesterday['amount'].sum()
    total_amount_month = aggregated_month['amount'].sum()
    print("📊 Агрегированные данные за вчера:")
    print(aggregated_yesterday.head())
    print(f"Общая сумма за вчера: {total_amount_yesterday}")
    
    print("\n📊 Агрегированные данные с начала месяца:")
    print(aggregated_month.head())
    print(f"Общая сумма с начала месяца: {total_amount_month}")
    
    """## Агрегация выручки по товарам
    
    После развёртки всех товаров мы группируем данные по `name`,  
    чтобы получить **итоговую сумму выручки по каждому товару**.
    
    ### Что делаем:
    - Группируем по `name`, суммируем `amount`
    - Сортируем по убыванию суммы (топ продаваемых товаров сверху)
    - Считаем общую выручку за:
      - Вчера
      - С начала месяца
    """
    
    expanded_yesterday['Сумма по name'] = expanded_yesterday.groupby('name')['amount'].transform('sum')
    expanded_yesterday['Общая сумма amount'] = expanded_yesterday['amount'].sum()
    
    expanded_month['Сумма по name'] = expanded_month.groupby('name')['amount'].transform('sum')
    expanded_month['Общая сумма amount'] = expanded_month['amount'].sum()
    
    total_amount_yesterday = expanded_yesterday['amount'].sum()
    total_amount_month = expanded_month['amount'].sum()
    
    print("📊 Обновлённая таблица за вчера:")
    print(expanded_yesterday.head())
    print(f"Общая сумма за вчера: {total_amount_yesterday}")
    
    print("\n📊 Обновлённая таблица с начала месяца:")
    print(expanded_month.head())
    print(f"Общая сумма с начала месяца: {total_amount_month}")
    
    """## Расчёт долей по каждому товару
    
    Для более глубокого анализа внутри `expanded_*`,  
    добавляем два новых столбца:
    
    ### Для каждого периода (`вчера` и `месяц`):
    
    - **Сумма по name** — общая сумма `amount`, приходящаяся на каждый `name`  
      _(используем `groupby().transform('sum')` — чтобы сохранить построчную детализацию)_
    
    - **Общая сумма amount** — единая сумма по всему периоду, проставляется в каждой строке  
      _(это позволяет быстро считать долю строки от общего оборота)_
    
    Выводим для проверки: `head()` + общая сумма
    """
    
    # --- Расчёты для вчера ---
    final_yesterday = final_yesterday.merge(aggregated_yesterday[['name', 'amount']], on='name', how='left')
    final_yesterday['Прибыль'] = final_yesterday['amount'] - final_yesterday['Сумма себестоимости']
    final_yesterday['Маржинальность (%)'] = (final_yesterday['Прибыль'] / final_yesterday['amount']) * 100
    
    общая_сумма_продаж_yesterday = final_yesterday['amount'].sum()
    final_yesterday['Доля продаж (%)'] = (final_yesterday['amount'] / общая_сумма_продаж_yesterday) * 100
    
    # Округление
    final_yesterday['Прибыль'] = final_yesterday['Прибыль'].round(0)
    final_yesterday['Маржинальность (%)'] = final_yesterday['Маржинальность (%)'].round(2)
    final_yesterday['Доля продаж (%)'] = final_yesterday['Доля продаж (%)'].round(2)
    
    # Сортировка
    final_yesterday = final_yesterday.sort_values(by='amount', ascending=False).reset_index(drop=True)
    
    # --- Расчёты для месяца ---
    final_month = final_month.merge(aggregated_month[['name', 'amount']], on='name', how='left')
    final_month['Прибыль'] = final_month['amount'] - final_month['Сумма себестоимости']
    final_month['Маржинальность (%)'] = (final_month['Прибыль'] / final_month['amount']) * 100
    
    общая_сумма_продаж_month = final_month['amount'].sum()
    final_month['Доля продаж (%)'] = (final_month['amount'] / общая_сумма_продаж_month) * 100
    
    # Округление
    final_month['Прибыль'] = final_month['Прибыль'].round(0)
    final_month['Маржинальность (%)'] = final_month['Маржинальность (%)'].round(2)
    final_month['Доля продаж (%)'] = final_month['Доля продаж (%)'].round(2)
    
    # Сортировка
    final_month = final_month.sort_values(by='amount', ascending=False).reset_index(drop=True)
    
    # --- Вывод ---
    print("📊 Итоговая таблица за вчера:")
    print(final_yesterday.head())
    
    print("\n📊 Итоговая таблица с начала месяца:")
    print(final_month.head())
    
    """## Финальные расчёты по прибыли и маржинальности
    
    Объединяем данные по отгрузкам и себестоимости,  
    чтобы получить **полную картину эффективности по каждому товару**.
    
    ---
    
    ### Что считаем:
    
    - `Прибыль`  
    - `Маржинальность (%)`
    - `Доля продаж (%)`
    
    Всё это считается отдельно:
    - Для **вчера**
    - Для **начала месяца**
    
    ---
    
    ### Финальная обработка:
    
    - Все значения округляются (`Прибыль` до целого, проценты — до сотых)
    - Сортируем по выручке (`amount`) в убывающем порядке
    - Получаем таблицы с полями: ame | sku | count | Себестоимость | amount | Прибыль | Маржинальность (%) | Доля продаж (%) Это итоговый отчёт: по нему видно всё — от оборота до прибыли по SKU.
    
    ## На этом можно остановиться. Но можно пойти дальше и добавить к каждому SKU ДРР(долю рекламных расходов).##
    
     Для этого придется автоизоваться через Озон Перфоманс чтобы получить инофарацию. А также придется на этапе создания рекламного инструмента заводить кампании определенным образом.
    
    1. Одна рекламная кампания - 1 SKU
    
    2. Названия кампании = название SKU чтобы можно было нехитрым способом к этому названию "вязаться".
    """
    
    url_token = "https://api-performance.ozon.ru/api/client/token"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "client_id": perf_client_id,
        "client_secret": perf_key,
        "grant_type": "client_credentials"
    }
    
    response = requests.post(url_token, headers=headers, json=payload)
    if response.status_code == 200:
        access_token = response.json()["access_token"]
        print(f"Токен успешно получен: {access_token}")
    else:
        print("Ошибка авторизации:", response.status_code)
        print("Ответ сервера:", response.text)
    
    """## Получение access token для Ozon Performance API
    
    Для доступа к рекламному API Ozon Performance (performance.ozon.ru),  
    используется авторизация по протоколу OAuth 2.0 (`client_credentials`).
    
    ### Шаги:
    1. Отправляем POST-запрос на `https://api-performance.ozon.ru/api/client/token`
    2. В `payload` передаём:
       - `client_id`
       - `client_secret`
       - `grant_type = "client_credentials"`
    3. В ответ получаем `access_token`, который используем в последующих запросах.
    
    Токен действителен ограниченное время. Храним его в переменной `access_token` и обновляем при необходимости.
    """
    
    yesterday = datetime.now() - timedelta(days=1)
    date_from_yesterday = yesterday.strftime("%Y-%m-%dT00:00:00Z")
    date_to_yesterday = yesterday.strftime("%Y-%m-%dT23:59:59Z")
    
    start_of_month = datetime.now().replace(day=1)
    date_from_month = start_of_month.strftime("%Y-%m-%dT00:00:00Z")
    date_to_today = yesterday.strftime("%Y-%m-%dT23:59:59Z")
    
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    url_report = "https://api-performance.ozon.ru/api/client/statistics/campaign/product/json"
    
    
    def fetch_report(start_date, end_date, period_name):
        payload = {
            "from": start_date,
            "to": end_date
        }
    
        response = requests.get(url_report, headers=headers, params=payload)
    
        if response.status_code == 200:
            print(f"✅ {period_name}: Отчет успешно получен!")
            return response.json()
        else:
            print(f"❌ {period_name}: Ошибка получения отчета:", response.status_code)
            print("Ответ сервера:", response.text)
            return None
    print("🔄 Получение отчета за вчера...")
    report_yesterday = fetch_report(date_from_yesterday, date_to_yesterday, "За вчера")
    
    print("\n🔄 Получение отчета с начала месяца...")
    report_month = fetch_report(date_from_month, date_to_today, "С начала месяца")
    if report_yesterday:
        print("\n📊 Данные за вчера:")
        #print(report_yesterday)
    
    if report_month:
        print("\n📊 Данные с начала месяца:")
        #print(report_month)
    
    """## Получение отчётов по рекламе Ozon Performance
    
    Этот блок отвечает за запрос статистики по продуктовым рекламным кампаниям через Ozon Performance API.
    
    ---
    
    ### Авторизация
    
    Используется заранее полученный `access_token`, передаётся в заголовке:
    ---
    
    ### ⏱Запрашиваемые периоды:
    - **За вчера**
    - **С начала месяца до вчерашнего дня**
    
    Формат даты: ISO 8601 (`%Y-%m-%dT%H:%M:%SZ`)
    Передаём параметры:
    ```json
    {
      "from": "2024-04-07T00:00:00Z",
      "to":   "2024-04-07T23:59:59Z"
    }
    """
    
    # === Фильтрация данных отчета ===
    if report_yesterday:
        df_yesterday = pd.DataFrame(report_yesterday.get('rows', []))
        df_filtered_yesterday = df_yesterday[df_yesterday['status'] == 'running']
        df_filtered_yesterday['moneySpent'] = pd.to_numeric(df_filtered_yesterday['moneySpent'], errors='coerce').fillna(0).round(0).astype(int)
        df_money_spent_yesterday = df_filtered_yesterday[['title', 'moneySpent']].rename(columns={'title': 'name', 'moneySpent': 'ДРР'})
    
        # Объединение с final_result за вчера
        final_result_yesterday = final_yesterday.merge(df_money_spent_yesterday, on='name', how='left')
        final_result_yesterday['ДРР'] = final_result_yesterday['ДРР'].fillna(0).astype(int)
        #print("📊 Итоговая таблица за вчера с учетом ДРР:")
        #print(final_result_yesterday.head())
    
    if report_month:
        df_month = pd.DataFrame(report_month.get('rows', []))
        df_filtered_month = df_month[df_month['status'] == 'running']
        df_filtered_month['moneySpent'] = pd.to_numeric(df_filtered_month['moneySpent'], errors='coerce').fillna(0).round(0).astype(int)
        df_money_spent_month = df_filtered_month[['title', 'moneySpent']].rename(columns={'title': 'name', 'moneySpent': 'ДРР'})
    
        # Объединение с final_result за месяц
        final_result_month = final_month.merge(df_money_spent_month, on='name', how='left')
        final_result_month['ДРР'] = final_result_month['ДРР'].fillna(0).astype(int)
        #print("\n📊 Итоговая таблица с начала месяца с учетом ДРР:")
        #print(final_result_month.head())
    
    """## Добавление рекламных расходов (ДРР) в финальные таблицы
    
    После получения рекламного отчёта из Ozon Performance API,  
    мы фильтруем активные кампании (`status == "running"`),  
    и достаём ключевые данные:
    
    - `title` — название товара (совпадает с `name` в финальных таблицах)
    - `moneySpent` — сумма потраченная на рекламу
    
    ---
    
    ###  Что делаем:
    
    1. Преобразуем JSON-ответ в `DataFrame`
    2. Оставляем только активные строки (`status == "running"`)
    3. Преобразуем `moneySpent` в числовой формат и округляем
    4. Формируем таблицу с: name | ДРР
    5. Объединяем с `final_yesterday` и `final_month` по `name`
    6. Заполняем пропущенные значения нулями (`fillna(0)`)
    
    ---
    
    ### Результат:
    
    Получаем финальные таблицы за вчера и месяц с учётом ДРР:
    name | sku | count | amount | Прибыль | Маржинальность (%) | Доля продаж (%) | ДРР
    """
    
    # --- Переименовываем столбцы ---
    final_result_yesterday.rename(columns={
        'amount': 'Сумма отгрузки',
        'cost': 'Себестоимость'
    }, inplace=True)
    
    final_result_month.rename(columns={
        'amount': 'Сумма отгрузки',
        'cost': 'Себестоимость'
    }, inplace=True)
    
    # --- Расчет ДРР в процентах ---
    final_result_yesterday['ДРР (%)'] = (
        (final_result_yesterday['ДРР'] / final_result_yesterday['Сумма отгрузки'] * 100)
        .fillna(0).round(2)
    )
    
    final_result_month['ДРР (%)'] = (
        (final_result_month['ДРР'] / final_result_month['Сумма отгрузки'] * 100)
        .fillna(0).round(2)
    )
    
    
    final_result_yesterday['Маржинальность с учетом ДРР'] = (
        (final_result_yesterday['Сумма отгрузки'] -
         final_result_yesterday['Сумма себестоимости'] -
         final_result_yesterday['ДРР']) /
        final_result_yesterday['Сумма отгрузки'] * 100
    ).fillna(0).round(2)
    
    final_result_month['Маржинальность с учетом ДРР'] = (
        (final_result_month['Сумма отгрузки'] -
         final_result_month['Сумма себестоимости'] -
         final_result_month['ДРР']) /
        final_result_month['Сумма отгрузки'] * 100
    ).fillna(0).round(2)
    
    excel_filename_yesterday = "final_result_yesterday_with_calculations.xlsx"
    excel_filename_month = "final_result_month_with_calculations.xlsx"
    
    final_result_yesterday.to_excel(excel_filename_yesterday, index=False)
    final_result_month.to_excel(excel_filename_month, index=False)
    
    print(f"✅ Таблица за вчера с расчетами сохранена в файл: {excel_filename_yesterday}")
    print(f"✅ Таблица с начала месяца с расчетами сохранена в файл: {excel_filename_month}")
    
    # --- Вывод для проверки ---
    print("📊 Итоговая таблица за вчера:")
    print(final_result_yesterday.head(10))
    
    print("\n📊 Итоговая таблица с начала месяца:")
    print(final_result_month.head(10))
    
    """## Финальный этап: расчёты и экспорт
    
    Добавляем итоговые расчёты по рекламной эффективности и сохраняем всё в Excel.
    
    ---
    
    ###  Что считаем:
    
    #### Переименование колонок:
    - `amount` → `Сумма отгрузки`
    - `cost` → `Себестоимость`
    
    ####  Расчёты:
    
    - **ДРР (%)** — доля рекламных расходов от выручки
    - **Маржа с учетом ДРР (%)** — финальная рентабельность
    #### Экспорт:
    Результаты сохраняются в Excel:
    - `final_result_yesterday_with_calculations.xlsx`
    - `final_result_month_with_calculations.xlsx`
    
    ---
    
    ### Содержимое итоговых таблиц:name | sku | count | Сумма отгрузки | Себестоимость | Прибыль | Маржинальность (%) | Доля продаж (%) | ДРР | ДРР (%) | Маржа с учетом ДРР
    
    
    """
    
    cols_to_round = [
        'Сумма отгрузки',
        'Сумма себестоимости',
        'Прибыль',
        'Маржинальность (%)',
        'Доля продаж (%)',
        'ДРР (%)',
        'Маржинальность с учетом ДРР'
    ]
    final_result_month[cols_to_round] = final_result_month[cols_to_round].astype(float).round(2)
    final_result_yesterday[cols_to_round] = final_result_yesterday[cols_to_round].astype(float).round(2)
    
    final_result_month.head(100)
    
    final_result_yesterday.head(50)
    
    items_yesterday.head()
    
    #file_name = 'final_result_yesterday.xlsx'
    #final_result_yesterday.to_excel(file_name, index=False)
    #files.download(file_name)
    
    nachislen_yesterday.head(20)
    
    nachislen_month.head(25)
    
    #nachislen_yesterday.to_excel("nachislen_yesterday.xlsx", index=False)
    #nachislen_month.to_excel("nachislen_month.xlsx", index=False)
    
    def prepare_pie_data(df):
        df_filtered = df[(df['operation_type_name'] != 'Общая сумма') & (df['amount'] < 0)].copy()
        df_filtered['amount'] = df_filtered['amount'].abs()
        return df_filtered
    
    pie_yesterday = prepare_pie_data(nachislen_yesterday)
    pie_month = prepare_pie_data(nachislen_month)
    
    def plot_pie(df, title):
        df_sorted = df.sort_values(by='amount', ascending=False)
        labels = df_sorted['operation_type_name']
        values = df_sorted['amount']
    
    
        if len(df_sorted) > 10:
            labels = list(labels[:9]) + ['Прочее']
            values = list(values[:9]) + [sum(values[9:])]
    
    
        colors = plt.get_cmap('Set3').colors
    
        plt.figure(figsize=(12, 12))
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
        plt.title(title)
        plt.axis('equal')
        plt.tight_layout()
        plt.show()
    
    plot_pie(pie_yesterday, "Распределение затрат за вчера")
    plot_pie(pie_month,  "Распределение затрат с начала месяца")
    
    price.columns
    
    final_result_yesterday = final_result_yesterday.merge(price[['Ozon SKU ID', 'Тип']],
                                                          left_on='sku', right_on='Ozon SKU ID',
                                                          how='left')
    
    final_result_month = final_result_month.merge(price[['Ozon SKU ID', 'Тип']],
                                                  left_on='sku', right_on='Ozon SKU ID',
                                                  how='left')
    
    
    def aggregate_by_type(df, period_name):
        if 'Тип' not in df.columns:
            print(f"⚠ Не найдена колонка 'Тип' в данных за {period_name}.")
            return pd.DataFrame()
    
        grouped = df.groupby('Тип', as_index=False).agg({
            'Сумма отгрузки': 'sum',
            'Сумма себестоимости': 'sum',
            'ДРР': 'sum'
        })
    
        grouped['Маржинальность (%)'] = (
            (grouped['Сумма отгрузки'] - grouped['Сумма себестоимости']) / grouped['Сумма отгрузки'] * 100
        ).round(2)
    
        grouped['ММаржинальность с учетом ДРР (%)'] = (
            (grouped['Сумма отгрузки'] - grouped['Сумма себестоимости'] - grouped['ДРР']) / grouped['Сумма отгрузки'] * 100
        ).round(2)
    
        print(f"\n📊 Агрегация по типам ({period_name}):")
        print(grouped)
    
        return grouped
    
    # Вызываем
    grouped_by_type_yesterday = aggregate_by_type(final_result_yesterday, "за вчера")
    grouped_by_type_month = aggregate_by_type(final_result_month, "с начала месяца")
    
    grouped_by_type_yesterday.head()
    
    df = grouped_by_type_yesterday.sort_values(by='Сумма отгрузки', ascending=True)
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(df['Тип'], df['Сумма отгрузки'], color='cornflowerblue')
    
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 1000, bar.get_y() + bar.get_height()/2,
                 f'{width:,.0f}', va='center')
    
    plt.xlabel('Сумма отгрузки (₽)')
    plt.title('Сумма отгрузки по категориям (за вчера)')
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()
    
    df = grouped_by_type_yesterday.sort_values(by='Сумма отгрузки', ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.barh(df['Тип'], df['Сумма отгрузки'], color='cornflowerblue', label='Сумма отгрузки')
    
    df['Прибыль'] = df['Сумма отгрузки'] - df['Сумма себестоимости'] - df['ДРР']
    ax.barh(df['Тип'], df['Прибыль'], color='red', label='Прибыль')
    
    for i, (y, profit) in enumerate(zip(df['Тип'], df['Прибыль'])):
        ax.text(profit + 1000, i, f'{profit:,.0f}', va='center', fontsize=8)
    
    ax.set_xlabel('₽')
    ax.set_title('Сравнение суммы отгрузки и прибыли по категориям (за вчера)')
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    ax.legend()
    plt.tight_layout()
    plt.show()
    
    df = grouped_by_type_yesterday.copy()
    df['Прибыль'] = df['Сумма отгрузки'] - df['Сумма себестоимости'] - df['ДРР']
    
    x = np.arange(len(df['Тип']))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, df['Сумма отгрузки'], width, label='Сумма отгрузки', color='#4C72B0')
    bars2 = ax.bar(x + width/2, df['Прибыль'], width, label='Прибыль', color='#DD8452')
    
    ax.set_ylabel('₽')
    ax.set_title('Отгрузка и прибыль по категориям (за вчера)')
    ax.set_xticks(x)
    ax.set_xticklabels(df['Тип'], rotation=45)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    df_sku = final_result_yesterday.sort_values(by='Сумма отгрузки', ascending=False).head(20)
    
    plt.figure(figsize=(15, 6))
    bars = plt.bar(df_sku['name'], df_sku['Сумма отгрузки'], color='skyblue')
    
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2000,
                 f'{bar.get_height():,.0f} ₽', ha='center', va='bottom', fontsize=8)
    
    plt.xticks(rotation=75, ha='right')
    plt.ylabel('₽')
    plt.title('Топ-15 товаров по сумме отгрузки (за вчера)')
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.show()

    # Фрагмент для вставки в calculate_all — блок графиков

# График 1: Сумма отгрузки по категориям (за вчера)
    df1 = grouped_by_type_yesterday.sort_values(by='Сумма отгрузки', ascending=True)
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    bars = ax1.barh(df1['Тип'], df1['Сумма отгрузки'], color='cornflowerblue')
    for bar in bars:
        width = bar.get_width()
        ax1.text(width + 1000, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', va='center')
    ax1.set_xlabel('Сумма отгрузки (₽)')
    ax1.set_title('Сумма отгрузки по категориям (за вчера)')
    ax1.grid(axis='x', linestyle='--', alpha=0.5)
    plt.subplots_adjust(left=0.3, bottom=0.2)
    plt.tight_layout()

# График 2: Сравнение суммы отгрузки и прибыли (за вчера)
    df2 = df1.copy()
    df2['Прибыль'] = df2['Сумма отгрузки'] - df2['Сумма себестоимости'] - df2['ДРР']
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ax2.barh(df2['Тип'], df2['Сумма отгрузки'], color='cornflowerblue', label='Сумма отгрузки')
    ax2.barh(df2['Тип'], df2['Прибыль'], color='red', label='Прибыль')
    for i, (y, profit) in enumerate(zip(df2['Тип'], df2['Прибыль'])):
        ax2.text(profit + 1000, i, f'{profit:,.0f}', va='center', fontsize=8)
    ax2.set_xlabel('₽')
    ax2.set_title('Сравнение отгрузки и прибыли по категориям (за вчера)')
    ax2.grid(axis='x', linestyle='--', alpha=0.5)
    ax2.legend()
    plt.tight_layout()

# График 3: Столбики рядом — отгрузка и прибыль
    x = np.arange(len(df2['Тип']))
    width = 0.35
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    bars1 = ax3.bar(x - width/2, df2['Сумма отгрузки'], width, label='Сумма отгрузки', color='#4C72B0')
    bars2 = ax3.bar(x + width/2, df2['Прибыль'], width, label='Прибыль', color='#DD8452')
    ax3.set_ylabel('₽')
    ax3.set_title('Отгрузка и прибыль по категориям (за вчера)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(df2['Тип'], rotation=45)
    ax3.legend()
    ax3.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()

# График 4: Топ-15 товаров по отгрузке
    df_sku = final_result_yesterday.sort_values(by='Сумма отгрузки', ascending=False).head(15)
    fig4, ax4 = plt.subplots(figsize=(15, 6))
    bars = ax4.bar(df_sku['name'], df_sku['Сумма отгрузки'], color='skyblue')
    for bar in bars:
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2000,
             f'{bar.get_height():,.0f} ₽', ha='center', va='bottom', fontsize=8)
    ax4.set_ylabel('₽')
    ax4.set_title('Топ-15 товаров по сумме отгрузки (за вчера)')
    ax4.set_xticklabels(df_sku['name'], rotation=75, ha='right')
    ax4.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()

# Добавляем графики в results

    low_margin_yesterday = final_result_yesterday[final_result_yesterday['Маржинальность (%)'] < 20]
    low_margin_month = final_result_month[final_result_month['Маржинальность (%)'] < 20]
    high_drr_yesterday = final_result_yesterday[
        (final_result_yesterday['Маржинальность (%)'] >= 20) &
        (final_result_yesterday['ДРР (%)'] > 15)
    ]
    high_drr_month = final_result_month[
        (final_result_month['Маржинальность (%)'] >= 20) &
        (final_result_month['ДРР (%)'] > 15)
    ]
    category_profit_yesterday = final_result_yesterday.groupby('Тип', as_index=False).agg({
        'Сумма отгрузки': 'sum',
        'Сумма себестоимости': 'sum',
        'ДРР': 'sum'
    })
    category_profit_yesterday['Маржинальность (%)'] = (
        (category_profit_yesterday['Сумма отгрузки'] - category_profit_yesterday['Сумма себестоимости']) /
        category_profit_yesterday['Сумма отгрузки'] * 100
    ).round(2)
    category_profit_yesterday['Маржинальность с учетом ДРР (%)'] = (
        (category_profit_yesterday['Сумма отгрузки'] - category_profit_yesterday['Сумма себестоимости'] - category_profit_yesterday['ДРР']) /
        category_profit_yesterday['Сумма отгрузки'] * 100
    ).round(2)
    top_categories_yesterday = category_profit_yesterday.sort_values(by='Сумма отгрузки', ascending=False).head(5)
    category_profit_month = final_result_month.groupby('Тип', as_index=False).agg({
        'Сумма отгрузки': 'sum',
        'Сумма себестоимости': 'sum',
        'ДРР': 'sum'
    })
    category_profit_month['Маржинальность (%)'] = (
        (category_profit_month['Сумма отгрузки'] - category_profit_month['Сумма себестоимости']) /
        category_profit_month['Сумма отгрузки'] * 100
    ).round(2)
    category_profit_month['Маржинальность с учетом ДРР (%)'] = (
        (category_profit_month['Сумма отгрузки'] - category_profit_month['Сумма себестоимости'] - category_profit_month['ДРР']) /
        category_profit_month['Сумма отгрузки'] * 100
    ).round(2)
    top_categories_month = category_profit_month.sort_values(by='Сумма отгрузки', ascending=False).head(5)
    
    
    buffer_account = io.BytesIO()
    buffer_sku = io.BytesIO()

    with pd.ExcelWriter(buffer_account, engine="xlsxwriter") as writer:
        nachislen_yesterday.to_excel(writer, sheet_name="Начисления вчера", index=False)
        nachislen_month.to_excel(writer, sheet_name="Начисления месяц", index=False)
        pd.DataFrame([{
            "Себестоимость": total_sebestoimost_yesterday,
            "Отгрузка": total_otgruzka_yesterday,
            "Доля себестоимости": sebestoimost_ratio_yesterday,
            "Маржинальность": marzha_percentage_yesterday
        }]).to_excel(writer, sheet_name="Итоги вчера", index=False)
        pd.DataFrame([{
            "Себестоимость": total_sebestoimost_month,
            "Отгрузка": total_otgruzka_month,
            "Доля себестоимости": sebestoimost_ratio_month,
            "Маржинальность": marzha_percentage_month
        }]).to_excel(writer, sheet_name="Итоги месяц", index=False)

    with pd.ExcelWriter(buffer_sku, engine="xlsxwriter") as writer:
        final_result_yesterday.to_excel(writer, sheet_name="SKU вчера", index=False)
        final_result_month.to_excel(writer, sheet_name="SKU месяц", index=False)

    buffer_insights = io.BytesIO()

    with pd.ExcelWriter(buffer_insights, engine="xlsxwriter") as writer:
        low_margin_yesterday.to_excel(writer, sheet_name="Маржинальность <20% вчера", index=False)
        high_drr_yesterday.to_excel(writer, sheet_name="Высокая ДРР вчера", index=False)
        top_categories_yesterday.to_excel(writer, sheet_name="Категории вчера", index=False)

        low_margin_month.to_excel(writer, sheet_name="Маржинальность <20% месяц", index=False)
        high_drr_month.to_excel(writer, sheet_name="Высокая ДРР месяц", index=False)
        top_categories_month.to_excel(writer, sheet_name="Категории месяц", index=False)

    
    return {
    "💰 Начисления за вчера": nachislen_yesterday,
    "💰 Начисления с начала месяца": nachislen_month,
    "📊 Итоги (вчера)": {
        "Себестоимость": total_sebestoimost_yesterday,
        "Отгрузка": total_otgruzka_yesterday,
        "Доля себестоимости": sebestoimost_ratio_yesterday,
        "Маржинальность": marzha_percentage_yesterday
    },
    "📊 Итоги (месяц)": {
        "Себестоимость": total_sebestoimost_month,
        "Отгрузка": total_otgruzka_month,
        "Доля себестоимости": sebestoimost_ratio_month,
        "Маржинальность": marzha_percentage_month
    },
    "📦 Финальная таблица за вчера": final_result_yesterday,
    "📦 Финальная таблица за месяц": final_result_month,

    "📈 График: Отгрузка по категориям (вчера)": fig1,
    "📈 График: Сравнение отгрузки и прибыли": fig2,
    "📈 График: Отгрузка vs Прибыль (столбики)": fig3,
    "📈 График: Топ-15 SKU по отгрузке": fig4,
    "buffer_account": buffer_account,
    "buffer_sku": buffer_sku,
    "buffer_insights": buffer_insights
}
