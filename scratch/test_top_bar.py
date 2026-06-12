import sys
sys.path.append(".")

# Mock streamlit before importing top_bar
import streamlit as st
class MockSt:
    def markdown(self, body, unsafe_allow_html=False):
        print("--- MOCK st.markdown ---")
        print(repr(body))
        print("------------------------")
    def html(self, body):
        print("--- MOCK st.html ---")
        print(repr(body))
        print("------------------------")

st.markdown = MockSt().markdown
st.html = MockSt().html

from dashboard.components.top_bar import top_bar

top_bar(
    breadcrumb=["Opérationnel", "Tableau de bord"],
    period="Juin 2026",
    anomaly_count=3,
    user_name="Karim Benali",
    user_role="Actuaire MOA"
)
