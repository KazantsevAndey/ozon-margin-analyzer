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


with st.sidebar:
    st.markdown("🔐 **API-ключи Ozon**")
    api_key = st.text_input("API ключ Ozon", type="password")
    perf_key = st.text_input("API ключ Performance API", type="password")
    client_id = st.text_input("Client ID (Seller ID)", type="default")
    perf_client_id = st.text_input("Performance Client ID")
    st.markdown("Ключи сохраняются только в сессии и не передаются третьим лицам.")


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



if st.button("📊 Рассчитать (этап 2)"):
    if not api_key or not perf_key or not client_id or price is None:
        st.error("Пожалуйста, заполните все поля и загрузите прайс.")
    else:
        with st.spinner("Выполняется расчёт..."):
            try:
                results = calculate_all(api_key, perf_key, perf_client_id, price, client_id)
                st.session_state.results = results
              #  st.write("🔍 Содержимое results:")
              #  for key in results:
              #      st.write("-", key)
                st.session_state.show_results = True
                st.success("Расчёт выполнен успешно!")
            except Exception as e:
                st.session_state.show_results = False
                st.error(f"Произошла ошибка: {e}")


if st.session_state.get("show_results") and "results" in st.session_state:
    st.markdown("### ⬇️ Скачайте готовые Excel-отчёты")
    st.download_button("📥 Отчёт по аккаунту", data=st.session_state.results["buffer_account"].getvalue(), file_name="account_summary.xlsx")
    st.download_button("📥 Отчёт по SKU (юнит-экономика)", data=st.session_state.results["buffer_sku"].getvalue(), file_name="sku_unit_economics.xlsx")

    for name, value in st.session_state.results.items():
        if name.startswith("buffer"):  # не отображаем буферы
            continue

        st.subheader(name)

        if isinstance(value, plt.Figure):
            st.pyplot(value)
        elif isinstance(value, pd.DataFrame):
            st.dataframe(value, use_container_width=True)
        elif isinstance(value, dict):
            for k, v in value.items():
                st.markdown(f"**{k}**: {v}")
        else:
            st.write(value)



if st.button("Анализ продаж AI"):
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
                •	Маржинальность за вчера: (значение)%.
                •	Маржинальность за месяц: (значение)%.
                Динамика: укажи явно, маржа растёт или падает (если маржа за вчера выше месячной — значит растёт, если ниже — значит падает). Растет прибыль или падает.
                
                2. Проблемные товары с низкой маржой (менее 20%):
                Отдельно напиши краткий список таких товаров каждый товар с новой строчки. 
                
                •	Название SKU — маржинальность за вчера (значение)%, маржинвльность за месяц (значение)%
                
                В конце напиши: «Обратите внимание на эти товары, маржа по ним ниже 20%.» цены на эти товары стоит внимательно пересмотреть. Чуток порассуждай как профи.
                
                3. Товары с высоким расходом на рекламу (высокая ДРР)
                
                Отдельно напиши краткий список таких товаров, каждый товар в с новой строчки. 
                
                •	Название SKU — ДРР за вчера (значение)%, и за месяц (значение)%.
                В конце обязательно напиши одним понятное предложение а после немного порассуждай про рекламные инструменты: «Проверьте настройки рекламных кампаний этих товаров, реклама съедает большую часть прибыли.» Порассуждай чуть чуть как это делают специалисты.
                
                4. Самые прибыльные категории:
                
                Отдельно топ-3 категории за вчера и топ-3 категории за месяц. 
                
                •	Категория — прибыль (значение в рублях).
                Закончить простым предложением: «Эти категории приносят наибольшую прибыль.»

                В конце немного оцени что все нормально в целом только посмотрите расходы на рекламу.
                
                
                Правила подготовки отчёта:
                
                Пиши понятно и кратко. Не используй нумерацию. Используй заголовки и эмодзи. Внимательно разделяй слова и предложения пробелами и новыми строками.
                Чётко разделяй абзацы и списки для удобства чтения.
                Никаких технических названий таблиц, только понятные и простые фразы для селлера.
                Всегда проверяй логику динамики маржи перед выводом.
                Нужно чтобы твой отчет был понятным. Поэтому каждый Товар в новой строчке, красиво, понятно. Добавляй комментарии специалиста в конце каждого блока. В конце
                чуть чуть порассуждай о том, что нужно всегда держать руку на пульсе и что даже у опытных продавцов бывают недочеты просто надо сразу исправлять и так далее.
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
