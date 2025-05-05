import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Ozon Margin Analyzer", layout="wide")
st.title("🛒 Ozon Margin Analyzer")

# --- SIDEBAR: API Ключи ---
with st.sidebar:
    st.header("🔐 API-ключи Ozon")
    ozon_api_key = st.text_input("API ключ Ozon", type="password")
    ozon_perf_key = st.text_input("API ключ Performance API", type="password")
    st.markdown("---")
    st.caption("Эти ключи пока не используются — подключим их на 2 этапе.")

# --- Ввод данных ---
st.subheader("📦 Загрузите прайс-лист или введите вручную")
upload_method = st.radio("Выберите способ:", ["Загрузить CSV", "Заполнить вручную"])

df = None

if upload_method == "Загрузить CSV":
    uploaded_file = st.file_uploader("Загрузите .csv файл с прайс-листом", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.success("Файл успешно загружен.")
        except Exception as e:
            st.error(f"Ошибка при чтении файла: {e}")
else:
    df = st.data_editor(
        pd.DataFrame({
            "Артикул": [],
            "Себестоимость": [],
            "Желаемая цена": []
        }),
        num_rows="dynamic",
        use_container_width=True
    )

# --- Кнопка запуска (будущая логика) ---
if st.button("📊 Рассчитать (этап 2)") and df is not None and not df.empty:
    st.info("Здесь появятся таблицы с расчётами. Этап 2 — подключение к API.")
    st.dataframe(df, use_container_width=True)
else:
    st.caption("После загрузки прайса нажмите кнопку для расчёта.")
