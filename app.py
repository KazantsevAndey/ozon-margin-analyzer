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

import io
buffer_account = io.BytesIO()
buffer_sku = io.BytesIO()

with pd.ExcelWriter(buffer_account, engine="xlsxwriter") as writer:
    results["💰 Начисления за вчера"].to_excel(writer, sheet_name="Начисления вчера", index=False)
    results["💰 Начисления с начала месяца"].to_excel(writer, sheet_name="Начисления месяц", index=False)
    pd.DataFrame([results["📊 Итоги (вчера)"]]).to_excel(writer, sheet_name="Итоги вчера", index=False)
    pd.DataFrame([results["📊 Итоги (месяц)"]]).to_excel(writer, sheet_name="Итоги месяц", index=False)

with pd.ExcelWriter(buffer_sku, engine="xlsxwriter") as writer:
    results["📦 Финальная таблица за вчера"].to_excel(writer, sheet_name="SKU вчера", index=False)
    results["📦 Финальная таблица за месяц"].to_excel(writer, sheet_name="SKU месяц", index=False)

# --- Кнопки скачивания ---
st.download_button("⬇️ Скачать отчёт по аккаунту", data=buffer_account.getvalue(), file_name="account_summary.xlsx")
st.download_button("⬇️ Скачать отчёт по юнит-экономике", data=buffer_sku.getvalue(), file_name="sku_unit_economics.xlsx")
# GPT-анализ отчёта по аккаунту
if st.button("🧠 Анализировать отчёт по аккаунту"):
    with st.spinner("Анализируем отчёт по аккаунту..."):
        try:
            prompt_account = (
                "Ты аналитик. Проанализируй отчёт по аккаунту. Укажи ключевые статьи затрат, тренд по марже, "
                "и дай краткие рекомендации:\n"
                f"Итоги вчера: {results['📊 Итоги (вчера)']}\n"
                f"Итоги месяц: {results['📊 Итоги (месяц)']}\n"
                f"Начисления вчера:\n{nachislen_yesterday.head(10).to_string(index=False)}\n"
                f"Начисления месяц:\n{nachislen_month.head(10).to_string(index=False)}"
            )
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_account}],
                temperature=0.3,
                max_tokens=1000
            )
            st.subheader("📋 Анализ аккаунта")
            st.write(response.choices[0].message.content)

        except Exception as e:
            st.error(f"Ошибка: {e}")

# GPT-анализ SKU
if st.button("🧠 Анализировать юнит-экономику по товарам"):
    with st.spinner("Анализируем юнит-экономику..."):
        try:
            prompt_sku = (
                "Ты специалист по юнит-экономике. Проанализируй прибыльность товаров. "
                "Найди товары с маржой ниже 15%, товары с нормальной маржой, но плохой маржой с учётом ДРР. "
                "Сделай 3–5 рекомендаций:\n"
                f"{results['📦 Финальная таблица за вчера'].head(20).to_string(index=False)}\n\n"
                f"{results['📦 Финальная таблица за месяц'].head(20).to_string(index=False)}"
            )
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_sku}],
                temperature=0.3,
                max_tokens=1000
            )
            st.subheader("📋 Анализ юнит-экономики")
            st.write(response.choices[0].message.content)

        except Exception as e:
            st.error(f"Ошибка: {e}")
#if st.button("🧠 Анализ показателей с помощью ИИ"):
#    with st.spinner("Анализируем отчёты..."):
#        try:
#            full_report = ""
#            for name, table in st.session_state.results.items():
#                if isinstance(table, pd.DataFrame):
#                    full_report += f"\n\n{name}:\n{table.head(20).to_string(index=False)}"
#                elif isinstance(table, dict):
#                    for k, v in table.items():
#                        full_report += f"\n\n{name} – {k}: {v}"
#                else:
#                    full_report += f"\n\n{name}: {table}"

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
#
#            st.subheader("📋 GPT-анализ отчётов")
#            st.write(response.choices[0].message.content)
#
#        except Exception as e:
#            st.error(f"Произошла ошибка при анализе: {e}")
