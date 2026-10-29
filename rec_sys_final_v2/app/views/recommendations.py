import streamlit as st

import ui

ui.page_header("Рекомендации", "Подборка фильмов, которая меняется после каждой вашей оценки и реакции.")

user_id = ui.current_user()
if user_id is None:
    ui.empty_state("Профиль не выбран",
                   "Выберите профиль в боковой панели или создайте новый, чтобы получить персональную подборку.")
    st.stop()

stats = ui.api("GET", f"/users/{user_id}/stats") or {}
first, second, third = st.columns(3)
first.metric("Действий в истории", stats.get("interactions", 0))
second.metric("Оценённых фильмов", stats.get("ratings", 0))
third.metric("Средняя оценка", stats.get("average_rating") or "нет данных")

models = ui.fetch("/models") or []
labels = {item["key"]: item["label"] for item in models}
genres = ui.fetch("/genres") or []
if not labels:
    st.stop()

st.subheader("Параметры подборки")
with st.form("recommendation_form"):
    left, right = st.columns([2, 1])
    model_key = left.selectbox("Алгоритм", list(labels), format_func=labels.get)
    limit = right.slider("Количество фильмов", 6, 42, 15, step=3)
    chosen_genres = st.multiselect("Дополнительно учесть жанры в этой выдаче", genres)
    submitted = st.form_submit_button("Построить подборку", type="primary")

if submitted:
    params = {"model": model_key, "limit": limit, "genres": ",".join(chosen_genres)}
    items = ui.api("GET", f"/users/{user_id}/recommendations", params=params, timeout=120)
    if items is not None:
        st.session_state["recommendations"] = items
        st.session_state["recommendations_user"] = user_id
        st.session_state["recommendations_model"] = model_key
        if not items:
            ui.empty_state("Рекомендаций нет",
                           "Каталог пуст или вы уже отреагировали на все фильмы. Проверьте, что импорт каталога выполнен.")

items = st.session_state.get("recommendations", []) if st.session_state.get("recommendations_user") == user_id else []
if not items:
    if not submitted:
        ui.empty_state("Подборка ещё не построена", "Выберите алгоритм и нажмите «Построить подборку».")
    st.stop()

used_model = labels.get(st.session_state.get("recommendations_model"), "")
st.subheader(f"Ваша подборка: {used_model}")
st.markdown(f'<div class="section-note">Найдено фильмов: {len(items)}</div>', unsafe_allow_html=True)

for start in range(0, len(items), 3):
    columns = st.columns(3)
    for column, movie in zip(columns, items[start:start + 3]):
        with column:
            with st.container(border=True):
                st.markdown(ui.movie_card_html(movie), unsafe_allow_html=True)
                like, dislike, skip = st.columns(3)
                payload = {"user_id": user_id, "movie_id": movie["id"],
                           "recommendation_id": movie.get("recommendation_id")}
                if like.button("Нравится", key=f"like_{movie['id']}", use_container_width=True):
                    ui.api("POST", "/interactions", json={**payload, "action": "like"})
                    st.toast("Предпочтения обновлены")
                if dislike.button("Не мое", key=f"dislike_{movie['id']}", use_container_width=True):
                    ui.api("POST", "/interactions", json={**payload, "action": "dislike"})
                    st.toast("Предпочтения обновлены")
                if skip.button("Пропустить", key=f"skip_{movie['id']}", use_container_width=True):
                    ui.api("POST", "/interactions", json={**payload, "action": "skip"})
                    st.toast("Фильм пропущен")
                with st.expander("Поставить оценку"):
                    rating = st.slider("Оценка фильма", 0.5, 5.0, 3.0, 0.5, key=f"rating_{movie['id']}")
                    if st.button("Сохранить оценку", key=f"save_rating_{movie['id']}", use_container_width=True):
                        if ui.api("POST", "/ratings", json={"user_id": user_id, "movie_id": movie["id"],
                                                             "rating": rating}):
                            st.success("Оценка сохранена")
                    quality = st.slider("Насколько точна рекомендация", 1, 5, 3, key=f"feedback_{movie['id']}")
                    if st.button("Отправить отзыв о подборке", key=f"save_feedback_{movie['id']}",
                                 use_container_width=True):
                        record_id = movie.get("recommendation_id")
                        if record_id:
                            if ui.api("POST", "/feedback", json={"recommendation_id": record_id,
                                                                  "feedback": quality}):
                                st.success("Отзыв сохранён")
                        else:
                            st.warning("Подборка устарела. Постройте её заново и повторите.")
