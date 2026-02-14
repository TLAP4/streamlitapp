import streamlit as st
import duckdb
import pandas as pd
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
        st.info("Veuillez télécharger un fichier CSV ou utiliser les données de démonstration.")
        st.stop()

# Afficher un aperçu des données
st.subheader("Aperçu des données")
st.dataframe(df.head(10))

# Statistiques générales
st.header("Statistiques générales")

# Utiliser DuckDB pour les statistiques de survie
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