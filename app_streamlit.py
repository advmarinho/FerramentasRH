import streamlit as st
import pandas as pd
import os
import plotly.express as px
import matplotlib.colors as mcolors

# --- Funções auxiliares ---
def adjust_color_brightness(hex_color, factor):
    rgb = mcolors.to_rgb(hex_color)
    adjusted = tuple(min(1, max(0, c * factor)) for c in rgb)
    return mcolors.to_hex(adjusted)

def get_green_gradient(n, base_color="#33CCCC", min_factor=0.7, max_factor=1.0):
    if n == 1:
        return [adjust_color_brightness(base_color, (min_factor + max_factor) / 2)]
    factors = [min_factor + i * (max_factor - min_factor) / (n - 1) for i in range(n)]
    return [adjust_color_brightness(base_color, f) for f in factors]

# --- Configuração do app Streamlit ---
st.set_page_config(page_title="Dashboard de Atendimentos Gente e Gestão", layout="wide")
st.title("Dashboard de Atendimentos Gente e Gestão")
st.markdown("""
Este dashboard interativo apresenta uma análise dos atendimentos da equipe de Gente & Gestão no período de **01/01/2025 a 28/03/2025**. 
Você pode visualizar:
- A **carga de atendimentos por atendente** (gráfico com rótulos de quantidade, seguido da tabela com percentual e total de atendimentos),
- A **distribuição por tipo de atendimento** (gráfico donut com filtro de categorias, seguido da tabela) e 
- Realizar um **Drill Down** para analisar os atendimentos de um ou mais atendente.
""")

# Caminho para a planilha (ajuste conforme necessário)
excel_file = "C:/_RPA/Email/atendimentos_gg_2025.xlsx"  # Atualize conforme necessário

if "uploaded_file" not in st.session_state:
    st.session_state["uploaded_file"] = None

if st.session_state["uploaded_file"] is None and not os.path.exists(excel_file):
    st.warning("Arquivo não encontrado no caminho padrão. Selecione o arquivo manualmente ou verifique o caminho.")
    uploaded_file = st.file_uploader("Envie o arquivo Excel de atendimentos:", type=["xlsx"])
    if uploaded_file is not None:
        st.session_state["uploaded_file"] = uploaded_file
        excel_file = uploaded_file
    else:
        st.stop()  # Para até que o arquivo seja enviado
elif st.session_state["uploaded_file"] is not None:
    excel_file = st.session_state["uploaded_file"]

if st.button("Limpar arquivo carregado"):
    st.session_state["uploaded_file"] = None
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.markdown("<meta http-equiv='refresh' content='0'>", unsafe_allow_html=True)

try:
    df_total_colab = pd.read_excel(excel_file, sheet_name="Total por Atendentes")
    df_total_tipo = pd.read_excel(excel_file, sheet_name="Total por Tipo")
    df_detalhado = pd.read_excel(excel_file, sheet_name="Detalhado", index_col=0)
except Exception as e:
    st.error(f"Erro ao carregar o arquivo Excel: {e}")
    st.stop()

st.sidebar.header("Menu")
page = st.sidebar.radio("Selecione a visualização", ("Total por Atendentes", "Total por Tipo", "Drill Down"))

base_color = "#33CCCC"
color_scale = [base_color, "#2A9A9A", "#1F7F7F"]

if page == "Total por Atendentes":
    st.header("Carga de Atendimento por Atendentes")
    total_atendimentos = df_total_colab["Total Atendimentos"].sum()
    df_total_colab["Percentual"] = df_total_colab["Total Atendimentos"] / total_atendimentos * 100
    sorted_colab = df_total_colab.sort_values("Total Atendimentos", ascending=False)
    mean_value = sorted_colab["Total Atendimentos"].mean()
    labels = sorted_colab["Total Atendimentos"].astype(str)
    st.markdown(f"**Total de Atendimentos:** {total_atendimentos}")
    fig = px.bar(
        sorted_colab,
        x="Atendente",
        y="Total Atendimentos",
        text=labels,
        color="Total Atendimentos",
        color_continuous_scale=color_scale,
        title="Carga de Atendimento por Atendentes"
    )
    fig.update_traces(textposition='outside')
    fig.add_hline(
        y=mean_value,
        line_dash="dash",
        line_color="red",
        annotation_text="Média",
        annotation_position="top left"
    )
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Dados - Carga de Atendimento por Atendentes")
    st.dataframe(sorted_colab)

