import pandas as pd
import numpy as np
from scipy import stats

def permutation_p_value(group1, group2, iterations=10000):
    combined = np.concatenate([group1, group2])
    n1 = len(group1)
    # Observe the actual absolute difference in means
    obs_diff = np.abs(np.mean(group1) - np.mean(group2))
    
    count = 0
    for _ in range(iterations):
        # Shuffle the data and split into random groups
        np.random.shuffle(combined)
        new_g1 = combined[:n1]
        new_g2 = combined[n1:]
        
        # Calculate random difference
        if np.abs(np.mean(new_g1) - np.mean(new_g2)) >= obs_diff:
            count += 1
            
    return count / iterations

def analyze_dynamic_performance(file_s, file_ns, output_file):
    # Load the combined dynamic metric files
    df_s = pd.read_csv(file_s)
    df_ns = pd.read_csv(file_ns)
    
    # Define the metrics to analyze
    metrics = ['Avg_RT', 'Avg_MT', 'Avg_Dynamic_Jerk', 'Total_Orbs_Hit', 'Success_Rate']
    results = []
    
    n1, n2 = len(df_s), len(df_ns)
    df_freedom = n1 + n2 - 2
    j_correction = 1 - (3 / (4 * df_freedom - 1)) 
    
    for m in metrics:
        s_vals = df_s[m].values
        ns_vals = df_ns[m].values
        
        m1, sd1 = np.mean(s_vals), np.std(s_vals, ddof=1)
        m2, sd2 = np.mean(ns_vals), np.std(ns_vals, ddof=1)
        
        # Welch's T-test
        t_stat, p_val_t = stats.ttest_ind(s_vals, ns_vals, equal_var=False)
        
        # Permutation Test (10,000 iterations)
        p_val_perm = permutation_p_value(s_vals, ns_vals)
        
        # Effect Sizes
        pooled_sd = np.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / df_freedom)
        cohen_d = (m2 - m1) / pooled_sd if pooled_sd != 0 else 0
        hedges_g = cohen_d * j_correction
        
        results.append({
            'Metric': m,
            'Sport_Mean': round(m1, 4),
            'NS_Mean': round(m2, 4),
            'p_val_t_test': round(p_val_t, 4),
            'p_val_permutation': round(p_val_perm, 4),
            'Cohen_d': round(cohen_d, 4),
            'Hedges_g': round(hedges_g, 4)
        })
    
    # Create summary table and export
    summary_df = pd.DataFrame(results)
    summary_df.to_csv(output_file, index=False)
    print("--- Dynamic Performance Comparison with Permutations ---")
    print(summary_df)
    return summary_df

# Execute
analyze_dynamic_performance('S_combined_dynamic_metrics.csv', 
                            'NS_combined_dynamic_metrics.csv', 
                            'dynamic_analysis_permutation_results.csv')