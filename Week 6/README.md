# Probabilistic Models & Bayesian Inference — Assignment Notebook

## Overview

This notebook explores various probabilistic models and Bayesian inference techniques through a series of exercises using the Telco Customer Churn dataset and the Mauna Loa CO₂ dataset. The assignment covers foundational concepts such as MLE, MAP, Full Bayes, sequential updating, Dirichlet-Multinomial distributions, multivariate Gaussians, Probabilistic Graphical Models (Bayesian Networks and MRFs), Gaussian Process Regression, and Markov Chain Monte Carlo (MCMC) for Bayesian Logistic Regression.

## Contents

### Part 1: The Estimation Trinity — MLE, MAP, Full Bayes

- **Objective:** Compare different approaches (Maximum Likelihood Estimation, Maximum A Posteriori, Full Bayesian inference) to estimate churn rates for different customer segments (Month-to-month vs. Two-year contracts).
- **Key Concepts:** Beta-Binomial conjugate prior, effect of prior on posterior with varying sample sizes.
- **Approach:**
    - Extracted customer groups based on contract type.
    - Computed MLE, MAP estimates, and the prior pull
    -  (difference between MAP and MLE).
    - Plotted posterior PDFs and 94% Highest Density Intervals (HDIs).
    - Used Monte Carlo sampling to compute the probability that one group's churn rate is higher than another: P(θ_A > θ_B).
- **Reflections:** Discussed why prior pull is more significant for smaller sample sizes and advocated for Full Bayesian posterior (with HDI) for quantifying uncertainty, especially with limited data. Explored the sample size at which the prior becomes irrelevant.

### Part 2: Sequential Bayesian Updating & Dirichlet-Multinomial

- **Objective:** Illustrate how beliefs are updated sequentially with new data and explore multinomial proportions using the Dirichlet distribution.
- **Key Concepts:** Beta-Binomial sequential updating, Bayesian decision boundaries, Dirichlet-Multinomial distribution, Laplace smoothing.
- **Approach:**
    - Implemented a function to sequentially update Beta posterior parameters with new churn observations.
    - Visualized the evolution of the posterior distribution as more data arrived.
    - Computed a Bayesian decision boundary (P(θ > threshold)) and compared the Bayesian sample size required to reach a decision with a frequentist approach.
    - Applied Dirichlet-Multinomial to model proportions of 3-category contract types.
    - Demonstrated how Dirichlet handles unseen categories (e.g., Biannual) with pseudocounts.
- **Reflections:** Explained why credible intervals are wider for categories with fewer observations. Clarified how the Dirichlet prior allows for non-zero probabilities for unseen events (Laplace smoothing). Discussed how to encode similar prior beliefs from a Beta-Binomial case into a 3-category Dirichlet model.

### Part 3: Multivariate Gaussians — When Features Correlate

- **Objective:** Understand and model multivariate relationships between continuous features using Gaussian distributions.
- **Key Concepts:** Mean vector, covariance matrix, correlation, confidence ellipses, conditional Gaussians, marginalization, condition number.
- **Approach:**
    - Fitted a 2D Gaussian to `tenure` and `MonthlyCharges`.
    - Plotted confidence ellipses (1σ, 2σ, 3σ) to visualize the joint distribution.
    - Computed a conditional distribution P(MonthlyCharges | tenure = 24).
    - Extended to a 3D covariance matrix for `tenure`, `MonthlyCharges`, and `TotalCharges`.
    - Verified marginalization by extracting a 2x2 submatrix and comparing it to the directly fitted 2D covariance.
- **Reflections:** Explained that a large condition number indicates high correlation/near-collinearity among features, which can lead to numerical instability in models. Stated the general rule for marginalizing a Gaussian. Discussed problems caused by including highly correlated features in models and identified Variance Inflation Factor (VIF) as a frequentist diagnostic for this issue.

### Part 4: Probabilistic Graphical Models — Bayesian Networks and MRFs

- **Objective:** Explore directed (Bayesian Networks) and undirected (Markov Random Fields) graphical models to represent relationships between discrete variables.
- **Key Concepts:** Directed Acyclic Graphs (DAGs), conditional probability distributions (CPDs), Variable Elimination, explaining away . Contrasted BNs' ability to answer causal questions with MRFs' focus on associations, and when one might be preferred over the other.

### Part 5: Gaussian Process Regression — Mauna Loa CO₂

- **Objective:** Model and predict the Mauna Loa CO₂ concentration data using Gaussian Process Regression, focusing on kernel design and uncertainty quantification.
- **Key Concepts:** Gaussian Processes (GPs), kernel functions (DotProduct for trend, RBF * ExpSineSquared for seasonality, WhiteKernel for noise), credible bands, extrapolation uncertainty.
- **Approach:**
    - Loaded the Mauna Loa CO₂ dataset.
    - Justified and constructed a composite kernel to capture the trend, seasonal cycle, and noise in the data.
    - Fitted a `GaussianProcessRegressor` to the training data.
    - Plotted the GP posterior mean and 95% credible bands over the full data range.
    - Conducted a gap experiment, removing data from a section and observing the behavior of credible bands.
    - Performed extrapolation beyond the training data and identified the model confidence boundary.
- **Reflections:** Explained the structural difference between GP extrapolation uncertainty (widening credible intervals) and the  of a `DecisionTreeRegressor(max_depth=None)`.

### Part 6: MCMC — Bayesian Logistic Regression

- **Objective:** Implement a Bayesian Logistic Regression model using PyMC and evaluate its performance and convergence characteristics.
- **Key Concepts:** Bayesian Logistic Regression, NUTS sampler, feature scaling, convergence diagnostics (R̂, bulk-ESS), prior sensitivity, Posterior Predictive Checks (PPC), Highest Density Interval (HDI), Confusion Matrix, ROC curve.
- **Approach:**
    - Prepared and scaled features (`tenure`, `MonthlyCharges`) for the logistic regression model.
    - Defined the Bayesian Logistic Regression model in PyMC with Normal priors for intercept and beta coefficients.
    - Sampled from the posterior using NUTS.
    - Performed convergence diagnostics using ArviZ (`az.plot_trace`, `az.summary`) to check R̂ and effective sample size (ESS).
    - Evaluated prior sensitivity by running the model with a tighter prior and comparing posteriors.
    - Generated posterior predictive samples on the test set and constructed a confusion matrix and ROC curve.
    - Compared Bayesian HDI with Frequentist Confidence Intervals (CIs).
    - Saved the MCMC trace using `pickle`.
- **Reflections:** Explained why feature scaling is critical for NUTS performance due to posterior geometry. Described the meaning and interpretation of R̂ and bulk-ESS for assessing MCMC quality. Analyzed prior sensitivity to understand the data's informativeness. Articulated the precise difference in interpretation between Bayesian HDI and Frequentist CI.

## Submission Artefacts

- `Probabilistic_Models_and_Bayesian_Inference.ipynb`: This fully executed notebook with all outputs visible.
- `telco_bayes_lr_v1.pkl`: The PyMC inference data object saved from Part 6, containing the MCMC samples for the Bayesian Logistic Regression model.
- `Reflection(Royas Shakya.pdf)`: A one-page reflection PDF/Markdown providing a concrete example where a fully Bayesian answer would alter a decision compared to an MLE-only approach, explaining the mechanism.

