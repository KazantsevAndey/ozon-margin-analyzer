import streamlit as st
import pandas as pd
from ozon_core_cleaned_fixed import calculate_all
import matplotlib.pyplot as plt

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
                st.success("Расчёт выполнен успешно!")

                # Отдельно рендерим таблицы
                for name, table in results.items():
                    if not isinstance(table, plt.Figure):
                        st.subheader(f"📋 {name}")
                        st.dataframe(table, use_container_width=True)

# Отдельно рендерим графики
                if "📊 График: Отгрузка по категориям (вчера)" in results:
                    st.subheader("📊 Отгрузка по категориям (вчера)")
                    st.pyplot(results["📊 График: Отгрузка по категориям (вчера)"])

                if "📊 График: Сравнение отгрузки и прибыли" in results:
                    st.subheader("📊 Сравнение отгрузки и прибыли")
                    st.pyplot(results["📊 График: Сравнение отгрузки и прибыли"])

                if "📊 График: Отгрузка vs Прибыль (столбики)" in results:
                    st.subheader("📊 Отгрузка vs Прибыль (столбики)")
                    st.pyplot(results["📊 График: Отгрузка vs Прибыль (столбики)"])

                if "📊 График: Top-15 SKU по отгрузке" in results:
                    st.subheader("📊 Top-15 SKU по отгрузке")
                    st.pyplot(results["📊 График: Top-15 SKU по отгрузке"])

            except Exception as e:
                st.error(f"Произошла ошибка: {e}")
