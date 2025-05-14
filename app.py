import streamlit as st
import pandas as pd
from ozon_core_cleaned_fixed import calculate_all
import matplotlib.pyplot as plt
from openai import OpenAI
import streamlit as st
import openai
import io

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Ozon Margin Analyzer", layout="wide")
st.title("🧾 Ozon Margin Analyzer")
#results = st.session_state.get("results")
st.subheader("🚀 Загрузите прайс-лист и введите ключи")

# Ввод ключей
with st.sidebar:
    st.markdown("🔐 **API-ключи Ozon**")
    api_key = st.text_input("API ключ Ozon", type="password")
    perf_key = st.text_input("API ключ Performance API", type="password")
    client_id = st.text_input("Client ID (Seller ID)", type="default")
    perf_client_id = st.text_input("Performance Client ID")
    st.markdown("Ключи сохраняются только в сессии и не передаются третьим лицам.")

# Выбор способа ввода прайса
st.markdown("### 📦 Загрузите прайс-лист или заполните вручную")
upload_method = st.radio("Выберите способ:", ["Загрузить Excel", "Заполнить вручную"])

price = None

if upload_method == "Загрузить Excel":
    uploaded_file = st.file_uploader("Загрузите .xlsx файл с прайс-листом", type="xlsx")
    if uploaded_file is not None:
        try:
            price = pd.read_excel(uploaded_file)
            st.success("Файл успешно загружен.")
            st.dataframe(price)
        except Exception as e:
            st.error(f"Ошибка при чтении Excel-файла: {e}")
else:
    st.info("⚠️ Ручной ввод пока не реализован. Используйте Excel.")

# Кнопка запуска
if st.button("📊 Рассчитать (этап 2)"):
    if not api_key or not perf_key or not client_id or price is None:
        st.error("Пожалуйста, заполните все поля и загрузите прайс.")
    else:
        with st.spinner("Выполняется расчёт..."):
            try:
                results = calculate_all(api_key, perf_key, perf_client_id, price, client_id)
                st.session_state.results = results
                st.success("Расчёт выполнен успешно!")
                st.markdown("### ⬇️ Скачайте готовые Excel-отчёты")
                st.download_button("📥 Отчёт по аккаунту", data=results["buffer_account"].getvalue(), file_name="account_summary.xlsx")
                st.download_button("📥 Отчёт по SKU (юнит-экономика)", data=results["buffer_sku"].getvalue(), file_name="sku_unit_economics.xlsx")
                st.session_state.results = results

                # Отдельно рендерим таблицы
                for name, value in results.items():
                    st.subheader(f"{name}")
                    if isinstance(value, plt.Figure):
                        st.pyplot(value)
                    else:
                        st.dataframe(value, use_container_width=True)

            except Exception as e:
                st.error(f"Произошла ошибка: {e}")


