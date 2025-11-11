import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from io import BytesIO

# ===========================================================
# 🧩 Load all trained components
# ===========================================================
@st.cache_resource
def load_components():
    model = joblib.load("best_model.pkl")
    scaler = joblib.load("scaler.pkl")
    encoder = joblib.load("label_encoder.pkl")
    with open("top_genes.json", "r") as f:
        top_genes = json.load(f)
    return model, scaler, encoder, top_genes

# ===========================================================
# 🧬 App Setup
# ===========================================================
st.set_page_config(page_title="🧬 Leukemia Classifier", layout="wide")
st.title("🧬 Leukemia Classification from Gene Expression")
st.write("Predict **ALL / AML / Healthy** from uploaded gene expression data with final medical-style summary.")

# ===========================================================
# 🔄 Load components
# ===========================================================
try:
    model, scaler, encoder, top_genes = load_components()
    st.success("✅ Model, scaler, and encoder loaded successfully!")
except Exception as e:
    st.error(f"⚠️ Error loading model/scaler: {e}")
    st.stop()

# ===========================================================
# 📥 File Upload Section
# ===========================================================
st.header("📁 Upload CSV or Excel File")
uploaded_file = st.file_uploader("Upload your file containing gene expressions", type=["csv", "xlsx"])

# ===========================================================
# ✍️ Manual Input Option
# ===========================================================
st.header("✍️ Or Enter Gene Expression Manually")
manual_input = {}
cols = st.columns(3)
for i, gene in enumerate(top_genes[:9]):  # Only first 9 genes for manual simplicity
    with cols[i % 3]:
        manual_input[gene] = st.number_input(f"{gene} expression", value=0.0)
manual_df = pd.DataFrame([manual_input])

# ===========================================================
# ⚙️ Main Processing Logic
# ===========================================================
if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write(f"✅ Loaded {df.shape[0]} samples, {df.shape[1]} features.")

    has_label = "Diagnosis" in df.columns
    if has_label:
        y_true = df["Diagnosis"]
        df = df.drop(columns=["Diagnosis"])

    # Handle missing/extra genes
    missing_cols = [g for g in top_genes if g not in df.columns]
    extra_cols = [c for c in df.columns if c not in top_genes]
    for col in missing_cols:
        df[col] = 0
    df_input = df[top_genes]

    if missing_cols:
        st.warning(f"ℹ️ Filled {len(missing_cols)} missing genes with 0. Ignored {len(extra_cols)} extras.")

    # Scale + Predict
    df_scaled = scaler.transform(df_input)
    preds = model.predict(df_scaled)
    probs = model.predict_proba(df_scaled)
    conf = np.max(probs, axis=1) * 100
    pred_labels = encoder.inverse_transform(preds)

    # Compile Results
    results = df_input.copy()
    results["Predicted"] = pred_labels
    results["Confidence (%)"] = conf.round(2)

    # ===========================================================
    # 📊 Evaluation if Labels Present
    # ===========================================================
    if has_label:
        acc = accuracy_score(y_true, pred_labels)
        st.success(f"🎯 Model Accuracy on uploaded data: {acc*100:.2f}%")
        st.text("Classification Report:")
        st.text(classification_report(y_true, pred_labels))

        cm = confusion_matrix(y_true, pred_labels, labels=encoder.classes_)
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=encoder.classes_, yticklabels=encoder.classes_)
        plt.xlabel("Predicted")
        plt.ylabel("True")
        plt.title("Confusion Matrix")
        st.pyplot(fig)

    # ===========================================================
    # 🔍 Final Declaration / Summary Section
    # ===========================================================
    st.header("🩺 Final Diagnostic Declaration")

    summary = results["Predicted"].value_counts().to_dict()
    most_common = max(summary, key=summary.get)
    avg_conf = results["Confidence (%)"].mean()

    st.write("### 🧾 Summary of Predictions:")
    st.dataframe(results[["Predicted", "Confidence (%)"]])

    st.markdown(f"""
    **🧬 Predominant Diagnosis:** `{most_common}`  
    **📈 Average Confidence:** `{avg_conf:.2f}%`  
    """)

    if most_common == "ALL":
        st.success("🩸 Final Declaration: **Acute Lymphoblastic Leukemia (ALL)** — detected in majority of samples.")
    elif most_common == "AML":
        st.warning("🧠 Final Declaration: **Acute Myeloid Leukemia (AML)** — detected in majority of samples.")
    else:
        st.info("💚 Final Declaration: **Healthy Gene Expression Pattern** — no leukemia indications detected.")

    # ===========================================================
    # 📈 Gene Importance Visualization
    # ===========================================================
    if hasattr(model, "feature_importances_"):
        imp = pd.Series(model.feature_importances_, index=top_genes).sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(8, 4))
        sns.barplot(x=imp[:20], y=imp.index[:20], palette="mako")
        plt.title("Top 20 Gene Importances")
        st.pyplot(fig)

    # ===========================================================
    # 📥 Download Report
    # ===========================================================
    buffer = BytesIO()
    results.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        "📥 Download Predictions Report (.xlsx)",
        data=buffer,
        file_name="leukemia_predictions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # ===========================================================
    # 🔄 Auto Retrain Option
    # ===========================================================
    if has_label and st.button("🔄 Retrain model with new labeled data"):
        st.info("Training new model with uploaded data...")
        X = scaler.fit_transform(df_input)
        y_enc = encoder.fit_transform(y_true)
        new_model = RandomForestClassifier(n_estimators=400, random_state=42)
        new_model.fit(X, y_enc)
        joblib.dump(new_model, "best_model.pkl")
        joblib.dump(scaler, "scaler.pkl")
        joblib.dump(encoder, "label_encoder.pkl")
        st.success("✅ Model retrained and saved successfully!")

else:
    st.write("⬆️ Upload a CSV/XLSX file or enter gene values manually above.")

# ===========================================================
# ✍️ Manual Input Prediction
# ===========================================================
if st.button("🔍 Predict from Manual Input"):
    try:
        df_scaled = scaler.transform(manual_df[top_genes])
        pred = model.predict(df_scaled)
        prob = model.predict_proba(df_scaled)[0]
        label = encoder.inverse_transform(pred)[0]

        st.success(f"🧾 Prediction: **{label}** ({prob.max()*100:.2f}% confidence)")
        conf_df = pd.DataFrame({"Class": encoder.classes_, "Probability (%)": prob * 100}).sort_values("Probability (%)", ascending=False)
        st.bar_chart(conf_df.set_index("Class"))
    except Exception as e:
        st.error(f"❌ Error: {e}")
