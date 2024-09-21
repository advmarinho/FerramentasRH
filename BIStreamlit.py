import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Definir variáveis globais para as cores
COR_HORAS_EXTRAS = '#1f77b4'  # Azul padrão
COR_ADICIONAL_NOTURNO = 'r'  # Vermelho
COR_OUTROS_ADICIONAIS = 'g'  # Verde
COR_BANCO_HORAS = 'orange'  # Laranja para Banco de Horas

# Função para carregar o arquivo Excel no Streamlit
def carregar_dados():
    arquivo_excel = st.file_uploader("Escolha o arquivo Excel", type=["xlsx"])

    if arquivo_excel:
        df = pd.read_excel(arquivo_excel)
        st.write("Dados Carregados:")
        st.dataframe(df)

        # Adicionar o filtro deslizante para horas extras
        min_horas_extras = st.slider('Selecione o número mínimo de horas extras', 
                                     min_value=int(df['Horas Extras'].min()), 
                                     max_value=int(df['Horas Extras'].max()), 
                                     value=6)
        
        # Filtrando os dados com base no valor do filtro deslizante
        df_filtrado = df[df['Horas Extras'] >= min_horas_extras]

        # Exibir os dados filtrados
        st.write(f"Exibindo os casos com mais de {min_horas_extras} horas extras:")
        st.dataframe(df_filtrado)

        # Gráfico de Horas Extras (filtrados)
        st.subheader(f"Gráfico de Horas Extras (Maiores que {min_horas_extras})")
        st.bar_chart(df_filtrado[['Nome', 'Horas Extras']].set_index('Nome'), use_container_width=True)

        # Gráfico de Adicional Noturno
        st.subheader(f"Gráfico de Adicional Noturno (Maiores que {min_horas_extras})")
        st.bar_chart(df_filtrado[['Nome', 'Adicional Noturno']].set_index('Nome'), use_container_width=True)

        # Gráfico de Outros Adicionais
        st.subheader(f"Gráfico de Outros Adicionais (Maiores que {min_horas_extras})")
        st.bar_chart(df_filtrado[['Nome', 'Outros Adicionais']].set_index('Nome'), use_container_width=True)

        # Gráfico de Banco de Horas
        st.subheader(f"Gráfico de Banco de Horas (Maiores que {min_horas_extras})")
        st.bar_chart(df_filtrado[['Nome', 'Banco de Horas']].set_index('Nome'), use_container_width=True)

        # Gráfico combinado com colunas para Horas Extras e linhas para Adicional Noturno, Outros Adicionais e Banco de Horas
        st.subheader("Gráfico Combinado: Horas Extras, Adicional Noturno, Outros Adicionais e Banco de Horas")
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # Gráfico de colunas para Horas Extras
        ax1.bar(df_filtrado['Nome'], df_filtrado['Horas Extras'], label='Horas Extras', color=COR_HORAS_EXTRAS, alpha=0.7)

        # Eixo y secundário para Adicional Noturno, Outros Adicionais e Banco de Horas
        ax2 = ax1.twinx()
        ax2.plot(df_filtrado['Nome'], df_filtrado['Adicional Noturno'], label='Adicional Noturno', color=COR_ADICIONAL_NOTURNO, marker='o', linestyle='-', linewidth=2)
        ax2.plot(df_filtrado['Nome'], df_filtrado['Outros Adicionais'], label='Outros Adicionais', color=COR_OUTROS_ADICIONAIS, marker='x', linestyle='--', linewidth=2)
        ax2.plot(df_filtrado['Nome'], df_filtrado['Banco de Horas'], label='Banco de Horas', color=COR_BANCO_HORAS, marker='s', linestyle=':', linewidth=2)

        # Configurar os eixos e legendas
        ax1.set_xlabel('Nome')
        ax1.set_ylabel('Valores de Horas Extras')
        ax2.set_ylabel('Adicional Noturno, Outros Adicionais e Banco de Horas')
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        plt.title(f"Visão Geral: Horas Extras, Adicional Noturno, Outros Adicionais e Banco de Horas (Maiores que {min_horas_extras})")
        st.pyplot(fig)

if __name__ == "__main__":
    st.title("Análise de Horas Extras e Adicionais")
    carregar_dados()
