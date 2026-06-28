## Assignment Summary: Telco Churn Prediction and Tenure Regression

This assignment covered a comprehensive machine learning workflow, from foundational concepts to model deployment and advanced interpretability techniques, applied to two distinct problems: Telco Customer Churn Prediction (classification) and Customer Tenure Prediction (regression).

### Section 1: Decision Tree Building Blocks
*   **Manual Implementations:** We started by implementing core decision tree algorithms from scratch, including Gini Impurity, Shannon Entropy, and Information Gain. This reinforced the fundamental math behind how trees make splitting decisions.

### Section 2: Bias-Variance Tradeoff
*   **Overfitting Demonstration:** We observed the bias-variance tradeoff by training decision trees with varying `max_depth` on a synthetic dataset (`make_moons`). This highlighted how unconstrained trees can perfectly fit training data (100% accuracy) but fail to generalize to unseen data due to high variance and overfitting.

### Section 3: Data Prep & The Accuracy Trap
*   **Data Cleaning:** The raw Telco dataset was cleaned by handling a data quality issue in `TotalCharges` (whitespace converted to NaN, then imputed with the median). The `Churn` target variable was encoded to binary (0/1).
*   **Naive Model & Metrics:** An unconstrained Decision Tree was trained on the cleaned data, exposing the "accuracy trap" – high accuracy (due to class imbalance) masking poor performance (low recall) on the minority class (churners). We then computed Precision, Recall, and F1-score manually to understand the true business impact.
*   **Model Pruning:** We used `GridSearchCV` to find an optimal `max_depth` for the Decision Tree, significantly reducing overfitting and improving test set performance. A business cost analysis clearly demonstrated the financial benefits of the pruned model over the naive, overfit one, emphasizing the importance of minimizing False Negatives.

### Section 4: Ensembles
*   **Bootstrap Sampling:** We implemented bootstrap sampling from scratch, which is the cornerstone of ensemble methods like Bagging and Random Forest.
*   **Bagging vs. Random Forest:** We compared `BaggingClassifier` and `RandomForestClassifier`, highlighting that Random Forests' feature subsampling at each split helps decorrelate trees, leading to better generalization and higher AUROC scores.

### Section 5: Boosting
*   **XGBoost Regularisation:** We explored how XGBoost's regularization parameters (`max_depth`, `learning_rate`, `n_estimators`) control the bias-variance tradeoff. We observed how different configurations lead to varying levels of overfitting or underfitting.
*   **Hyperparameter Tuning:** A `GridSearchCV` was performed to optimize XGBoost hyperparameters, followed by a more efficient Bayesian Optimization using Optuna, showcasing advanced tuning techniques and identifying the most impactful parameters for F1-score.

### Section 6: Pipelines
*   **ColumnTransformer:** A `ColumnTransformer` was built to handle mixed data types (numeric and categorical) with appropriate preprocessing steps (imputation, scaling, one-hot encoding). The importance of fitting the preprocessor only on training data to prevent data leakage was thoroughly discussed.
*   **SMOTE Leakage:** We deliberately demonstrated how applying SMOTE *before* cross-validation leads to severe data leakage and artificially inflated performance metrics. This was then corrected by integrating SMOTE within an `ImbPipeline`, ensuring a leak-proof workflow.

### Section 7: Interpretability
*   **Full Production Pipeline:** A complete, leak-proof `ImbPipeline` integrating preprocessing, SMOTE, and a `RandomForestClassifier` was built and evaluated.
*   **Global SHAP:** SHAP (SHapley Additive exPlanations) was used to identify the top 3 global features driving churn risk across all customers (`Contract_Month-to-month`, `InternetService_Fiber optic`, `MonthlyCharges`), providing actionable insights for retention strategies.
*   **Local SHAP:** A SHAP waterfall plot was generated for a single, high-confidence churning customer (True Positive), providing a granular explanation of *why* that specific customer was predicted to churn, which is invaluable for targeted interventions.

### Section 8: Deployment
*   **Model Serialization:** The trained `full_pipeline` model was saved to disk using `joblib` and then reloaded to simulate a production environment, verifying that it produced identical predictions.
*   **Model Card:** A comprehensive Model Card was drafted, detailing the model's purpose, architecture, expected metrics, top predictive features, known limitations, and retraining policy, ensuring proper documentation and responsible deployment.

### Part 2: Regression with Tree Models
*   **Tenure Prediction:** We shifted focus to predicting `tenure` (customer duration) as a regression problem.
*   **Decision Tree Regressor:** An unconstrained `DecisionTreeRegressor` was trained and evaluated using RMSE, MAE, and R², and the MAE was interpreted in the context of a retention campaign.
*   **XGBoost Regressor:** An `XGBRegressor` was trained with regularization, demonstrating improved performance over the single Decision Tree, especially in MAE, justifying its complexity for business-critical applications.
*   **Learning Curves & Extrapolation Failure:** Learning curves were plotted to compare the bias-variance characteristics of the regression models. Crucially, we demonstrated and explained the fundamental limitation of tree-based models: their inability to extrapolate beyond the range of `y_train` values, making them unsuitable for tasks like forecasting CLTV for new, higher-value customer segments.