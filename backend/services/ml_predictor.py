import os
import uuid
import hashlib
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import sqlalchemy as sa
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, confusion_matrix
from scipy.stats import pearsonr

from backend.models import RecoveryTrainingExample, RecoveryModelVersion
from backend.services.feature_engine import FEATURE_SCHEMA_VERSION

ARTIFACT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "artifacts", "models")
os.makedirs(ARTIFACT_DIR, exist_ok=True)

NUMERIC_FEATURES = [
    "amount_due", "outstanding_amount", "obligation_age_seconds", 
    "attempt_count", "failed_attempt_count", "captured_attempt_count", 
    "last_attempt_age_seconds", "time_since_last_failure_seconds",
    "previous_obligation_count", "previous_success_count", 
    "previous_failure_count", "historical_success_rate", 
    "historical_average_amount", "hour_of_day", "day_of_week"
]

CATEGORICAL_FEATURES = [
    "obligation_state", "failure_category", "failure_code", 
    "failure_reason", "payment_method", "candidate_action"
]

def _build_pipeline():
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, NUMERIC_FEATURES),
            ('cat', categorical_transformer, CATEGORICAL_FEATURES)
        ])
    return Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(random_state=42, max_iter=1000))
    ])

async def train_model(db: AsyncSession, dataset_version: int) -> RecoveryModelVersion:
    # 1. Load Data
    stmt = select(RecoveryTrainingExample).where(RecoveryTrainingExample.dataset_version == dataset_version)
    result = await db.execute(stmt)
    examples = result.scalars().all()
    
    if not examples:
        raise ValueError(f"No training data found for dataset {dataset_version}")
        
    records = []
    metadata = []
    
    for ex in examples:
        rec = ex.features.copy()
        
        # EXPLICIT LEAKAGE PREVENTION: Extract and remove _metadata
        meta = rec.pop('_metadata', {})
        
        rec['candidate_action'] = ex.candidate_action
        rec['outcome'] = ex.outcome
        
        records.append(rec)
        meta['candidate_action'] = ex.candidate_action
        meta['outcome'] = ex.outcome
        meta['amount_due'] = rec['amount_due'] # Needed for policy eval
        meta['failure_category'] = rec['failure_category'] # For diagnostics
        metadata.append(meta)
        
    df = pd.DataFrame(records)
    df_meta = pd.DataFrame(metadata)
    
    # 2. Synthetic Data Quality Diagnostics
    print("\n--- SYNTHETIC DATA QUALITY DIAGNOSTICS ---")
    print(f"Total records: {len(df)}")
    print(f"Unique contexts: {df_meta['context_id'].nunique()}")
    print(f"Action balance:\n{df['candidate_action'].value_counts(normalize=True)}")
    print(f"Outcome balance:\n{df['outcome'].value_counts(normalize=True)}")
    print(f"Failure category distribution:\n{df_meta['failure_category'].value_counts(normalize=True)}")
    
    df_meta['true_probability_uplift'] = pd.to_numeric(df_meta['true_probability_uplift'], errors='coerce')
    print(f"\nMean p_wait: {df_meta['p_wait'].mean():.4f}")
    print(f"Mean p_link: {df_meta['p_link'].mean():.4f}")
    print(f"Mean true probability uplift: {df_meta['true_probability_uplift'].mean():.4f}")
    print(f"Uplift std dev: {df_meta['true_probability_uplift'].std():.4f}")
    
    # 3. Model Feature Audit & Leakage Check
    print("\n--- LEAKAGE AUDIT ---")
    excluded = ['p_wait', 'p_link', 'true_probability_uplift', 'Y_wait', 'Y_link', 'observed_potential_outcome_difference', 'context_id']
    leaked = [col for col in excluded if col in df.columns]
    
    if leaked:
        print(f"FATAL: LEAKAGE DETECTED. Ground truth columns in feature matrix: {leaked}")
        raise ValueError("Data Leakage Detected")
    else:
        print("PASS: p_wait, p_link, and potential outcomes successfully excluded.")
        print("PASS: context_id excluded.")
        
    print("\nFeature Columns Used:")
    print("Numerical:", NUMERIC_FEATURES)
    print("Categorical:", CATEGORICAL_FEATURES)
    
    # 4. Context-Level Train/Test Split
    unique_contexts = df_meta['context_id'].unique()
    np.random.seed(42)
    np.random.shuffle(unique_contexts)
    
    train_size = int(len(unique_contexts) * 0.8)
    train_contexts = set(unique_contexts[:train_size])
    test_contexts = set(unique_contexts[train_size:])
    
    is_train = df_meta['context_id'].isin(train_contexts)
    is_test = df_meta['context_id'].isin(test_contexts)
    
    df_train = df[is_train].copy()
    df_test = df[is_test].copy()
    
    y_train = df_train.pop('outcome')
    y_test = df_test.pop('outcome')
    
    print(f"PASS: Train/Test splits are strictly context-disjoint. Train contexts: {len(train_contexts)}, Test contexts: {len(test_contexts)}")
    
    # 5. Train Pipeline
    pipeline = _build_pipeline()
    pipeline.fit(df_train, y_train)
    
    # 6. Base Model Metrics (on Outcome prediction)
    y_pred_proba = pipeline.predict_proba(df_test)[:, 1]
    y_pred = pipeline.predict(df_test)
    
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    pr_auc = average_precision_score(y_test, y_pred_proba)
    brier = brier_score_loss(y_test, y_pred_proba)
    cm = confusion_matrix(y_test, y_pred).tolist()
    
    print("\n--- OUTCOME MODEL PERFORMANCE (BASELINE) ---")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"PR-AUC:  {pr_auc:.4f}")
    print(f"Brier:   {brier:.4f}")
    
    # 7. Uplift and Policy Evaluation
    print("\n--- UPLIFT & POLICY EVALUATION (SIMULATED) ---")
    
    # We need to pair the test set back together for policy eval
    df_test_eval = df_test.copy()
    df_test_eval['predicted_prob'] = y_pred_proba
    df_test_eval['context_id'] = df_meta.loc[is_test, 'context_id']
    df_test_eval['true_uplift'] = df_meta.loc[is_test, 'true_probability_uplift']
    df_test_eval['amount_due'] = df_meta.loc[is_test, 'amount_due']
    df_test_eval['actual_outcome'] = y_test
    
    # Pivot to wide format
    eval_pivot = df_test_eval.pivot_table(
        index=['context_id', 'true_uplift', 'amount_due'],
        columns='candidate_action',
        values=['predicted_prob', 'actual_outcome']
    ).reset_index()
    
    # Flatten columns
    eval_pivot.columns = ['_'.join(col).strip('_') for col in eval_pivot.columns.values]
    
    # Check if both actions exist for all test contexts
    if eval_pivot.isnull().any().any():
        print("Warning: Missing action pairs in some test contexts. Dropping them.")
        eval_pivot = eval_pivot.dropna()
        
    eval_pivot['predicted_uplift'] = eval_pivot['predicted_prob_PAYMENT_LINK'] - eval_pivot['predicted_prob_WAIT']
    eval_pivot['observed_potential_outcome_difference'] = eval_pivot['actual_outcome_PAYMENT_LINK'] - eval_pivot['actual_outcome_WAIT']
    
    # Uplift Metrics
    mae = np.mean(np.abs(eval_pivot['predicted_uplift'] - eval_pivot['true_uplift']))
    rmse = np.sqrt(np.mean((eval_pivot['predicted_uplift'] - eval_pivot['true_uplift'])**2))
    corr, _ = pearsonr(eval_pivot['predicted_uplift'], eval_pivot['true_uplift'])
    
    print(f"Uplift MAE:  {mae:.4f}")
    print(f"Uplift RMSE: {rmse:.4f}")
    print(f"Uplift Corr: {corr:.4f}")
    
    # Policy Evaluation
    eval_pivot['action_always_wait'] = 'WAIT'
    eval_pivot['action_learned'] = np.where(eval_pivot['predicted_uplift'] > 0, 'PAYMENT_LINK', 'WAIT')
    eval_pivot['action_oracle'] = np.where(eval_pivot['true_uplift'] > 0, 'PAYMENT_LINK', 'WAIT')
    
    def get_realized_value(row, policy_col):
        action = row[policy_col]
        return row[f'actual_outcome_{action}'] * row['amount_due']
        
    val_always_wait = eval_pivot.apply(lambda r: get_realized_value(r, 'action_always_wait'), axis=1).sum()
    val_learned = eval_pivot.apply(lambda r: get_realized_value(r, 'action_learned'), axis=1).sum()
    val_oracle = eval_pivot.apply(lambda r: get_realized_value(r, 'action_oracle'), axis=1).sum()
    
    learned_incremental = val_learned - val_always_wait
    regret = val_oracle - val_learned
    
    print(f"\nPolicy Value (Always WAIT): ${val_always_wait:,.2f}")
    print(f"Policy Value (Learned):     ${val_learned:,.2f}")
    print(f"Policy Value (Oracle):      ${val_oracle:,.2f}")
    print(f"Learned Incremental Value:  ${learned_incremental:,.2f}")
    print(f"Policy Regret (Oracle - L): ${regret:,.2f}")
    
    print("\n--- CONCLUSION ---")
    if roc_auc > 0.65 and corr > 0.3:
        print("The Logistic Regression model has demonstrated meaningful predictive structure for uplift in this synthetic environment.")
    else:
        print("The model struggles to capture the underlying structure. Nonlinear interactions may be required.")
        
    # 8. Save Artifact
    version_id = f"v{int(pd.Timestamp.now().timestamp())}"
    artifact_path = os.path.join(ARTIFACT_DIR, f"model_{version_id}.joblib")
    joblib.dump(pipeline, artifact_path)
    
    with open(artifact_path, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
        
    await db.execute(sa.text("UPDATE recovery_model_versions SET active = false"))
    
    metrics = {
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "brier_score": float(brier),
        "uplift_mae": float(mae),
        "uplift_rmse": float(rmse),
        "uplift_corr": float(corr),
        "policy_always_wait": float(val_always_wait),
        "policy_learned": float(val_learned),
        "policy_oracle": float(val_oracle),
        "regret": float(regret)
    }
    
    model_record = RecoveryModelVersion(
        version=version_id,
        dataset_version=dataset_version,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        algorithm="LogisticRegression",
        metrics=metrics,
        artifact_uri=artifact_path,
        artifact_checksum=checksum,
        active=True
    )
    
    db.add(model_record)
    await db.commit()
    await db.refresh(model_record)
    
    return model_record

_loaded_model = None
_loaded_version = None

def get_model(version: str, artifact_uri: str):
    global _loaded_model, _loaded_version
    if _loaded_version == version and _loaded_model is not None:
        return _loaded_model
    if not os.path.exists(artifact_uri):
        raise ValueError(f"Model artifact not found at {artifact_uri}")
    _loaded_model = joblib.load(artifact_uri)
    _loaded_version = version
    return _loaded_model

def predict(model_record: RecoveryModelVersion, features: Dict[str, Any], candidate_action: str) -> float:
    pipeline = get_model(model_record.version, model_record.artifact_uri)
    req = features.copy()
    req.pop('_metadata', None)
    req['candidate_action'] = candidate_action
    
    df = pd.DataFrame([req])
    proba = pipeline.predict_proba(df)[0, 1]
    return float(proba)
