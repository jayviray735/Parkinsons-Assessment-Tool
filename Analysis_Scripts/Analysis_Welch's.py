import pandas as pd
import numpy as np
from scipy import stats

# Define the specific Participant IDs for the 12/10 split
# This ensures only the correct participants are included in the analysis
sport_ids = [5, 6, 9, 11, 12, 13, 14, 16, 17, 19, 20, 21]
ns_ids = [2, 3, 4, 7, 8, 10, 15, 18, 125, 369]

def run_analysis(file_s, file_ns, task_label):
    # Load the datasets
    df_s = pd.read_csv(file_s)
    df_ns = pd.read_csv(file_ns)
    
    # Filter for the definitive group IDs
    s_filtered = df_s[df_s['Participant_ID'].isin(sport_ids)]
    ns_filtered = df_ns[df_ns['Participant_ID'].isin(ns_ids)]
    
    # Calculate the mean of the 3 trials for each participant
    # This is critical to ensure each person provides only ONE data point for the test
    s_p_means = s_filtered.groupby('Participant_ID')[['RMS', 'NPL', 'P2P_Total']].mean()
    ns_p_means = ns_filtered.groupby('Participant_ID')[['RMS', 'NPL', 'P2P_Total']].mean()
    
    results = []
    n1, n2 = len(s_p_means), len(ns_p_means)
    df = n1 + n2 - 2  # Degrees of Freedom
    j_correction = 1 - (3 / (4 * df - 1))  # Hedges' g correction factor
    
    for metric in ['RMS', 'NPL', 'P2P_Total']:
        m1, sd1 = s_p_means[metric].mean(), s_p_means[metric].std()
        m2, sd2 = ns_p_means[metric].mean(), ns_p_means[metric].std()
        
        # Welch's T-test
        t_stat, p_val = stats.ttest_ind(s_p_means[metric], ns_p_means[metric], equal_var=False)
        
        pooled_sd = np.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / df)
        
        # Cohen'S D
        cohen_d = (m2 - m1) / pooled_sd
        
        # Hedges' g
        g = ((m2 - m1) / pooled_sd) * j_correction
        
        results.append({
            'Task': task_label,
            'Metric': metric,
            'Sport_Mean': round(m1, 6),
            'NS_Mean': round(m2, 6),
            'p_value': round(p_val, 4),
            'Cohen_d': round(cohen_d, 4),
            'Hedges_g': round(g, 4)
        })
    
    return pd.DataFrame(results)

# Execute Analysis for Static and Dual-Task Files
# Ensure these filenames match the files you have saved locally
try:
    static_results = run_analysis('S_combined_static_stability_metrics.csv', 
                                  'NS_combined_static_stability_metrics.csv', 'Static')
    
    dual_results = run_analysis('S_combined_dual_stability_metrics.csv', 
                                'NS_combined_dual_stability_metrics.csv', 'Dual-Task')

    # Combine and Print
    full_report = pd.concat([static_results, dual_results], ignore_index=True)
    print("--- Statistical Summary ---")
    print(full_report)

    # Save to a final results file
    full_report.to_csv('sway_results_2.csv', index=False)
    print("\nResults exported to 'sway_results_2.csv'")

except FileNotFoundError as e:
    print(f"File Error: {e}")