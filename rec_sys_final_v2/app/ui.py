import functools
import html
import os
import time

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
NO_PROFILE = "Не выбран"
PALETTE = ["#cfa65a", "#62b6a9", "#d9798f", "#8f9ae0", "#e3875f", "#7fb8e0", "#b9c26a", "#a58fc9", "#8b93a7"]

ACTION_LABELS = {
    "view": "Просмотр",
    "click": "Переход",
    "skip": "Пропуск",
    "like": "Нравится",
    "dislike": "Не нравится",
    "rate": "Оценка",
}

STYLES = """
<style>
:root {
    --ink: #15111b;
    --surface: #1e1926;
    --surface-high: #272131;
    --line: rgba(235, 231, 240, 0.09);
    --brass: #cfa65a;
    --teal: #62b6a9;
    --text: #ebe7f0;
    --muted: #a39bb0;
}
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1240px; }
header[data-testid="stHeader"] { background: transparent; }
section[data-testid="stSidebar"] { border-right: 1px solid var(--line); }
.brand {
    font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
    font-size: 1.7rem; font-weight: 700; color: var(--brass); line-height: 1.1;
}
.brand-sub { color: var(--muted); font-size: 0.85rem; margin: 0.25rem 0 1.1rem 0; }
.page-head { margin: 0 0 1.6rem 0; padding: 0.2rem 0 0.2rem 1.1rem; border-left: 4px solid var(--brass); }
.page-head h1 {
    margin: 0; padding: 0; line-height: 1.15; font-size: 2.2rem;
    font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif; font-weight: 700;
}
.page-head p { margin: 0.45rem 0 0 0; color: var(--muted); font-size: 1rem; max-width: 52rem; }
.empty-state {
    margin: 1.2rem 0; padding: 1.6rem 1.8rem; border-radius: 6px;
    background: var(--surface); border: 1px dashed rgba(207, 166, 90, 0.45);
}
.empty-state strong { display: block; font-size: 1.1rem; margin-bottom: 0.35rem; }
.empty-state span { color: var(--muted); }
div[data-testid="stMetric"] {
    background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 0.9rem 1.1rem;
}
div[data-testid="stMetricLabel"] p { color: var(--muted); font-size: 0.85rem; }
div[data-testid="stMetricValue"] { font-family: "Iowan Old Style", Georgia, serif; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 8px; }
.stButton > button, .stFormSubmitButton > button { border-radius: 8px; font-weight: 600; }
div[data-testid="stTabs"] button[role="tab"] { font-size: 0.98rem; }
.movie-title {
    font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
    font-size: 1.22rem; font-weight: 700; line-height: 1.25; margin: 0 0 0.35rem 0; color: var(--text);
}
.movie-meta { display: flex; gap: 1.1rem; flex-wrap: wrap; color: var(--muted); font-size: 0.83rem; margin-bottom: 0.6rem; }
.movie-meta b { color: var(--text); font-weight: 600; }
.chip {
    display: inline-block; padding: 0.12rem 0.65rem; margin: 0 0.35rem 0.35rem 0; border-radius: 4px;
    background: rgba(98, 182, 169, 0.13); color: var(--teal); font-size: 0.76rem; font-weight: 500;
}
.movie-overview { color: #cfc9da; font-size: 0.9rem; line-height: 1.55; min-height: 6.6rem; margin: 0.4rem 0 0.8rem 0; }
.score-row { display: flex; justify-content: space-between; color: var(--muted); font-size: 0.78rem; margin-bottom: 0.3rem; }
.score-track { height: 5px; border-radius: 3px; background: rgba(235, 231, 240, 0.09); overflow: hidden; margin-bottom: 0.7rem; }
.score-fill { height: 100%; background: var(--brass); }
.section-note { color: var(--muted); font-size: 0.9rem; margin: -0.3rem 0 1rem 0; }
</style>
"""


def retry(times=2, delay=0.4):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(times + 1):
                try:
                    return func(*args, **kwargs)
                except requests.ConnectionError as error:
                    last_error = error
                    time.sleep(delay * (attempt + 1))
            raise last_error

        return wrapper

    return decorator