if st.button("🧠 AI анализ отчётов"):
    if "results" not in st.session_state or "buffer_insights" not in st.session_state.results:
        st.error("Сначала рассчитай отчёты.")
    else:
        with st.spinner("Анализируем отчёты по блокам..."):
            try:
                import pandas as pd
                from openai import OpenAI

                df_account = pd.read_excel(st.session_state.results["buffer_account"], sheet_name=None)
                df_insights = pd.read_excel(st.session_state.results["buffer_insights"], sheet_name=None)

                # Извлекаем нужные блоки
                margin_yesterday = df_account.get("Итоги вчера", pd.DataFrame()).get("Маржа", [None])[0]
                margin_month = df_account.get("Итоги месяц", pd.DataFrame()).get("Маржа", [None])[0]

                low_margin_yesterday = df_insights.get("low_margin_yesterday", pd.DataFrame()).to_string(index=False)
                low_margin_month = df_insights.get("low_margin_month", pd.DataFrame()).to_string(index=False)
                high_drr_yesterday = df_insights.get("high_drr_yesterday", pd.DataFrame()).to_string(index=False)
                high_drr_month = df_insights.get("high_drr_month", pd.DataFrame()).to_string(index=False)
                top_categories_yesterday = df_insights.get("top_categories_yesterday", pd.DataFrame()).to_string(index=False)
                top_categories_month = df_insights.get("top_categories_month", pd.DataFrame()).to_string(index=False)

                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

                prompt_blocks = [
                    {
                        "title": "1. 📊 Общая ситуация по марже",
                        "template": f"""
Ты аналитик маркетплейса Ozon. Посмотри на следующие цифры:
• Маржа за вчера:  {margin_yesterday}%.
• Маржа за месяц: {margin_month}%.

Сравни эти два значения и кратко напиши:
• Какая маржа выше.
• Одним простым предложением сделай вывод: улучшилась или ухудшилась ситуация с маржой.
"""
                    },
                    {
                        "title": "2. ⚠️ Проблемные товары с низкой маржой",
                        "template": f"""
Вот список товаров с маржой менее 20%:

За вчера:
покажи вот эти данные {low_margin_yesterday}

За месяц:
покажи вот эти данные {low_margin_month}

В конце добавь: «Обратите внимание на эти товары — маржа по ним ниже 20%.»
"""
                    },
                    {
                        "title": "3. 💸 Товары с высокой ДРР",
                        "template": f"""
Вот товары, у которых реклама съедает большую часть прибыли:

За вчера:
покажи вот эти данные {high_drr_yesterday}

За месяц:
покажи вот эти данные {high_drr_month}

В конце добавь: «Проверьте рекламные кампании — реклама съедает прибыль.»
"""
                    },
                    {
                        "title": "4. 💰 Категории-лидеры по прибыли",
                        "template": f"""
Вот топ-3 категории по прибыли:

За вчера:
{top_categories_yesterday}

За месяц:
{top_categories_month}

В конце добавь: «Эти категории приносят наибольшую прибыль.»
"""
                    }
                ]

                for block in prompt_blocks:
                    with st.spinner(block["title"]):
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": block["template"]}],
                            temperature=0.4,
                            max_tokens=1000
                        )
                        st.subheader(block["title"])
                        st.write(response.choices[0].message.content)

            except Exception as e:
                st.error(f"Ошибка при анализе: {e}")

if st.button("🧠 GPT-3 анализ отчётов"):
    if "results" not in st.session_state or "buffer_insights" not in st.session_state.results:
        st.error("Сначала рассчитай отчёты.")
    else:
        with st.spinner("Анализируем отчёты..."):
            try:
                # Читаем оба Excel-файла из буферов
                df_account = pd.read_excel(st.session_state.results["buffer_account"], sheet_name=None)
                df_insights = pd.read_excel(st.session_state.results["buffer_insights"], sheet_name=None)

                # Объединяем всё в одну строку
                full_report = ""
                for name, table in {**df_account, **df_insights}.items():
                    full_report += f"\n\n{name}:\n{table.to_string(index=False)}"

                # Сам промт
                prompt = ( f"""Ты — аналитик маркетплейса Ozon. На основе переданных данных напиши очень чёткий, структурированный и понятный отчёт для селлера. Говори кратко, точно и обязательно делай выводы по ситуации.
                Структура твоего отчёта должна быть именно такой:
                
                1. Общая ситуация по марже:
                •	Маржа за вчера: (значение)%.
                •	Маржа за месяц: (значение)%.
                •	Динамика: укажи явно, маржа растёт или падает (если маржа за вчера выше месячной — значит растёт, если ниже — значит падает). Одно предложение.
                
                2. Проблемные товары с низкой маржой (менее 20%):
                Отдельно напиши краткий список таких товаров в виде таблички. 
                
                •	Название SKU — маржа за вчера (значение)%, за месяц (значение)%
                
                В конце одним простым человеческим предложением напиши: «Обратите внимание на эти товары, маржа по ним ниже 20%.»
                
                3. Товары с высоким расходом на рекламу (высокая ДРР)
                
                Отдельно напиши краткий список таких товаров, каждый товар в с новой строчки. 
                
                •	Название SKU — ДРР за вчера (значение)%, за месяц (значение)%.
                В конце обязательно напиши одним понятным предложением: «Проверьте настройки рекламных кампаний этих товаров, реклама съедает большую часть прибыли.»
                
                4. Самые прибыльные категории:
                
                Отдельно топ-3 категории за вчера и топ-3 категории за месяц. 
                
                •	Категория — прибыль (значение в рублях).
                Закончить простым предложением: «Эти категории приносят наибольшую прибыль.»
                Правила подготовки отчёта:
                
                •	Пиши понятно и кратко.
                •	Чётко разделяй абзацы и списки для удобства чтения.
                •	Никаких технических названий таблиц, только понятные и простые фразы для селлера.
                •	Всегда проверяй логику динамики маржи перед выводом.
                Нужно чтобы твой отчет был понятным. Поэтому каждый Товар в новой строчке, красиво, понятно. Добавляй комментарии специалиста в конце каждого блока. 
                     {full_report}"""
                )

                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=2000
                )

                st.subheader("📋 GPT-анализ отчётов")
                st.write(response.choices[0].message.content)

            except Exception as e:
                st.error(f"Ошибка при анализе: {e}")
    #Кнопки скачивания Excel-отчётов
