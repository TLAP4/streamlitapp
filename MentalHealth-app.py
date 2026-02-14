import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import os

# Configuration de la page
st.set_page_config(page_title="Analyse des données de santé mentale des étudiants avec DuckDB", layout="wide")

# Titre de l'application
st.title("Analyse des données santé mentale des étudiants avec DuckDB et Streamlit")
st.write("Cette application analyse les données de santé mentale des étudiants en utilisant DuckDB et Streamlit.")

# Charger les données depuis le dossier data
chemin_fichier = os.path.join("data", "Student Mental Health.csv")

df = pd.read_csv(chemin_fichier)

# Sidebar pour le chargement des données
st.sidebar.title("Source de données")
source_option = st.sidebar.radio(
    "Choisir la source de données:",
    ["Données santé mentale des étudiants", "Télécharger un fichier CSV"]
)

# Initialiser la connexion DuckDB
conn = duckdb.connect(database=':memory:', read_only=False)

# Obtenir les données
if source_option == "Données santé mentale des étudiants":
    df = pd.read_csv(chemin_fichier)
    st.sidebar.success("Données santé mentale des étudiants chargées!")
    
    # Enregistrer les données dans DuckDB
    conn.execute("CREATE TABLE IF NOT EXISTS mental_health AS SELECT * FROM df")
    
else:
    uploaded_file = st.sidebar.file_uploader("Télécharger un fichier CSV", type=["csv"])
    if uploaded_file is not None:
        # Sauvegarder temporairement le fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # Créer une table à partir du CSV avec DuckDB
        conn.execute(f"CREATE TABLE IF NOT EXISTS mental_health AS SELECT * FROM read_csv_auto('{tmp_path}')")
        
        # Charger les données pour affichage
        df = conn.execute("SELECT * FROM mental_health").fetchdf()
        st.sidebar.success(f"{len(df)} étudiants chargés!")
        
        # Supprimer le fichier temporaire
        os.unlink(tmp_path)
    else:
        st.info("Veuillez télécharger un fichier CSV ou utiliser les données de santé mentale fournies.")
        st.stop()

# Afficher un aperçu des données
st.subheader("Aperçu des données")
st.dataframe(df.head(10))

# Statistiques générales
st.header("Statistiques générales")

# Utiliser DuckDB pour les statistiques de santé mentale
stats_generales = conn.execute("""
  SELECT 
        COUNT(*) as total_students,
        ROUND(AVG(Age), 2) as average_age,
        SUM(CASE WHEN "Do you have Depression?" = 'Yes' THEN 1 ELSE 0 END) as total_depression,
        ROUND(100.0 * SUM(CASE WHEN "Do you have Depression?" = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_depression,
        SUM(CASE WHEN "Do you have Anxiety?" = 'Yes' THEN 1 ELSE 0 END) as total_anxiety,
        ROUND(100.0 * SUM(CASE WHEN "Do you have Anxiety?" = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_anxiety,
        SUM(CASE WHEN "Do you have Panic attack?" = 'Yes' THEN 1 ELSE 0 END) as total_panic,
        ROUND(100.0 * SUM(CASE WHEN "Do you have Panic attack?" = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_panic
    FROM mental_health
""").fetchdf()
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total étudiants", stats_generales["total_students"][0])
col2.metric("Âge moyen", stats_generales["average_age"][0])
col3.metric("Dépression", f"{stats_generales['pct_depression'][0]}%")
col4.metric("Anxiété", f"{stats_generales['pct_anxiety'][0]}%")
col5.metric("Panic attack", f"{stats_generales['pct_panic'][0]}%")


# Création d'un graphique
st.header("Carte de chaleur : santé mentale par cours (%)")


