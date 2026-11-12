import pandas as pd
import plotly.express as px
import streamlit as st

import ui

ui.page_header("История просмотров", "Что вы оценивали, лайкали и пропускали, и как менялась активность.")

user_id = ui.current_user()
if user_id is None:
    ui.empty_state("Профиль не выбран", "Выберите профиль в боковой панели, чтобы увидеть его историю.")
    st.stop()

history = ui.api("GET", f"/users/{user_id}/history", params={"limit": 500})
if history is None:
    st.stop()
if not history:
    ui.empty_state("История пока пуста",
                   "Оцените фильм, поставьте отметку «Нравится» или пропустите карточку на странице рекомендаций.")
    st.stop()

frame = pd.DataFrame([{
    "Дата": pd.to_datetime(row["timestamp"]),
    "Фильм": row["title"],
    "Год": row.get("release_year"),
    "Жанры": row.get("genres") or "",
    "Код": row["action"],
    "Действие": ui.ACTION_LABELS.get(row["action"], row["action"]),
    "Рейтинг": row.get("vote_average"),
} for row in history])

st.subheader("Параметры отображения")
control_left, control_middle, control_right = st.columns([2, 1, 1])
available = sorted(frame["Действие"].unique())
selected = control_left.multiselect("Типы действий", available, default=available)
top_genres = control_middle.slider("Жанров на диаграмме", 3, 15, 8)
period = control_right.radio("Группировка активности", ["День", "Неделя"], horizontal=True)

filtered = frame[frame["Действие"].isin(selected)]
if filtered.empty:
    ui.empty_state("Нет данных для выбранных типов действий", "Добавьте хотя бы один тип действия в фильтр.")
    st.stop()

first, second, third = st.columns(3)
first.metric("Действий в выборке", len(filtered))
second.metric("Уникальных фильмов", filtered["Фильм"].nunique())
third.metric("Последняя активность", filtered["Дата"].max().strftime("%d.%m.%Y %H:%M"))

left, right = st.columns(2)
with left:
    st.subheader("Структура действий")
    counts = filtered["Действие"].value_counts().rename_axis("Действие").reset_index(name="Количество")
    figure = px.pie(counts, names="Действие", values="Количество", hole=0.55)
    figure.update_traces(textinfo="label+percent", sort=False)
    ui.show_figure(figure)

with right:
    st.subheader("Любимые жанры")
    genre_counts = (filtered.assign(Жанр=filtered["Жанры"].str.split(","))
                    .explode("Жанр"))
    genre_counts["Жанр"] = genre_counts["Жанр"].str.strip()
    genre_counts = genre_counts[genre_counts["Жанр"] != ""]
    top = genre_counts["Жанр"].value_counts().head(top_genres).rename_axis("Жанр").reset_index(name="Количество")
    figure = px.bar(top, x="Количество", y="Жанр", orientation="h")
    figure.update_yaxes(categoryorder="total ascending")
    ui.show_figure(figure)

st.subheader("Активность во времени")
rule = "D" if period == "День" else "W"
timeline = (filtered.set_index("Дата").groupby([pd.Grouper(freq=rule), "Действие"]).size()
            .rename("Количество").reset_index())
figure = px.bar(timeline, x="Дата", y="Количество", color="Действие")
ui.show_figure(figure, height=320)

st.subheader("Журнал действий")
table = filtered.drop(columns=["Код"]).assign(Дата=filtered["Дата"].dt.strftime("%Y-%m-%d %H:%M"))
st.dataframe(table, use_container_width=True, hide_index=True)