#if st.button("🧠 GPT-анализ отчётов"):
#    if "results" not in st.session_state:
#        st.error("Сначала рассчитай отчёты.")
#    else:
#        with st.spinner("Анализируем отчёты..."):
#            try:
#                results = st.session_state.results
#                df_account = pd.read_excel(results["buffer_account"])
#                df_sku = pd.read_excel(results["buffer_sku"])#

#                prompt = (
#                   "Ты аналитик маркетплейса. Проанализируй следующие Excel-отчёты. "
#                    "Выведи ключевые выводы по марже, затратам и товарам с проблемной экономикой.\n\n"
#                    f"Отчёт по аккаунту (первые 20 строк):\n{df_account.head(20).to_string(index=False)}\n\n"
#                    f"Отчёт по SKU (первые 20 строк):\n{df_sku.head(20).to_string(index=False)}"
#                )   

 #               client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
 #               response = client.chat.completions.create(
 #                   model="gpt-4",
 #                   messages=[{"role": "user", "content": prompt}],
 #                   temperature=0.3,
 #                   max_tokens=1000
 #               )

#                st.subheader("📋 GPT-анализ отчётов")
#                st.write(response.choices[0].message.content)

#            except Exception as e:
#                st.error(f"Ошибка при анализе: {e}")

# if st.button("🧠 Анализ показателей с помощью ИИ"): 
   # with st.spinner("Анализируем отчёты..."):
  #      try:
   #         full_report = "" 
   #         for name, table in st.session_state.results.items():
   #             if isinstance(table, pd.DataFrame):
   #                 full_report += f"\n\n{name}:\n{table.head(20).to_string(index=False)}"
   #             elif isinstance(table, dict):
   #                 for k, v in table.items():
   #                     full_report += f"\n\n{name} – {k}: {v}"
   #             else:
   #                 full_report += f"\n\n{name}: {table}"
#
#            prompt = (
#    "Ты аналитик маркетплейса. Проанализируй следующие отчёты о продажах. "
#    "Сделай анализ по следующей логике:\n"
#    "1. Сравни общую маржу за вчера и за месяц. Сделай вывод: растёт, падает или стабильна.\n"
#    "2. Определи, на что идут основные затраты. Укажи конкретные статьи расходов, где траты особенно велики.\n"
#    "3. Найди товары, у которых маржа за месяц или вчера ниже 15%. Укажи их SKU и краткий комментарий.\n"
#    "4. Найди товары, у которых высокая базовая маржа, но после вычета маркетинговых затрат прибыль минимальна или отрицательна.\n"
#    "5. В завершение — сделай краткий итог: состояние маржи, на какие товары и статьи затрат стоит обратить внимание.\n"
#    "Структурируй ответ по пунктам, с подзаголовками и списками.\n\n"
#    f"{full_report}"
#)
#
#            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
#            response = client.chat.completions.create(
#                model="gpt-4",
#                messages=[{"role": "user", "content": prompt}],
#                temperature=0.3,
#                max_tokens=1000
#            )

#            st.subheader("📋 GPT-анализ отчётов")
#            st.write(response.choices[0].message.content)

#        except Exception as e:
#            st.error(f"Произошла ошибка при анализе: {e}")
