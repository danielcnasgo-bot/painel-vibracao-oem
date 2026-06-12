import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
import zipfile
import io
import gc  # Biblioteca para forçar a limpeza da Memória RAM

# ==========================================
# 0. CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==========================================
st.set_page_config(page_title="Gerador de Relatórios O&M", layout="centered")
st.title("Gerador de Relatórios de Confiabilidade O&M")

# ==========================================
# 1. FUNÇÕES ESTATÍSTICAS
# ==========================================
def calcular_p99_com_trava(series):
    s_limpa = series.dropna()
    if s_limpa.empty: return np.nan
    q1 = s_limpa.quantile(0.25)
    q3 = s_limpa.quantile(0.75)
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr
    p99_real = s_limpa.quantile(0.99)
    return min(p99_real, upper_fence)

def calcular_media_p90(series):
    s_limpa = series.dropna()
    if s_limpa.empty: return np.nan
    p90 = s_limpa.quantile(0.90)
    dados_90 = s_limpa[s_limpa <= p90]
    return dados_90.mean()

# ==========================================
# 2. CONFIGURAÇÃO DA UNIDADE VIA BARRA LATERAL
# ==========================================
UNIDADE_ALVO = st.sidebar.selectbox('Selecione a Unidade', ['UG1', 'UG2'])

limites_alarme_ug1 = {'50-100MW': {'OMGG-0':127.4375, 'OMGG-90':154.71, 'OMGG-A':360.83, 'VMGG-0':0.60, 'VMGG-90':0.63, 'VMCG-A':0.85, 'OMGT-0':134.64, 'OMGT-90':137.50, 'VMGT-0':1.38, 'VMGT-90':1.21, 'VCGR':2.00}, '101-150MW': {'OMGG-0':122.70, 'OMGG-90':149.38, 'OMGG-A':373.62, 'VMGG-0':0.75, 'VMGG-90':0.75, 'VMCG-A':1.22, 'OMGT-0':137.50, 'OMGT-90':137.50, 'VMGT-0':1.38, 'VMGT-90':1.38, 'VCGR':2.11}, '151-200MW': {'OMGG-0':137.43, 'OMGG-90':164.89, 'OMGG-A':375.55, 'VMGG-0':0.75, 'VMGG-90':0.75, 'VMCG-A':1.73, 'OMGT-0':137.50, 'OMGT-90':137.50, 'VMGT-0':1.38, 'VMGT-90':1.38, 'VCGR':2.02}}
limites_trip_ug1 = {'50-100MW': {'OMGG-0':224, 'OMGG-90':224, 'OMGG-A':451.035, 'VMGG-0':0.75, 'VMGG-90':0.78, 'VMCG-A':1.065, 'OMGT-0':252, 'OMGT-90':252, 'VMGT-0':1.65, 'VMGT-90':1.52, 'VCGR':2.51}, '101-150MW': {'OMGG-0':224, 'OMGG-90':224, 'OMGG-A':467.025, 'VMGG-0':0.84, 'VMGG-90':0.79, 'VMCG-A':1.53, 'OMGT-0':252, 'OMGT-90':252, 'VMGT-0':1.73, 'VMGT-90':1.72, 'VCGR':2.64}, '151-200MW': {'OMGG-0':224, 'OMGG-90':224, 'OMGG-A':469.44, 'VMGG-0':1.10, 'VMGG-90':0.88, 'VMCG-A':2.16, 'OMGT-0':252, 'OMGT-90':252, 'VMGT-0':1.54, 'VMGT-90':1.59, 'VCGR':2.52}}
limites_alarme_ug2 = {'50-100MW': {'OMGG-0':212.5, 'OMGG-90':212.5, 'OMGG-A':301.88, 'VMGG-0':0.54, 'VMGG-90':0.43, 'VMCG-A':0.90, 'OMGT-0':84.04, 'OMGT-90':77.58, 'VMGT-0':1.38, 'VMGT-90':1.38, 'VCGR':2.70}, '101-150MW': {'OMGG-0':212.50, 'OMGG-90':212.50, 'OMGG-A':296.48, 'VMGG-0':0.65, 'VMGG-90':0.56, 'VMCG-A':0.85, 'OMGT-0':102.10, 'OMGT-90':104.43, 'VMGT-0':1.38, 'VMGT-90':1.38, 'VCGR':3.14}, '151-200MW': {'OMGG-0':212.5, 'OMGG-90':212.5, 'OMGG-A':292.04, 'VMGG-0':0.75, 'VMGG-90':0.60, 'VMCG-A':1.10, 'OMGT-0':124.59, 'OMGT-90':125.53, 'VMGT-0':1.38, 'VMGT-90':1.38, 'VCGR':4.80}}
limites_trip_ug2 = {'50-100MW': {'OMGG-0':252, 'OMGG-90':252, 'OMGG-A':377.355, 'VMGG-0':0.67, 'VMGG-90':0.53, 'VMCG-A':1.125, 'OMGT-0':252, 'OMGT-90':252, 'VMGT-0':2.05, 'VMGT-90':1.71, 'VCGR':3.38}, '101-150MW': {'OMGG-0':252, 'OMGG-90':252, 'OMGG-A':370.605, 'VMGG-0':0.81, 'VMGG-90':0.70, 'VMCG-A':1.07, 'OMGT-0':252, 'OMGT-90':252, 'VMGT-0':2.18, 'VMGT-90':1.86, 'VCGR':3.93}, '151-200MW': {'OMGG-0':252, 'OMGG-90':252, 'OMGG-A':365.055, 'VMGG-0':0.78, 'VMGG-90':0.75, 'VMCG-A':1.38, 'OMGT-0':252, 'OMGT-90':252, 'VMGT-0':1.83, 'VMGT-90':1.88, 'VCGR':6.00}}

