import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

# ==========================================
# CONFIGURATION & FILE PATHS
# ==========================================
# Pointing to the Sample_Data folder relative to the Data_Analysis folder
DATA_DIR = Path("../Sample_Data")

# Define the mock files based on the GitHub repository structure
FILES = {
    'Static': (DATA_DIR / 'sport_mock_static_data.csv', DATA_DIR / 'nonsport_mock_static_data.csv'),
    'Dual': (DATA_DIR / 'sport_mock_dual_data.csv', DATA_DIR / 'nonsport_mock_dual_data.csv'),
    'Dynamic': (DATA_DIR / 'sport_mock_dynamic_data.csv', DATA_DIR / 'nonsport_mock_dynamic_data.csv')
}

# ==========================================
# STATISTICAL FUNCTIONS
# ==========================================
def permutation_p_value(group1, group2, iterations=10000):
    """
    Calculates the p-value using a non-parametric permutation test.
    Useful for objective kinematic data that may violate assumptions of normality.
    """
    combined = np.concatenate([group1, group2])
    n1 = len(group1)
    obs_diff = np.abs(np.mean(group1) - np.mean(group2))
    
    count = 0
    for _ in range(iterations):
        np.random.shuffle(combined)
        new_g1 = combined[:n1]
        new_g2 = combined[n1:]
        
        # Count how often random shuffling produces a difference larger than the real data
        if np.abs(np.mean(new_g1) - np.mean(new_g2)) >= obs_diff:
            count += 1
            
    return count / iterations

def analyze_metrics(s_vals, ns_vals, task_name, metric_name):
    """Performs Welch's T-test, Permutation Test, and calculates Hedges' g."""
    n1, n2 = len(s_vals), len(ns_vals)
    df_freedom = n1 + n2 - 2
    j_correction = 1 - (3 / (4 * df_freedom - 1)) # Small sample size correction
    
    m1, sd1 = np.mean(s_vals), np.std(s_vals, ddof=1)
    m2, sd2 = np.mean(ns_vals), np.std(ns_vals, ddof=1)
    
    # Parametric Test (Unequal variance assumption)
    t_stat, p_val_t = stats.ttest_ind(s_vals, ns_vals, equal_var=False)
    
    # Non-Parametric Test
    p_val_perm = permutation_p_value(s_vals, ns_vals)
    
    # Effect Sizes
    pooled_sd = np.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / df_freedom)
    cohen_d = (m2 - m1) / pooled_sd if pooled_sd != 0 else 0
    hedges_g = cohen_d * j_correction
    
    return {
        'Task': task_name,
        'Metric': metric_name,
        'Sport_Mean': round(m1, 4),
        'NonSport_Mean': round(m2, 4),
        'p_val_t_test': round(p_val_t, 4),
        'p_val_permutation': round(p_val_perm, 4),
        'Hedges_g': round(hedges_g, 4)
    }

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    results = []
    
    # Analyze Static and Dual Tasks (Postural Sway)
    sway_metrics = ['RMS', 'NPL', 'P2P_Total', 'Jerk']
    for task in ['Static', 'Dual']:
        try:
            df_s = pd.read_csv(FILES[task][0])
            df_ns = pd.read_csv(FILES[task][1])
            
            # Aggregate to ensure 1 data point per participant
            s_means = df_s.groupby('Participant_ID')[sway_metrics].mean()
            ns_means = df_ns.groupby('Participant_ID')[sway_metrics].mean()
            
            for m in sway_metrics:
                if m in s_means.columns and m in ns_means.columns:
                    res = analyze_metrics(s_means[m].values, ns_means[m].values, task, m)
                    results.append(res)
        except FileNotFoundError as e:
            print(f"Skipping {task} Sway Analysis: File not found ({e.filename})")

    # Analyze Dynamic Task (Reaching Kinematics)
    dynamic_metrics = ['Avg_RT', 'Avg_MT', 'Avg_Dynamic_Jerk', 'Success_Rate']
    try:
        df_s_dyn = pd.read_csv(FILES['Dynamic'][0])
        df_ns_dyn = pd.read_csv(FILES['Dynamic'][1])
        
        for m in dynamic_metrics:
            if m in df_s_dyn.columns and m in df_ns_dyn.columns:
                res = analyze_metrics(df_s_dyn[m].values, df_ns_dyn[m].values, 'Dynamic', m)
                results.append(res)
    except FileNotFoundError as e:
        print(f"Skipping Dynamic Analysis: File not found ({e.filename})")

    # Export Summary
    if results:
        final_df = pd.DataFrame(results)
        print("=== STATISTICAL ANALYSIS COMPLETE ===")
        print(final_df.to_string(index=False))
        final_df.to_csv("master_statistical_results.csv", index=False)
        print("\nResults exported to 'master_statistical_results.csv'")

if __name__ == "__main__":
    main()