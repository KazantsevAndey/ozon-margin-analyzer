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
                #st.markdown("### ⬇️ Скачайте готовые Excel-отчёты")
                #st.download_button("📥 Отчёт по аккаунту", data=results["buffer_account"].getvalue(), file_name="account_summary.xlsx")
                #st.download_button("📥 Отчёт по SKU (юнит-экономика)", data=results["buffer_sku"].getvalue(), file_name="sku_unit_economics.xlsx")
                #st.session_state.results = results

                # Отдельно рендерим таблицы
                for name, value in results.items():
                    st.subheader(f"{name}")
                    if isinstance(value, plt.Figure):
                        st.pyplot(value)
                    else:
                        st.dataframe(value, use_container_width=True)

            except Exception as e:
                st.error(f"Произошла ошибка: {e}")

if st.button("🧠 GPT-анализ отчётов"):
    if "results" not in st.session_state or "buffer_insights" not in st.session_state.results:
        st.error("Сначала рассчитай отчёты.")
    else:
        with st.spinner("Анализируем отчёты..."):
            try:
                insights_df = pd.read_excel(
                    df_account = pd.read_excel(results["buffer_account"], sheet_name=None)
                    df_insights = pd.read_excel(results["buffer_insights"], sheet_name=None)
                    st.session_state.results["buffer_insights"], sheet_name=None
                )

                # Склеиваем всё в одну строку
                full_report = ""
                for name, table in insights_df.items():
                    full_report += f"\n\n{name}:\n{table.to_string(index=False)}"

                prompt = (
                    "Ты аналитик маркетплейса. Проанализируй все эти таблицы:\n"
                    "Найди проблемные товары, убыточные категории, плохие рекламные показатели. Тебе нужно сравнить маржу по аккаунту с начала месяца и в за вчера. Если за вчера больше скажи "маржа растет" Тебе нужно сравнить маржу уходит ли товар из проблемных и низкомаржинальных. Потом дать совет проверить товары с низкой маржой перечислив их\n"
                    "Сделай 5–7 рекомендаций по улучшению продаж и маржи:\n"
                    f"{full_report}"
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