if UNIDADE_ALVO == 'UG1':
    limites_alarme, limites_trip, pref = limites_alarme_ug1, limites_trip_ug1, 'U1'
else:
    limites_alarme, limites_trip, pref = limites_alarme_ug2, limites_trip_ug2, 'U2'

estrutura_abas = {
    'MGT': {
        'VMGT': [f'AQT.{pref}.EQ1.CLIENT.VMGT-0', f'AQT.{pref}.EQ1.CLIENT.VMGT-90'],
        'OMGT': [f'AQT.{pref}.EQ1.CLIENT.OMGT-0', f'AQT.{pref}.EQ1.CLIENT.OMGT-90'],
        'TEMP.': [f'CF.{pref}.TUR.MGT.49_{i}' for i in range(1, 6)]
    },
    'MGG': {
        'VMGG': [f'AQT.{pref}.EQ1.CLIENT.VMGG-0', f'AQT.{pref}.EQ1.CLIENT.VMGG-90'],
        'OMGG': [f'AQT.{pref}.EQ1.CLIENT.OMGG-0', f'AQT.{pref}.EQ1.CLIENT.OMGG-90'],
        'VCGR': [f'AQT.{pref}.EQ1.CLIENT.VCGR'],
        'TEMP.': [f'CF.{pref}.GER.MGS.49_{i}' for i in range(1, 5)]
    },
    'ME': {
        'VMCG': [f'AQT.{pref}.EQ1.CLIENT.VMCG-A'],
        'TEMP.': [f'CF.{pref}.TUR.ME.49_{i}' for i in range(12, 21)]
    }
}

todas_as_colunas = [col for macro in estrutura_abas.values() for micro in macro.values() for col in micro]
colunas_vibracao = [col for macro in estrutura_abas.values() for micro_nome, cols in macro.items() if micro_nome != 'TEMP.' for col in cols]
colunas_temperatura = [col for macro in estrutura_abas.values() for micro_nome, cols in macro.items() if micro_nome == 'TEMP.' for col in cols]

def extrair_short_name(coluna):
    if 'CLIENT.' in coluna: return coluna.split('CLIENT.')[-1]
    return coluna.split('.')[-1]

def formatar_nome_eixo(short_name, is_temp=False):
    if is_temp: return f"Sensor {short_name}"
    return f"Eixo {short_name.split('-')[-1]}°" if '-' in short_name and short_name.split('-')[-1] in ['0', '90'] else "Eixo Único"