# Récupérer les données depuis DuckDB avec pourcentages
mental_health_par_cours = conn.execute("""
    SELECT 
        "What is your course?" as cours,
        ROUND(100.0 * SUM(CASE WHEN "Do you have Depression?" = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_depression,
        ROUND(100.0 * SUM(CASE WHEN "Do you have Anxiety?" = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_anxiety,
        ROUND(100.0 * SUM(CASE WHEN "Do you have Panic attack?" = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_panic
    FROM mental_health
    GROUP BY "What is your course?"
    ORDER BY cours
""").fetchdf()

# Transformer les données pour Plotly
df_heatmap = mental_health_par_cours.melt(
    id_vars=['cours'], 
    value_vars=['pct_depression','pct_anxiety','pct_panic'],
    var_name='Problème',
    value_name='% étudiants'
)

# Remplacer les noms pour plus de clarté
df_heatmap['Problème'] = df_heatmap['Problème'].replace({
    'pct_depression': 'Dépression',
    'pct_anxiety': 'Anxiété',
    'pct_panic': 'Panic attack'
})

# --- FILTRES INTERACTIFS ---
# Filtrer par cours
tous_les_cours = df_heatmap['cours'].unique()
cours_selectionnes = st.multiselect(
    "Sélectionner les cours à afficher :", 
    options=tous_les_cours,
    default=tous_les_cours  # par défaut tous les cours
)

# Filtrer par problème
tous_les_problemes = df_heatmap['Problème'].unique()
problemes_selectionnes = st.multiselect(
    "Sélectionner les problèmes à afficher :", 
    options=tous_les_problemes,
    default=tous_les_problemes  # par défaut tous les problèmes
)

# Appliquer les filtres
df_filtre = df_heatmap[
    (df_heatmap['cours'].isin(cours_selectionnes)) &
    (df_heatmap['Problème'].isin(problemes_selectionnes))
]

# Créer la heatmap filtrée
if not df_filtre.empty:
    fig = px.imshow(
        df_filtre.pivot(index='cours', columns='Problème', values='% étudiants'),
        color_continuous_scale='Reds',
        text_auto=True,
        aspect="auto"
    )

    fig.update_layout(
        xaxis_title='Problème',
        yaxis_title='Cours',
        yaxis=dict(tickangle=0)
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Aucun résultat pour les filtres sélectionnés.")

# -------------------------
# 1️⃣ Taux d’anxiété / dépression / panic attack par sexe
# -------------------------
st.header("Taux de problèmes par sexe (%)")

# Filtre : quels problèmes afficher
problemes_selection = st.multiselect(
    "Sélectionner les problèmes à afficher :",
    ["Dépression", "Anxiété", "Panic attack"],
    default=["Dépression", "Anxiété", "Panic attack"],
    key="graph1_problemes"  # clé unique pour éviter doublons
)

# Préparer dataframe pour le graphique
stats_sexe = df.groupby("Choose your gender").agg({
    "Do you have Depression?": lambda x: round(100*(x=="Yes").sum()/len(x),2),
    "Do you have Anxiety?": lambda x: round(100*(x=="Yes").sum()/len(x),2),
    "Do you have Panic attack?": lambda x: round(100*(x=="Yes").sum()/len(x),2)
}).reset_index()

# Créer graphique barres horizontales
fig_sexe = go.Figure()
colors_map = {"Dépression":"purple","Anxiété":"orange","Panic attack":"red"}

for prob in problemes_selection:
    col_name = {
        "Dépression": "Do you have Depression?",
        "Anxiété": "Do you have Anxiety?",
        "Panic attack": "Do you have Panic attack?"
    }[prob]
    
    fig_sexe.add_trace(go.Bar(
        y=stats_sexe["Choose your gender"],
        x=stats_sexe[col_name],
        name=prob,
        orientation='h',
        text=stats_sexe[col_name].apply(lambda x: f"{x}%"),
        textposition='auto',
        marker_color=colors_map[prob]
    ))

fig_sexe.update_layout(
    xaxis_title='% d’étudiants',
    yaxis_title='Genre',
    barmode='group'
)

st.plotly_chart(fig_sexe, use_container_width=True)