elif page == "Total por Tipo":
    st.header("Distribuição por Tipo de Atendimento")
    available_categories = df_total_tipo["Tipo de Atendimento"].unique()
    default_categories = list(available_categories[:12])
    selected_categories = st.multiselect(
        "Selecione as categorias disponíveis",
        options=available_categories,
        default=default_categories
    )
    filtered_tipo = df_total_tipo[df_total_tipo["Tipo de Atendimento"].isin(selected_categories)]
    if filtered_tipo.empty:
        st.warning("Nenhuma categoria corresponde à seleção.")
    else:
        sorted_tipo = filtered_tipo.sort_values("Total", ascending=False).head(12)
        fig2 = px.pie(
            sorted_tipo,
            values="Total",
            names="Tipo de Atendimento",
            title="Distribuição por Tipo de Atendimento",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Teal
        )
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True)
        st.subheader("Dados - Distribuição por Tipo de Atendimento")
        st.dataframe(sorted_tipo)

elif page == "Drill Down":
    st.header("Drill Down: Análise Detalhada por Analista")
    all_analysts = df_total_colab["Atendente"].tolist()
    options_list = ["Todos"] + all_analysts
    selected_analysts = st.multiselect(
        "Selecione os Analistas",
        options=options_list,
        default=[]
    )
    if "Todos" in selected_analysts:
        selected_analysts = all_analysts
    if not selected_analysts:
        st.write("Nenhum analista selecionado. Selecione 'Todos' ou escolha individualmente.")
    else:
        df_filtered = df_detalhado[selected_analysts]
        analyst_totals = df_filtered.sum(axis=0)
        overall_total = analyst_totals.sum()
        analyst_percentage = (analyst_totals / overall_total * 100).round(2)
        st.subheader("Percentual de Atendimento por Analista")
        percentage_df = pd.DataFrame({
            "Analista": analyst_totals.index,
            "Total Atendimentos": analyst_totals.values,
            "Percentual (%)": analyst_percentage.apply(lambda x: f"{x:,.2f}%".replace('.',',')).values
        })
        st.table(percentage_df)
        df_selected = df_filtered.reset_index().melt(
            id_vars=["Tipo de Atendimento"],
            var_name="Atendente",
            value_name="Atendimentos"
        )
        mean_drill = df_selected["Atendimentos"].mean()
        sorted_drill = df_selected.sort_values("Atendimentos", ascending=False)
        palette = get_green_gradient(len(selected_analysts), base_color=base_color, min_factor=0.7, max_factor=1.0)
        color_discrete_map = {analyst: palette[i] for i, analyst in enumerate(selected_analysts)}
        fig3 = px.bar(
            sorted_drill,
            x="Tipo de Atendimento",
            y="Atendimentos",
            color="Atendente",
            barmode="group",
            text="Atendimentos",
            title="Atendimentos por Tipo e Analista",
            color_discrete_map=color_discrete_map
        )
        fig3.update_traces(textposition='outside')
        fig3.update_xaxes(tickangle=90)
        fig3.add_hline(
            y=mean_drill,
            line_dash="dash",
            line_color="red",
            annotation_text="Média",
            annotation_position="top left"
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.subheader("Tabela Detalhada")
        st.dataframe(df_selected)

if isinstance(excel_file, str):
    with open(excel_file, "rb") as file:
        file_bytes = file.read()
else:
    file_bytes = excel_file.getvalue()

st.download_button(
    label="Baixar arquivo Excel", 
    data=file_bytes, 
    file_name="atendimentos_gg_2025.xlsx", 
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.markdown("<hr><center>By Anderson Marinho</center>", unsafe_allow_html=True)
