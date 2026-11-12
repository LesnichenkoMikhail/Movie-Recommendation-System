import pandas as pd
import plotly.express as px
import streamlit as st

import ui

METRIC_LABELS = {
    "precision": "Precision",
    "recall": "Recall",
    "ndcg": "NDCG",
    "hit_rate": "Hit Rate",
    "map": "MAP",
    "mrr": "MRR",
}
BASELINE_KEY = "random"
BASELINE_LABEL = "Случайный список (базовая линия)"


def build_frame(result, labels):
    frame = pd.DataFrame(result["models"])
    frame["Модель"] = frame["model"].map(labels).fillna(frame["model"])
    for key in METRIC_LABELS:
        frame[f"{key}_ci"] = frame["ci"].map(lambda ci, key=key: ci.get(key, 0.0))
    return frame


def verdict(frame):
    real = frame[frame["model"] != BASELINE_KEY]
    if real.empty:
        return None
    best = real.sort_values("ndcg", ascending=False).iloc[0]
    baseline = frame[frame["model"] == BASELINE_KEY]
    text = f"Лучшая модель по NDCG: **{best['Модель']}** ({best['ndcg']:.3f})."
    if not baseline.empty:
        base = baseline.iloc[0]
        if best["ndcg"] - best["ndcg_ci"] > base["ndcg"] + base["ndcg_ci"]:
            text += " Она надёжно лучше случайного списка: доверительные интервалы не пересекаются."
        else:
            text += (" Отрыв от случайного списка пока в пределах погрешности. "
                     "Увеличьте число пользователей или оценок, чтобы вывод был надёжнее.")
    return text


ui.page_header("Качество моделей",
               "Сравнение алгоритмов на отложенной части оценок: что модель угадала из того, что пользователю понравилось.")

models = ui.fetch("/models") or []
labels = {item["key"]: item["label"] for item in models}
labels.setdefault(BASELINE_KEY, BASELINE_LABEL)
overview = ui.fetch("/analytics/overview") or {}

first, second = st.columns(2)
first.metric("Пользователей", overview.get("users", 0))
second.metric("Оценок в базе", overview.get("ratings", 0))

st.subheader("Параметры эксперимента")
with st.form("evaluation_form"):
    one, two, three = st.columns(3)
    k = one.slider("Длина списка K", 3, 30, 10)
    min_ratings = two.slider("Минимум оценок у пользователя", 4, 40, 8)
    test_ratio = three.slider("Доля отложенных оценок", 0.1, 0.5, 0.3, 0.05)
    four, five = st.columns(2)
    max_users = four.slider("Максимум пользователей", 5, 1000, 100)
    negatives = five.slider(
        "Случайных фильмов-негативов", 0, 500, 100, 10,
        help="Модель ранжирует отложенные фильмы вместе с этим числом случайных фильмов, которых пользователь "
             "не оценивал. 0 означает ранжирование всего каталога: значения метрик будут очень низкими.")
    run = st.form_submit_button("Запустить оценку", type="primary")

if run:
    with st.spinner("Модели оцениваются на отложенной выборке"):
        result = ui.api("POST", "/evaluation/run", timeout=900, json={
            "k": k, "min_ratings": min_ratings, "test_ratio": test_ratio, "max_users": max_users,
            "negatives": negatives,
        })
    if result is not None:
        st.session_state["evaluation_result"] = result

result = st.session_state.get("evaluation_result")
if result:
    if not result["models"]:
        ui.empty_state(
            "Недостаточно данных для оценки",
            f"Пользователей с нужным числом оценок: {result['users_eligible']}, "
            f"оценено: {result['users_evaluated']}. Уменьшите минимум оценок или создайте демонстрационных "
            "пользователей командой python -m etl.seed_demo --users 300 --ratings 40.",
        )
    else:
        protocol = (f"{result['negatives']} случайных негативов на пользователя" if result["negatives"]
                    else "весь каталог")
        st.subheader(f"Результат: {result['users_evaluated']} пользователей, K = {result['k']}")
        st.caption(f"Кандидаты для ранжирования: отложенные фильмы + {protocol}. "
                   f"Пропущено пользователей без понравившихся фильмов: {result.get('users_skipped', 0)}. "
                   "Усы на графике показывают 95% доверительный интервал.")
        frame = build_frame(result, labels)

        note = verdict(frame)
        if note:
            st.markdown(note)

        long_rows = []
        for key, name in METRIC_LABELS.items():
            for _, row in frame.iterrows():
                long_rows.append({"Метрика": name, "Модель": row["Модель"], "Значение": row[key],
                                  "Погрешность": row[f"{key}_ci"]})
        long = pd.DataFrame(long_rows)
        figure = px.bar(long, x="Метрика", y="Значение", color="Модель", barmode="group", error_y="Погрешность")
        ui.show_figure(figure, height=420)

        table = frame[["Модель", *METRIC_LABELS]].rename(columns=METRIC_LABELS)
        st.dataframe(table.round(4), use_container_width=True, hide_index=True)
else:
    ui.empty_state("Оценка ещё не запускалась",
                   "Задайте параметры и нажмите «Запустить оценку». Нужны пользователи с оценками фильмов.")

st.subheader("История запусков")
runs = ui.api("GET", "/evaluation/runs", params={"limit": 80})
if runs:
    history = pd.DataFrame(runs)
    history["Модель"] = history["model"].map(labels).fillna(history["model"])
    history["Дата"] = pd.to_datetime(history["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    trend = px.line(history.sort_values("id"), x="Дата", y="ndcg", color="Модель", markers=True)
    trend.update_yaxes(title="NDCG")
    ui.show_figure(trend, height=320)
    columns = ["Дата", "Модель", "k", "negatives", "users", "precision", "recall", "ndcg", "hit_rate", "map", "mrr"]
    for column in columns:
        if column not in history:
            history[column] = None
    st.dataframe(
        history[columns].rename(
            columns={"k": "K", "negatives": "Негативов", "users": "Пользователей", "precision": "Precision",
                     "recall": "Recall", "ndcg": "NDCG", "hit_rate": "Hit Rate", "map": "MAP", "mrr": "MRR"}
        ).round(4),
        use_container_width=True, hide_index=True)
else:
    st.markdown('<div class="section-note">Сохранённых запусков пока нет.</div>', unsafe_allow_html=True)

with st.expander("Как читать метрики"):
    st.write("Для каждого пользователя часть его оценок скрывается. Модель строит список из K фильмов по оставшимся "
             "данным и ранжирует среди кандидатов скрытые фильмы и случайные негативы. Успехом считается скрытый "
             "фильм с оценкой от 4.")
    st.markdown(
        "- **Precision@K**: доля удачных фильмов в списке.\n"
        "- **Recall@K**: какую долю понравившихся скрытых фильмов удалось найти.\n"
        "- **NDCG@K**: как Precision, но выше оценка, если удачные фильмы стоят ближе к началу списка.\n"
        "- **Hit Rate@K**: доля пользователей, у которых в списке есть хотя бы один удачный фильм.\n"
        "- **MAP@K**: средняя точность по позициям попаданий.\n"
        "- **MRR**: насколько высоко стоит первый удачный фильм (1 / позиция).")
    st.write("Случайный список служит базовой линией: модель полезна, только если заметно лучше него. "
             "Метрики нельзя сравнивать между запусками с разным числом негативов.")
