import streamlit as st

import ui

st.set_page_config(page_title="Киносоветник", layout="wide", initial_sidebar_state="expanded")
ui.inject_styles()

navigation = st.navigation([
    st.Page("views/recommendations.py", title="Рекомендации", default=True),
    st.Page("views/history.py", title="История просмотров"),
    st.Page("views/analytics.py", title="Аналитика каталога"),
    st.Page("views/quality.py", title="Качество моделей"),
])
ui.render_sidebar()
navigation.run()
