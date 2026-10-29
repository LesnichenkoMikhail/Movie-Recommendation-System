import pandas as pd
import plotly.express as px
import streamlit as st

import ui

METRIC_LABELS = {"precision": "Precision", "recall": "Recall", "ndcg": "NDCG"}

ui.page_header("Качество моделей",
               "Сравнение алгоритмов на отложенной части оценок: что модель угадала из того, что пользователю понравилось.")

models = ui.fetch("/models") or []
labels = {item["key"]: item["label"] for item in models}
overview = ui.fetch("/analytics/overview") or {}

first, second = st.columns(2)
first.metric("Пользователей", overview.get("users", 0))
second.metric("Оценок в базе", overview.get("ratings", 0))

st.subheader("Параметры эксперимента")
with st.form("evaluation_form"):
    one, two, three, four = st.columns(4)
    k = one.slider("Длина списка K", 3, 30, 10)
    min_ratings = two.slider("Минимум оценок у пользователя", 4, 40, 8)
    test_ratio = three.slider("Доля отложенных оценок", 0.1, 0.5, 0.3, 0.05)
    max_users = four.slider("Максимум пользователей", 5, 100, 30)
    run = st.form_submit_button("Запустить оценку", type="primary")

if run:
    with st.spinner("Модели оцениваются на отложенной выборке"):
        result = ui.api("POST", "/evaluation/run", timeout=900, json={
            "k": k, "min_ratings": min_ratings, "test_ratio": test_ratio, "max_users": max_users,
        })
    if result is not None:
        st.session_state["evaluation_result"] = result

result = st.session_state.get("evaluation_result")
if result:
    if not result["models"]:
        ui.empty_state(
            "Недостаточно данных для оценки",
            f"Подходящих пользователей: {result['users_eligible']}, с отложенными понравившимися фильмами: "
            f"{result['users_evaluated']}. Добавьте оценки или создайте демонстрационных пользователей "
            "командой python -m etl.seed_demo.",
        )
    else:
        st.subheader(f"Результат: {result['users_evaluated']} пользователей, K = {result['k']}")
        frame = pd.DataFrame(result["models"])
        frame["Модель"] = frame["model"].map(labels)
        long = frame.melt(id_vars="Модель", value_vars=list(METRIC_LABELS), var_name="Метрика", value_name="Значение")
        long["Метрика"] = long["Метрика"].map(METRIC_LABELS)
        figure = px.bar(long, x="Метрика", y="Значение", color="Модель", barmode="group")
        ui.show_figure(figure, height=400)
        table = frame[["Модель", "precision", "recall", "ndcg"]].rename(columns=METRIC_LABELS)
        st.dataframe(table.round(4), use_container_width=True, hide_index=True)
else:
    ui.empty_state("Оценка ещё не запускалась",
                   "Задайте параметры и нажмите «Запустить оценку». Нужны пользователи с оценками фильмов.")

st.subheader("История запусков")
runs = ui.api("GET", "/evaluation/runs", params={"limit": 80})
if runs:
    history = pd.DataFrame(runs)
    history["Модель"] = history["model"].map(labels)
    history["Дата"] = pd.to_datetime(history["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    trend = px.line(history.sort_values("id"), x="Дата", y="ndcg", color="Модель", markers=True)
    trend.update_yaxes(title="NDCG")
    ui.show_figure(trend, height=320)
    st.dataframe(
        history[["Дата", "Модель", "k", "users", "precision", "recall", "ndcg"]].rename(
            columns={"k": "K", "users": "Пользователей", "precision": "Precision", "recall": "Recall",
                     "ndcg": "NDCG"}).round(4),
        use_container_width=True, hide_index=True)
else:
    st.markdown('<div class="section-note">Сохранённых запусков пока нет.</div>', unsafe_allow_html=True)

with st.expander("Как читать метрики"):
    st.write("Для каждого пользователя часть его оценок скрывается. Модель строит список из K фильмов по оставшимся "
             "данным, а затем проверяется, сколько из скрытых фильмов с оценкой от 4 она угадала.")
    st.write("Precision показывает долю удачных фильмов в списке, Recall показывает, какую долю понравившихся "
             "фильмов удалось найти, NDCG дополнительно учитывает позицию удачных фильмов: чем выше, тем лучше.")