@retry()
def request(method, path, timeout=30, **kwargs):
    response = requests.request(method, f"{API_URL}{path}", timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json()


def api(method, path, timeout=30, **kwargs):
    try:
        return request(method, path, timeout=timeout, **kwargs)
    except requests.RequestException as error:
        st.error(f"Не удалось выполнить запрос к API ({API_URL}). Проверьте, что сервис запущен. Детали: {error}")
        return None


@st.cache_data(ttl=120, show_spinner=False)
def cached_get(path, params_key):
    return request("GET", path, params=dict(params_key))


def fetch(path, **params):
    params = {key: value for key, value in params.items() if value is not None}
    try:
        return cached_get(path, tuple(sorted(params.items())))
    except requests.RequestException as error:
        st.error(f"Не удалось загрузить данные ({path}). Детали: {error}")
        return None


def inject_styles():
    st.markdown(STYLES, unsafe_allow_html=True)


def page_header(title, subtitle):
    st.markdown(
        f'<div class="page-head"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def empty_state(title, text):
    st.markdown(
        f'<div class="empty-state"><strong>{html.escape(title)}</strong><span>{html.escape(text)}</span></div>',
        unsafe_allow_html=True,
    )


def current_user():
    return st.session_state.get("user_id")


def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div class="brand">Киносоветник</div>'
            '<div class="brand-sub">Рекомендации, которые учатся на ваших оценках</div>',
            unsafe_allow_html=True,
        )
        users = api("GET", "/users")
        if users is None:
            st.session_state["user_id"] = None
            return
        options = {user["name"]: user["id"] for user in users}
        pending = st.session_state.pop("pending_profile", None)
        if pending in options:
            st.session_state["profile_select"] = pending
        choice = st.selectbox("Профиль", [NO_PROFILE] + list(options), key="profile_select")
        st.session_state["user_id"] = options.get(choice)

        with st.expander("Новый профиль", expanded=not options):
            name = st.text_input("Имя", placeholder="Например, Алекс", key="new_profile_name")
            genres = fetch("/genres") or []
            if not genres:
                st.warning("Список жанров пуст. Сначала импортируйте каталог фильмов.")
            picked = st.multiselect("Любимые жанры", genres, key="new_profile_genres")
            if st.button("Сохранить профиль", use_container_width=True):
                if not name.strip():
                    st.warning("Введите имя профиля.")
                else:
                    created = api("POST", "/users", json={"name": name.strip(), "genres": picked})
                    if created:
                        st.session_state["pending_profile"] = created["name"]
                        st.rerun()


def truncate(text, limit):
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def movie_card_html(movie):
    title = html.escape(movie.get("title") or "Без названия")
    year = movie.get("release_year") or "год не указан"
    runtime = movie.get("runtime")
    rating = float(movie.get("vote_average") or 0)
    votes = int(movie.get("vote_count") or 0)
    names = [name.strip() for name in (movie.get("genres") or "").split(",") if name.strip()]
    chips = "".join(f'<span class="chip">{html.escape(name)}</span>' for name in names[:4])
    overview = html.escape(truncate(movie.get("overview") or "Описание отсутствует", 230))
    match = max(0.0, min(1.0, float(movie.get("score") or 0)))
    runtime_part = f"<span><b>{runtime}</b> мин</span>" if runtime else ""
    return (
        f'<div class="movie-title">{title}</div>'
        f'<div class="movie-meta"><span><b>{year}</b></span>{runtime_part}'
        f'<span>рейтинг <b>{rating:.1f}</b> из 10</span><span>голосов <b>{votes}</b></span></div>'
        f'<div>{chips}</div>'
        f'<div class="movie-overview">{overview}</div>'
        f'<div class="score-row"><span>Соответствие профилю</span><span>{match * 100:.0f}%</span></div>'
        f'<div class="score-track"><div class="score-fill" style="width:{match * 100:.0f}%"></div></div>'
    )


def style_figure(figure, height=380):
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=PALETTE,
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(color="#cfc9da"),
        legend=dict(orientation="h", y=-0.2),
        hoverlabel=dict(bgcolor="#272131"),
    )
    figure.update_xaxes(gridcolor="rgba(235,231,240,0.07)", zerolinecolor="rgba(235,231,240,0.12)")
    figure.update_yaxes(gridcolor="rgba(235,231,240,0.07)", zerolinecolor="rgba(235,231,240,0.12)")
    return figure


def show_figure(figure, height=380):
    st.plotly_chart(style_figure(figure, height), use_container_width=True, theme=None)