# ==========================================
# 3. UPLOAD DO ARQUIVO E PROCESSAMENTO
# ==========================================
uploaded_file = st.file_uploader("Carregue a base de dados em Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    with st.spinner("Processando dados, gerando dashboard HTML e exportando Imagens HD. Isso levará alguns segundos..."):
        df_presente = pd.read_excel(uploaded_file, sheet_name='Presente')
        df_passado = pd.read_excel(uploaded_file, sheet_name='Passado')

        col_data, col_pot = 'Data', f'CF.{pref}.GER.SYN.ACTIVE_POWER_P1'

        for df in [df_presente, df_passado]:
            if col_pot in df.columns:
                df[col_pot] = df[col_pot].astype(str).str.replace(',', '.')
                df[col_pot] = pd.to_numeric(df[col_pot], errors='coerce')
                
            for col in todas_as_colunas: 
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
            if col_data in df.columns:
                df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
                df.sort_values(col_data, inplace=True)
                
            if col_pot in df.columns:
                mask_pot_zero = (df[col_pot] == 0)
                for col_vib in colunas_vibracao:
                    if col_vib in df.columns:
                        df.loc[mask_pot_zero, col_vib] = 0.0

        JANELA_MW = 5.0
        bins_potencia = [50, 100, 150, 200]
        labels_potencia_base = ['50-100MW', '101-150MW', '151-200MW']
        _cache_historico = {}

        def calcular_linha_historica(pot_atual):
            if pd.isna(pot_atual): return pd.Series({c + '_media_p90': np.nan for c in todas_as_colunas})
            pot_inteira = int(pot_atual)
            if pot_inteira in _cache_historico: return _cache_historico[pot_inteira]
            
            filtro = (df_passado[col_pot] >= pot_inteira - JANELA_MW) & (df_passado[col_pot] <= pot_inteira + JANELA_MW)
            df_janela = df_passado.loc[filtro]
            
            resultados = {}
            for c in todas_as_colunas:
                if c in df_janela.columns:
                    s_historico = df_janela[c].copy()
                    if c in colunas_temperatura:
                        s_historico = s_historico[s_historico <= 100.0]
                    resultados[c + '_media_p90'] = calcular_media_p90(s_historico)
                else:
                    resultados[c + '_media_p90'] = np.nan
            resultado_series = pd.Series(resultados)
            _cache_historico[pot_inteira] = resultado_series
            return resultado_series

        baselines = df_presente[col_pot].apply(calcular_linha_historica)
        df_presente = pd.concat([df_presente, baselines], axis=1)

        sns.set_theme(style="whitegrid", context="talk")
        zip_buffer = io.BytesIO()

        # Inicia a construção da String do HTML do Dashboard
        html_content = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Dashboard - {UNIDADE_ALVO}</title>
        <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script><style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; }}
        h1 {{ text-align: center; color: #333; }}
        .macro-tabs {{ overflow: hidden; background-color: #1f77b4; border-radius: 8px 8px 0 0; display: flex; justify-content: center; }}
        .macro-tabs button {{ background-color: inherit; border: none; outline: none; cursor: pointer; padding: 16px 40px; font-weight: bold; color: white; font-size: 16px; transition: 0.3s; }}
        .macro-tabs button:hover {{ background-color: #155a8a; }}
        .macro-tabs button.active {{ background-color: #fff; color: #1f77b4; border-top: 3px solid #1f77b4; }}
        .macro-content {{ display: none; border: 1px solid #ccc; border-top: none; background-color: #fff; padding: 20px; border-radius: 0 0 8px 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
        .micro-tabs {{ overflow: hidden; border-bottom: 2px solid #ccc; margin-bottom: 20px; display: flex; justify-content: center; }}
        .micro-tabs button {{ background-color: inherit; border: none; outline: none; cursor: pointer; padding: 12px 24px; font-weight: bold; color: #555; transition: 0.3s; }}
        .micro-tabs button:hover {{ background-color: #eee; }}
        .micro-tabs button.active {{ color: #0056b3; border-bottom: 3px solid #0056b3; }}
        .micro-content {{ display: none; width: 100%; box-sizing: border-box; }}
        .grafico-container {{ margin-bottom: 40px; border-bottom: 2px solid #eee; padding-bottom: 20px; width: 100%;}}
        .styled-table {{ border-collapse: collapse; margin: 25px auto; font-size: 0.9em; font-family: sans-serif; min-width: 400px; box-shadow: 0 0 20px rgba(0, 0, 0, 0.15); width: 90%; background-color: #ffffff; }}
        .styled-table thead tr {{ background-color: #1f77b4; color: #ffffff; text-align: center; font-weight: bold; }}
        .styled-table th, .styled-table td {{ padding: 12px 15px; text-align: center; border: 1px solid #dddddd; }}
        .styled-table tbody tr {{ border-bottom: 1px solid #dddddd; }}
        .styled-table tbody tr:nth-of-type(even) {{ background-color: #f8f9fa; }}
        .styled-table tbody tr:hover {{ background-color: #f1f1f1; }}
        </style></head><body>
        <h1>Painel de Confiabilidade O&M - {UNIDADE_ALVO}</h1>"""

        html_content += '<div class="macro-tabs">\n'
        for i, macro_nome in enumerate(estrutura_abas.keys()):
            html_content += f'<button class="macro-links {"active" if i==0 else ""}" onclick="openMacro(event, \'{macro_nome}\')">{macro_nome}</button>\n'
        html_content += '</div>\n'

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            
            for i, (macro_nome, micros) in enumerate(estrutura_abas.items()):
                display_macro = "block" if i == 0 else "none"
                html_content += f'<div id="{macro_nome}" class="macro-content" style="display:{display_macro}">\n'
                
                html_content += '<div class="micro-tabs">\n'
                for j, micro_nome in enumerate(micros.keys()):
                    html_content += f'<button class="micro-links {macro_nome}-links {"active" if j==0 else ""}" onclick="openMicro(event, \'{macro_nome}_{micro_nome.replace(".","")}\', \'{macro_nome}\')">{micro_nome}</button>\n'
                html_content += '</div>\n'

                for j, (micro_nome, cols) in enumerate(micros.items()):
                    id_micro = f"{macro_nome}_{micro_nome.replace('.','')}"
                    display_micro = "block" if j == 0 else "none"
                    html_content += f'<div id="{id_micro}" class="micro-content {macro_nome}-content" style="display:{display_micro}">\n'
                    
                    is_temp = (micro_nome == 'TEMP.')
                    unidade_medida = "°C" if is_temp else ("mm/s" if micro_nome.startswith('V') else "μm")
                    
                    cols_existentes = [c for c in cols if c in df_presente.columns]
                    if not cols_existentes:
                        html_content += '<p>Dados não encontrados.</p></div>\n'
                        continue
                        
                    df_box_pass = df_passado[[col_data, col_pot] + cols_existentes].copy()
                    df_box_pass['Periodo'] = 'Histórico'
                    df_box_pres = df_presente[[col_data, col_pot] + cols_existentes].copy()
                    df_box_pres['Periodo'] = 'Semana Atual'
                    
                    df_box = pd.concat([df_box_pass, df_box_pres])
                    df_box['Range'] = pd.cut(df_box[col_pot], bins=bins_potencia, labels=labels_potencia_base)
                    
                    df_box_melt = df_box.melt(id_vars=[col_data, col_pot, 'Periodo', 'Range'], value_vars=cols_existentes, var_name='ColunaOriginal', value_name='Valor').dropna(subset=['Range', 'Valor'])
                    df_box_melt['ShortName'] = df_box_melt['ColunaOriginal'].apply(extrair_short_name)
                    df_box_melt['Eixo'] = df_box_melt['ShortName'].apply(lambda x: formatar_nome_eixo(x, is_temp))
                    eixos_unicos = [formatar_nome_eixo(extrair_short_name(c), is_temp) for c in cols_existentes]

                    df_box_melt['n_amostras'] = df_box_melt.groupby(['Periodo', 'Range', 'Eixo'], observed=False)['Valor'].transform('count')
                    df_box_melt = df_box_melt[df_box_melt['n_amostras'] >= 20]

                    df_atual_melt = df_box_melt[df_box_melt['Periodo'].str.contains('Semana Atual')].copy()
                    
                    def count_amostras_atual(r):
                        sub = df_atual_melt[df_atual_melt['Range'] == r]
                        return sub.groupby('ShortName', observed=False).size().max() if not sub.empty else 0

                    labels_base_com_n = {r: f"{r}<br>(n={count_amostras_atual(r)})" for r in labels_potencia_base}
                    labels_sns_atual = {r: f"{r}\n(n={count_amostras_atual(r)})" for r in labels_potencia_base}
                    
                    df_atual_melt['Range_Plotly'] = df_atual_melt['Range'].map(labels_base_com_n)
                    df_atual_melt['Range_Sns'] = df_atual_melt['Range'].map(labels_sns_atual)

                    # --- 1. HTML PLOTLY: BOXPLOT EXPLORATÓRIO ---
                    fig_box = px.box(df_box_melt, x='Range', y='Valor', color='Periodo', facet_col='Eixo', points='outliers',
                                     title=f'[EXPLORATÓRIO] Comparativo Macro - {macro_nome} {micro_nome}',
                                     category_orders={"Range": labels_potencia_base, "Eixo": eixos_unicos},
                                     labels={col_pot: 'Potência (MW)', 'Valor': f'Amplitude ({unidade_medida})'})
                    fig_box.update_layout(boxmode='group', template="plotly_white", height=500, margin=dict(l=20, r=20, t=50, b=40))
                    fig_box.update_xaxes(tickangle=45)
                    
                    if not is_temp:
                        for col_idx, col_name in enumerate(cols_existentes, start=1):
                            sn = extrair_short_name(col_name)
                            alarms, trips = [limites_alarme[r].get(sn, None) for r in labels_potencia_base], [limites_trip[r].get(sn, None) for r in labels_potencia_base]
                            if any(a is not None for a in alarms): fig_box.add_trace(go.Scatter(x=labels_potencia_base, y=alarms, mode='markers', marker=dict(symbol='line-ew', size=40, color='#FFCC00', line=dict(color='#FFCC00', width=4)), showlegend=False), row=1, col=col_idx)
                            if any(t is not None for t in trips): fig_box.add_trace(go.Scatter(x=labels_potencia_base, y=trips, mode='markers', marker=dict(symbol='line-ew', size=40, color='red', line=dict(color='red', width=4)), showlegend=False), row=1, col=col_idx)

                    html_content += f'<div class="grafico-container">{fig_box.to_html(full_html=False, include_plotlyjs=False, default_width="100%")}</div>\n'

                    # --- 2. HTML PLOTLY: BOXPLOT EXECUTIVO COM P99 ---
                    fig_exec = px.box(df_atual_melt, x='Range_Plotly', y='Valor', facet_col='Eixo', points='outliers',
                                     title=f'Visão Geral - {macro_nome} {micro_nome}', category_orders={"Range_Plotly": list(labels_base_com_n.values()), "Eixo": eixos_unicos},
                                     color_discrete_sequence=['#1f77b4'], hover_data=[col_pot], labels={'Valor': f'Amplitude ({unidade_medida})'}) 
                    fig_exec.update_layout(template="plotly_white", height=600, margin=dict(l=20, r=20, t=50, b=50))
                    fig_exec.update_xaxes(tickangle=45)
                    
                    for col_idx, col_name in enumerate(cols_existentes, start=1):
                        sn = extrair_short_name(col_name)
                        for r_base, r_plotly in zip(labels_potencia_base, labels_base_com_n.values()):
                            df_filtered = df_atual_melt[(df_atual_melt['Range'] == r_base) & (df_atual_melt['ShortName'] == sn)]
                            if not df_filtered.empty:
                                p99_val = calcular_p99_com_trava(df_filtered['Valor'])
                                if pd.notna(p99_val):
                                    fig_exec.add_shape(type="line", x0=labels_potencia_base.index(r_base)-0.4, x1=labels_potencia_base.index(r_base)+0.4, y0=p99_val, y1=p99_val, line=dict(color="purple", width=2, dash="dash"), row=1, col=col_idx)
                                    fig_exec.add_annotation(x=r_plotly, y=p99_val, text=f"<b>P99={p99_val:.2f}</b>", showarrow=False, yshift=10, font=dict(color='purple', size=11), row=1, col=col_idx)
                        
                        if not is_temp:
                            alarms, trips = [limites_alarme[r].get(sn, None) for r in labels_potencia_base], [limites_trip[r].get(sn, None) for r in labels_potencia_base]
                            if any(a is not None for a in alarms): fig_exec.add_trace(go.Scatter(x=list(labels_base_com_n.values()), y=alarms, mode='markers', marker=dict(symbol='line-ew', size=40, color='#FFCC00', line=dict(color='#FFCC00', width=4)), showlegend=False), row=1, col=col_idx)
                            if any(t is not None for t in trips): fig_exec.add_trace(go.Scatter(x=list(labels_base_com_n.values()), y=trips, mode='markers', marker=dict(symbol='line-ew', size=40, color='red', line=dict(color='red', width=4)), showlegend=False), row=1, col=col_idx)
                    
                    html_content += f'<div class="grafico-container">{fig_exec.to_html(full_html=False, include_plotlyjs=False, default_width="100%")}</div>\n'

                    # --- GERAÇÃO IMAGEM ESTÁTICA ULTRAWIDE NO BUFFER ---
                    fig_static_box, axes_box = plt.subplots(1, len(eixos_unicos), figsize=(24, 12), sharey=True)
                    if len(eixos_unicos) == 1: axes_box = [axes_box]
                    fig_static_box.suptitle(f'Visão Geral - {macro_nome} {micro_nome}', fontsize=24, fontweight='bold')
                    
                    for ax_idx, eixo_nome in enumerate(eixos_unicos):
                        ax = axes_box[ax_idx]
                        df_eixo = df_atual_melt[df_atual_melt['Eixo'] == eixo_nome]
                        sn = extrair_short_name(cols_existentes[ax_idx])
                        
                        if not df_eixo.empty:
                            sns.boxplot(data=df_eixo, x='Range_Sns', y='Valor', order=list(labels_sns_atual.values()), ax=ax, color='#8AB1D4', width=0.5, fliersize=0, whis=(0, 100))
                            sns.stripplot(data=df_eixo, x='Range_Sns', y='Valor', order=list(labels_sns_atual.values()), ax=ax, color='#1f77b4', alpha=0.6, jitter=True, size=4)
                            
                        ax.set_title(eixo_nome, fontsize=18)
                        ax.set_xlabel('Faixa de Potência (MW)', fontsize=16)
                        ax.set_ylabel(f'Amplitude ({unidade_medida})' if ax_idx == 0 else '', fontsize=16)
                        ax.tick_params(axis='both', which='major', labelsize=14)
                        
                        total_alarme_viol = 0
                        total_trip_viol = 0
                        
                        for pos_x, (r_base, r_sns) in enumerate(zip(labels_potencia_base, labels_sns_atual.values())):
                            df_filt = df_eixo[df_eixo['Range'] == r_base]
                            if not df_filt.empty:
                                p99_val = calcular_p99_com_trava(df_filt['Valor'])
                                if pd.notna(p99_val):
                                    ax.hlines(p99_val, pos_x - 0.4, pos_x + 0.4, colors='purple', linestyles='dashed', lw=2)
                                    ax.text(pos_x, p99_val + (df_eixo['Valor'].max() * 0.02), f'P99={p99_val:.2f}', color='purple', ha='center', va='bottom', fontweight='bold', fontsize=13)
                                
                                if not is_temp:
                                    a, t = limites_alarme[r_base].get(sn, None), limites_trip[r_base].get(sn, None)
                                    if a: 
                                        ax.hlines(a, pos_x - 0.3, pos_x + 0.3, colors='#FFCC00', lw=4, label='Limite Alarme' if pos_x == 0 else "")
                                        total_alarme_viol += (df_filt['Valor'] > a).sum()
                                    if t: 
                                        ax.hlines(t, pos_x - 0.3, pos_x + 0.3, colors='red', lw=4, label='Limite Trip' if pos_x == 0 else "")
                                        total_trip_viol += (df_filt['Valor'] > t).sum()

                        if not is_temp:
                            from matplotlib.patches import Patch
                            handles, labels = ax.get_legend_handles_labels()
                            patch_alm = Patch(color='none', label=f'Excedeu Alarme: {total_alarme_viol}x')
                            patch_trip = Patch(color='none', label=f'Excedeu Trip: {total_trip_viol}x')
                            handles.extend([patch_alm, patch_trip])
                            ax.legend(handles=handles, loc='upper right', fontsize=14, frameon=True, facecolor='white')

                    plt.tight_layout()
                    
                    img_buffer_box = io.BytesIO()
                    fig_static_box.savefig(img_buffer_box, format="png", dpi=250, bbox_inches='tight')
                    zip_file.writestr(f"01_Boxplot_Executivo_{macro_nome}_{micro_nome.replace('.','')}.png", img_buffer_box.getvalue())
                    plt.close('all')
                    img_buffer_box.close()
                    gc.collect() # Libera RAM imediatamente

                    # --- 3. HTML PLOTLY: TENDÊNCIA DINÂMICA ---
                    if is_temp:
                        medias_atuais = {col: df_presente[col].mean() for col in cols_existentes}
                        sensor_pior = max(medias_atuais, key=medias_atuais.get)
                        nome_pior_sensor = formatar_nome_eixo(extrair_short_name(sensor_pior), True)
                        
                        cols_p90 = [c + '_media_p90' for c in cols_existentes]
                        media_historica_global = df_presente[cols_p90].mean(axis=1)

                        fig_tend = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, subplot_titles=[f"Temperatura (°C) - {nome_pior_sensor} (Atual vs Média Global Histórica)", "Potência (MW)"])
                        fig_tend.add_trace(go.Scatter(x=df_presente[col_data], y=df_presente[sensor_pior], name=f"Atual: {nome_pior_sensor}", line=dict(color='rgba(214, 39, 40, 0.8)', width=2), customdata=df_presente[col_pot], hovertemplate=f"%{{y:.2f}} °C<br>Pot: %{{customdata:.1f}} MW"), row=1, col=1)
                        fig_tend.add_trace(go.Scatter(x=df_presente[col_data], y=media_historica_global, name="Histórico Global (90%)", line=dict(color='green', dash='dot', width=2.5)), row=1, col=1)
                        fig_tend.update_yaxes(title_text="Temperatura (°C)", row=1, col=1)
                        fig_tend.add_trace(go.Scatter(x=df_presente[col_data], y=df_presente[col_pot], name="Potência (MW)", line=dict(color='orange', width=2)), row=2, col=1)
                        fig_tend.update_layout(title=f'Tendência Dinâmica: {macro_nome} {micro_nome}', hovermode="x unified", template="plotly_white", height=600, margin=dict(l=20, r=20, t=50, b=20))
                    else:
                        titulos_sub = [formatar_nome_eixo(extrair_short_name(c)) for c in cols_existentes] + ["Potência (MW)"]
                        fig_tend = make_subplots(rows=len(cols_existentes)+1, cols=1, shared_xaxes=True, vertical_spacing=0.06, subplot_titles=titulos_sub)
                        for idx_col, col_val in enumerate(cols_existentes):
                            fig_tend.add_trace(go.Scatter(x=df_presente[col_data], y=df_presente[col_val], name=f"Atual", line=dict(color='rgba(0, 0, 255, 0.4)', width=1.5), customdata=df_presente[col_pot], hovertemplate=f"%{{y:.2f}} {unidade_medida}<br>Pot: %{{customdata:.1f}} MW"), row=idx_col+1, col=1)
                            fig_tend.add_trace(go.Scatter(x=df_presente[col_data], y=df_presente[col_val + '_media_p90'], name=f"Média Hist. (90%)", line=dict(color='green', dash='dot', width=2.5)), row=idx_col+1, col=1)
                            fig_tend.update_yaxes(title_text=f"Amplitude ({unidade_medida})", row=idx_col+1, col=1)
                        fig_tend.add_trace(go.Scatter(x=df_presente[col_data], y=df_presente[col_pot], name="Potência (MW)", line=dict(color='orange', width=2)), row=len(cols_existentes)+1, col=1)
                        fig_tend.update_layout(title=f'Tendência Dinâmica: {macro_nome} {micro_nome}', hovermode="x unified", template="plotly_white", height=300*(len(cols_existentes)+1), margin=dict(l=20, r=20, t=50, b=20))
                        
                    html_content += f'<div class="grafico-container">{fig_tend.to_html(full_html=False, include_plotlyjs=False, default_width="100%")}</div>\n'
                    
                    # --- 4. GERAÇÃO IMAGEM ESTÁTICA DA TENDÊNCIA NO BUFFER ---
                    if is_temp:
                        fig_static_tend, axes_tend = plt.subplots(2, 1, figsize=(24, 12), sharex=True)
                        fig_static_tend.suptitle(f'Tendência Dinâmica - {macro_nome} {micro_nome}', fontsize=24, fontweight='bold')
                        ax_temp, ax_pot = axes_tend[0], axes_tend[1]
                        ax_temp.plot(df_presente[col_data], df_presente[sensor_pior], color='red', linewidth=2, label=f"Atual: {nome_pior_sensor} (Pior)")
                        ax_temp.plot(df_presente[col_data], media_historica_global, color='green', linestyle='--', linewidth=2.5, label="Histórico Global (90%)")
                        ax_temp.set_ylabel("Temperatura (°C)", fontsize=16)
                        ax_temp.tick_params(axis='both', which='major', labelsize=14)
                        ax_temp.legend(loc="upper right", fontsize=14)
                    else:
                        fig_static_tend, axes_tend = plt.subplots(len(cols_existentes) + 1, 1, figsize=(24, 12), sharex=True)
                        fig_static_tend.suptitle(f'Tendência Dinâmica - {macro_nome} {micro_nome}', fontsize=24, fontweight='bold')
                        for ax_idx, col_val in enumerate(cols_existentes):
                            ax = axes_tend[ax_idx]
                            ax.plot(df_presente[col_data], df_presente[col_val], color='blue', alpha=0.5, linewidth=1.5, label='Valor Atual')
                            ax.plot(df_presente[col_data], df_presente[col_val + '_media_p90'], color='green', linestyle='--', linewidth=2.5, label='Média Hist. (90%)')
                            ax.set_ylabel(f"{formatar_nome_eixo(extrair_short_name(col_val))}\n({unidade_medida})", fontsize=16)
                            ax.tick_params(axis='both', which='major', labelsize=14)
                            ax.legend(loc="upper right", fontsize=14)
                        ax_pot = axes_tend[-1]
                        
                    ax_pot.plot(df_presente[col_data], df_presente[col_pot], color='orange', linewidth=2)
                    ax_pot.set_ylabel("Potência (MW)", fontsize=16)
                    ax_pot.set_xlabel("Período (Semana Atual)", fontsize=16)
                    ax_pot.tick_params(axis='both', which='major', labelsize=14)
                    plt.tight_layout()
                    
                    img_buffer_tend = io.BytesIO()
                    fig_static_tend.savefig(img_buffer_tend, format="png", dpi=250, bbox_inches='tight')
                    zip_file.writestr(f"02_Tendencia_Executiva_{macro_nome}_{micro_nome.replace('.','')}.png", img_buffer_tend.getvalue())
                    plt.close('all')
                    img_buffer_tend.close()
                    gc.collect() # Libera RAM imediatamente

                    # --- 5. TABELA DE VALIDAÇÃO DA MÉDIA DE 90% (INSERIDA NO HTML) ---
                    tabela_auditoria = []
                    for p_alvo in range(50, 205, 5):
                        df_janela = df_passado.loc[(df_passado[col_pot] >= p_alvo - JANELA_MW) & (df_passado[col_pot] <= p_alvo + JANELA_MW)]
                        if len(df_janela) > 0:
                            linha = {'Potência Específica (MW)': f"{p_alvo} MW", 'Janela de Cálculo (MW)': f"{p_alvo-5} a {p_alvo+5}", 'Amostras Úteis (n)': len(df_janela)}
                            for col in cols_existentes:
                                val = calcular_media_p90(df_janela[col])
                                linha[f'Média 90% ({extrair_short_name(col)})'] = f"{val:.2f}" if pd.notna(val) else "-"
                            tabela_auditoria.append(linha)
                            
                    df_tabela_aud = pd.DataFrame(tabela_auditoria)
                    html_content += f'<div class="grafico-container" style="padding-bottom: 50px;"><h3 style="text-align: center; color: #555;">Tabela de Auditoria do Histórico: Média de 90% dos Dados ({macro_nome} {micro_nome})</h3>'
                    html_content += f'{df_tabela_aud.to_html(index=False, classes="styled-table", justify="center")}</div>\n</div>\n'
                    
                html_content += '</div>\n'

            # --- 6. FECHAMENTO DO HTML E INSERÇÃO NO ZIP ---
            html_content += """
            <script>
            function openMacro(evt, macroName) {
              var macros = document.getElementsByClassName("macro-content");
              for (var i = 0; i < macros.length; i++) { macros[i].style.display = "none"; }
              var links = document.getElementsByClassName("macro-links");
              for (var i = 0; i < links.length; i++) { links[i].classList.remove("active"); }
              document.getElementById(macroName).style.display = "block";
              evt.currentTarget.classList.add("active");
              window.dispatchEvent(new Event('resize'));
            }

            function openMicro(evt, microName, macroName) {
              var micros = document.getElementsByClassName(macroName + "-content");
              for (var i = 0; i < micros.length; i++) { micros[i].style.display = "none"; }
              var links = document.getElementsByClassName(macroName + "-links");
              for (var i = 0; i < links.length; i++) { links[i].classList.remove("active"); }
              document.getElementById(microName).style.display = "block";
              evt.currentTarget.classList.add("active");
              window.dispatchEvent(new Event('resize'));
            }
            setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 200);
            </script></body></html>"""
            
            zip_file.writestr(f"00_Dashboard_Interativo_{UNIDADE_ALVO}.html", html_content.encode('utf-8'))

        st.success("Análise concluída com sucesso!")
        
        st.download_button(
            label="📦 Baixar Relatório Completo (.zip)",
            data=zip_buffer.getvalue(),
            file_name=f"Relatorio_Confiabilidade_{UNIDADE_ALVO}.zip",
            mime="application/zip",
        )
else:
    st.info("Aguardando upload da planilha Excel para iniciar o processamento matemático.")
