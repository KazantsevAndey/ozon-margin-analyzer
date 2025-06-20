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
st.title("Автоматический анализ рентабельности для селлера Озон")
#results = st.session_state.get("results")
st.subheader("Загрузите прайс-лист и введите ключи(этап 1)")


with st.sidebar:
    st.markdown("🔐 **API-ключи Ozon**")
    api_key = st.text_input("API ключ Ozon", type="password")
    perf_key = st.text_input("API ключ Performance API", type="password")
    client_id = st.text_input("Client ID (Seller ID)", type="default")
    perf_client_id = st.text_input("Performance Client ID")
    st.markdown("Ключи сохраняются только в сессии и не передаются третьим лицам.")

#st.markdown("### 📦 Загрузите прайс-лист")

# 📥 Кнопка: скачать шаблон
template_df = pd.DataFrame(columns=["Ozon SKU ID", "Цена в рублях", "Тип"])
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    template_df.to_excel(writer, index=False, sheet_name="Template")
output.seek(0)

st.download_button(
    label="📥 Скачать шаблон Excel",
    data=output,
    file_name="шаблон_прайс-листа.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# 📤 Загрузка Excel файла
uploaded_file = st.file_uploader("📤 Загрузите .xlsx прайс-лист", type="xlsx")

price = None
if uploaded_file is not None:
    try:
        price = pd.read_excel(uploaded_file)
        st.success("✅ Прайс-лист успешно загружен.")
        st.dataframe(price)
    except Exception as e:
        st.error(f"❌ Ошибка при чтении Excel-файла: {e}")




if st.button("📊 Рассчитать (этап 2)"):
    if price is None:
        price = st.session_state.get("price_from_template")
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



if st.button("Анализ продаж AI(этап 3"):
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
                Структура твоего отчёта должна быть именно такой: Обязательно при обязательно пиши с новой строчки! Рассуждай! Пиши человеческим языком как профи.
                
                1. Общая ситуация по марже:
                /n •	Маржинальность за вчера: (значение)%.
                /n •	Маржинальность за месяц: (значение)%.
                /n Динамика: укажи явно, маржа растёт или падает (если маржа за вчера выше месячной — значит растёт, если ниже — значит падает). Растет прибыль или падает.
                
                2. Проблемные товары с низкой маржой (менее 20%) Смотри столбик Маржинальность в отчетах:
                Отдельно напиши краткий список таких товаров каждый товар с новой строчки в виде таблицы. 
                
                /n •	В виде таблица Название SKU — маржинальность за вчера (значение)% и отдельно с начала месяца
                
                /n В конце напиши: «Обратите внимание на эти товары, маржа по ним ниже 20%.» цены на эти товары стоит внимательно пересмотреть. Чуток порассуждай как профи.
                
                /n 3. Товары доход у которых пости польностью ушел на рекламу (высокая ДРР)
                
                /n Отдельно напиши краткий список таких товаров, каждый товар в с новой строчки.
                
                /n •	Название SKU — смотри колонку ДРР % за вчера, и за месяц. 1 товар - одна строчка!/n
                /n С новой строчки объясни что такое доля рекламных расходов, В конце обязательно напиши одним понятное предложение а после немного порассуждай про рекламные инструменты: «Проверьте настройки рекламных кампаний этих товаров, реклама съедает большую часть прибыли.» Порассуждай чуть чуть как это делают специалисты.
                
                /n 4. Самые прибыльные категории:
                
                Отдельно топ-3 категории за вчера и топ-3 категории за месяц. 
                
                /n •	Категория — прибыль (значение в рублях).
                /n Закончить простым предложением: «Эти категории приносят наибольшую прибыль.»/n

                /n В конце немного оцени что все нормально в целом только посмотрите расходы на рекламу или еще что-то ты же профи. /n
                /n Добавляй комментарии специалиста в конце каждого блока./n В конце
                чуть чуть порассуждай о том, что нужно всегда держать руку на пульсе и что даже у опытных продавцов бывают недочеты просто надо сразу исправлять и так далее.
                
                
                Правила подготовки отчёта:
                
                Пиши понятно и кратко. Не используй нумерацию. Используй заголовки и эмодзи. Внимательно разделяй слова и предложения пробелами и новыми строками.
                Чётко разделяй абзацы и списки для удобства чтения.
                Никаких технических названий таблиц, только понятные и простые фразы для селлера.
                Всегда проверяй логику динамики маржи перед выводом.
                Нужно чтобы твой отчет был понятным. Поэтому каждый Товар в новой строчке, красиво, понятно. И обязательно с пояснениям. 
                     {full_report}"""
                )

                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=2000
                )

                st.subheader("📋 GPT-анализ отчётов")
                st.write(response.choices[0].message.content)

            except Exception as e:
                st.error(f"Ошибка при анализе: {e}")
