import pandas as pd
import numpy as np
from scipy import stats

def analyze_dynamic_performance(file_s, file_ns, output_file):
    # Load the combined dynamic metric files
    df_s = pd.read_csv(file_s)
    df_ns = pd.read_csv(file_ns)
    
    # Define the metrics to analyze
    metrics = ['Avg_RT', 'Avg_MT', 'Avg_Dynamic_Jerk', 'Total_Orbs_Hit', 'Success_Rate']
    results = []
    
    n1, n2 = len(df_s), len(df_ns)
    df_freedom = n1 + n2 - 2
    j_correction = 1 - (3 / (4 * df_freedom - 1)) # Hedges' g correction factor
    
    for m in metrics:
        # Extract values
        s_vals = df_s[m]
        ns_vals = df_ns[m]
        
        # Calculate Descriptive Stats
        m1, sd1 = s_vals.mean(), s_vals.std()
        m2, sd2 = ns_vals.mean(), ns_vals.std()
        
        # Welch's T-test (p-value) - chosen for unequal group sizes and variances
        t_stat, p_val = stats.ttest_ind(s_vals, ns_vals, equal_var=False)
        
        # Cohen's d (Magnitude of difference)
        pooled_sd = np.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / df_freedom)
        cohen_d = (m2 - m1) / pooled_sd if pooled_sd != 0 else 0
        
        # Hedges' g (Corrected for small sample bias)
        hedges_g = cohen_d * j_correction
        
        results.append({
            'Metric': m,
            'Sport_Mean': round(m1, 4),
            'NS_Mean': round(m2, 4),
            'p_value': round(p_val, 4),
            'Cohen_d': round(cohen_d, 4),
            'Hedges_g': round(hedges_g, 4)
        })
    
    # Create summary table and export
    summary_df = pd.DataFrame(results)
    summary_df.to_csv(output_file, index=False)
    print("--- Dynamic Performance Comparison ---")
    print(summary_df)
    return summary_df

# Execute
analyze_dynamic_performance('S_combined_dynamic_metrics.csv', 
                            'NS_combined_dynamic_metrics.csv', 
                            'dynamic_analysis_summary.csv')