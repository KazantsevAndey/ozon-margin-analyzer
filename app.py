import streamlit as st
import pandas as pd
from ozon_core_cleaned_fixed import calculate_all
import matplotlib.pyplot as plt
from openai import OpenAI
import streamlit as st
import openai

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Ozon Margin Analyzer", layout="wide")
st.title("🧾 Ozon Margin Analyzer")
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

                # Отдельно рендерим таблицы
                for name, value in results.items():
                    st.subheader(f"{name}")
                    if isinstance(value, plt.Figure):
                        st.pyplot(value)
                    else:
                        st.dataframe(value, use_container_width=True)

            except Exception as e:
                st.error(f"Произошла ошибка: {e}")

if st.button("🧠 Анализ показателей с помощью ИИ"):
    with st.spinner("Анализируем отчёты..."):
        try:
            full_report = ""
            for name, table in st.session_state.results.items():
                if isinstance(table, pd.DataFrame):
                    full_report += f"\n\n{name}:\n{table.head(20).to_string(index=False)}"
                elif isinstance(table, dict):
                    for k, v in table.items():
                        full_report += f"\n\n{name} – {k}: {v}"
                else:
                    full_report += f"\n\n{name}: {table}"

            prompt = (
    "Ты — AI-аналитик, встроенный в калькулятор маржи для Ozon. Твоя задача — подробно проанализировать предоставленные данные и составить понятный отчёт для менеджера.\n\n"
    "Ты получаешь шесть отчётов:\n"
    "1. Результаты продаж за вчера.\n"
    "2. Экономика по SKU за вчера.\n"
    "3. Общая маржа по аккаунту за вчера.\n"
    "4. Результаты продаж с начала текущего месяца.\n"
    "5. Экономика по SKU с начала текущего месяца.\n"
    "6. Общая маржа по аккаунту с начала текущего месяца.\n\n"
    "Твои действия:\n"
    "1. Проанализируй динамику продаж, сравнив вчерашние данные с месячными трендами. Отметь заметные изменения или аномалии.\n"
    "2. Выдели товары с низкой маржой (ниже среднего уровня), укажи их SKU и маржу, дай краткие рекомендации по улучшению.\n"
    "3. Подсвети крупные затраты, указав категории или конкретные товары, которые больше всего влияют на маржинальность.\n"
    "4. Опиши общий тренд маржи и затрат за текущий месяц, указав, улучшается ситуация или ухудшается.\n"
    "5. Сформулируй выводы и дай конкретные рекомендации для повышения общей маржинальности и эффективности продаж.\n\n"
    "Структурируй ответ следующим образом:\n"
    "Анализ динамики продаж:\n"
    "-\n"
    "Товары с низкой маржой:\n"
    "-\n"
    "Высокие затраты:\n"
    "-\n"
    "Общий тренд за месяц:\n"
    "-\n"
    "Выводы и рекомендации:\n"
    "-\n\n"
    f"{full_report}"
)

            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )

            st.subheader("📋 GPT-анализ отчётов")
            st.write(response.choices[0].message.content)

        except Exception as e:
            st.error(f"Произошла ошибка при анализе: {e}")
