import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui

GENRE_METRICS = {
    "count": "Количество фильмов",
    "avg_rating": "Средний рейтинг",
    "avg_popularity": "Средняя популярность",
    "total_revenue": "Суммарные сборы",
}
TIMELINE_METRICS = {
    "count": "Количество фильмов",
    "avg_rating": "Средний рейтинг",
    "total_revenue": "Суммарные сборы",
}
AXES = {
    "popularity": "Популярность",
    "vote_average": "Средний рейтинг",
    "vote_count": "Число голосов",
    "revenue": "Сборы",
    "runtime": "Длительность, мин",
}
COLORINGS = {"genre": "Основной жанр", "language": "Язык оригинала"}
ALL_GENRES = "Все жанры"

ui.page_header("Аналитика каталога", "Как устроен каталог фильмов: оценки, жанры, динамика по годам и связь показателей.")

overview = ui.fetch("/analytics/overview")
if not overview:
    st.stop()
if not overview["movies"]:
    ui.empty_state("Каталог пуст", "Импортируйте фильмы командой python -m etl.load_movies и обновите страницу.")
    st.stop()

first, second, third, fourth = st.columns(4)
first.metric("Фильмов", f"{overview['movies']:,}".replace(",", " "))
second.metric("Жанров", overview["genres"])
third.metric("Пользователей", overview["users"])
fourth.metric("Оценок", overview["ratings"])

genres = ui.fetch("/genres") or []
year_min = int(overview["year_min"] or 1900)
year_max = int(overview["year_max"] or 2030)

with st.expander("Общие фильтры каталога", expanded=True):
    filter_left, filter_middle, filter_right = st.columns([2, 1, 1])
    years = filter_left.slider("Годы выхода", year_min, year_max, (year_min, year_max))
    min_votes = filter_middle.number_input("Минимум голосов", min_value=0, max_value=100000, value=50, step=50)
    genre = filter_right.selectbox("Жанр", [ALL_GENRES] + genres)

filters = {
    "year_from": years[0],
    "year_to": years[1],
    "min_votes": int(min_votes),
    "genre": None if genre == ALL_GENRES else genre,
}

tab_ratings, tab_genres, tab_years, tab_scatter = st.tabs(
    ["Распределение оценок", "Жанры", "Динамика по годам", "Популярность и рейтинг"]
)

with tab_ratings:
    bins = st.slider("Число интервалов", 5, 40, 20)
    data = ui.fetch("/analytics/rating-distribution", bins=bins, **filters)
    if data and data["total"]:
        edges = data["edges"]
        middles = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
        width = (edges[1] - edges[0]) * 0.92
        figure = go.Figure(go.Bar(x=middles, y=data["counts"], width=width, marker_color="#cfa65a"))
        figure.update_layout(xaxis_title="Средний рейтинг", yaxis_title="Количество фильмов")
        ui.show_figure(figure)
        st.markdown(f'<div class="section-note">Фильмов в выборке: {data["total"]}</div>', unsafe_allow_html=True)
    else:
        ui.empty_state("Нет фильмов под выбранные фильтры", "Ослабьте фильтры: расширьте годы или уменьшите минимум голосов.")

with tab_genres:
    control_left, control_right = st.columns(2)
    metric = control_left.selectbox("Показатель", list(GENRE_METRICS), format_func=GENRE_METRICS.get, key="genre_metric")
    top = control_right.slider("Сколько жанров показать", 3, 20, 12)
    data = ui.fetch("/analytics/genres", metric=metric, top=top, **filters)
    if data:
        frame = pd.DataFrame(data)
        figure = px.bar(frame, x="value", y="genre", orientation="h", text="value")
        figure.update_yaxes(categoryorder="total ascending", title="")
        figure.update_xaxes(title=GENRE_METRICS[metric])
        figure.update_traces(marker_color="#62b6a9", texttemplate="%{text:.3s}", textposition="outside")
        ui.show_figure(figure, height=max(320, 28 * len(frame) + 80))
    else:
        ui.empty_state("Нет данных", "Под выбранные фильтры не попал ни один жанр.")

with tab_years:
    metric = st.selectbox("Показатель", list(TIMELINE_METRICS), format_func=TIMELINE_METRICS.get, key="timeline_metric")
    data = ui.fetch("/analytics/timeline", metric=metric, **filters)
    if data:
        frame = pd.DataFrame(data)
        figure = px.area(frame, x="year", y="value")
        figure.update_traces(line_color="#d9798f", fillcolor="rgba(217,121,143,0.22)")
        figure.update_xaxes(title="Год выхода")
        figure.update_yaxes(title=TIMELINE_METRICS[metric])
        ui.show_figure(figure)
    else:
        ui.empty_state("Нет данных", "Под выбранные фильтры не попал ни один фильм.")

with tab_scatter:
    axis_left, axis_middle, color_column, limit_column = st.columns(4)
    x_axis = axis_left.selectbox("Ось X", list(AXES), format_func=AXES.get, index=0)
    y_axis = axis_middle.selectbox("Ось Y", list(AXES), format_func=AXES.get, index=1)
    coloring = color_column.selectbox("Цвет", list(COLORINGS), format_func=COLORINGS.get)
    limit = limit_column.slider("Число фильмов", 50, 1000, 400, step=50)
    log_left, log_right = st.columns(2)
    log_x = log_left.checkbox("Логарифмическая шкала по X", value=x_axis in ("popularity", "revenue", "vote_count"))
    log_y = log_right.checkbox("Логарифмическая шкала по Y", value=False)
    data = ui.fetch("/analytics/scatter", x=x_axis, y=y_axis, color=coloring, limit=limit, **filters)
    if data and data["points"]:
        frame = pd.DataFrame(data["points"])
        figure = px.scatter(frame, x="x", y="y", color="group", hover_name="title",
                            hover_data={"year": True, "x": ":.2f", "y": ":.2f", "group": False},
                            opacity=0.78, log_x=log_x, log_y=log_y)
        figure.update_xaxes(title=AXES[x_axis])
        figure.update_yaxes(title=AXES[y_axis])
        figure.update_traces(marker=dict(size=8))
        ui.show_figure(figure, height=460)
    else:
        ui.empty_state("Нет данных", "Под выбранные фильтры и оси не попал ни один фильм.")
