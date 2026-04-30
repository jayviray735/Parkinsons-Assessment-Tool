import pandas as pd
import numpy as np
from scipy import stats

# Define the specific Participant IDs for the 12/10 split
sport_ids = [5, 6, 9, 11, 12, 13, 14, 16, 17, 19, 20, 21]
ns_ids = [2, 3, 4, 7, 8, 10, 15, 18, 125, 369]

def permutation_p_value(group1, group2, iterations=10000):
    combined = np.concatenate([group1, group2])
    n1 = len(group1)
    # Calculate the observed absolute difference in means
    obs_diff = np.abs(np.mean(group1) - np.mean(group2))
    
    count = 0
    for _ in range(iterations):
        # Shuffle the data and split into two new random groups
        np.random.shuffle(combined)
        new_g1 = combined[:n1]
        new_g2 = combined[n1:]
        # Calculate the random difference
        rand_diff = np.abs(np.mean(new_g1) - np.mean(new_g2))
        
        # Count how often luck produces a difference larger than your real data
        if rand_diff >= obs_diff:
            count += 1
            
    return count / iterations

def run_analysis(file_s, file_ns, task_label):
    # Load the datasets
    df_s = pd.read_csv(file_s)
    df_ns = pd.read_csv(file_ns)
    
    # Filter for the definitive group IDs
    s_filtered = df_s[df_s['Participant_ID'].isin(sport_ids)]
    ns_filtered = df_ns[df_ns['Participant_ID'].isin(ns_ids)]
    
    # Calculate the mean of the 3 trials for each participant
    s_p_means = s_filtered.groupby('Participant_ID')[['RMS', 'NPL', 'P2P_Total', 'Jerk']].mean()
    ns_p_means = ns_filtered.groupby('Participant_ID')[['RMS', 'NPL', 'P2P_Total', 'Jerk']].mean()
    
    results = []
    n1, n2 = len(s_p_means), len(ns_p_means)
    df = n1 + n2 - 2 
    j_correction = 1 - (3 / (4 * df - 1)) 
    
    for metric in ['RMS', 'NPL', 'P2P_Total', 'Jerk']:
        g1 = s_p_means[metric].values
        g2 = ns_p_means[metric].values
        
        m1, sd1 = np.mean(g1), np.std(g1, ddof=1)
        m2, sd2 = np.mean(g2), np.std(g2, ddof=1)
        
        # Standard Welch's T-test
        t_stat, p_val_t = stats.ttest_ind(g1, g2, equal_var=False)
        
        # Permutation Test (10,000 iterations)
        p_val_perm = permutation_p_value(g1, g2)
        
        # Effect Sizes
        pooled_sd = np.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / df)
        cohen_d = (m2 - m1) / pooled_sd
        g = cohen_d * j_correction
        
        results.append({
            'Task': task_label,
            'Metric': metric,
            'Sport_Mean': round(m1, 6),
            'NS_Mean': round(m2, 6),
            'p_val_t_test': round(p_val_t, 4),
            'p_val_permutation': round(p_val_perm, 4),
            'Cohen_d': round(cohen_d, 4),
            'Hedges_g': round(g, 4)
        })
    
    return pd.DataFrame(results)

# Execute Analysis for Static and Dual-Task Files
try:
    static_results = run_analysis('S_combined_static_stability_metrics.csv', 
                                  'NS_combined_static_stability_metrics.csv', 'Static')
    
    dual_results = run_analysis('S_combined_dual_stability_metrics.csv', 
                                'NS_combined_dual_stability_metrics.csv', 'Dual-Task')

    # Combine and Print
    full_report = pd.concat([static_results, dual_results], ignore_index=True)
    print("--- Statistical Summary with Permutation Results ---")
    print(full_report)

    # Save to a final results file
    full_report.to_csv('sway_results_permutation.csv', index=False)
    print("\nResults exported to 'sway_results_permutation.csv'")

except FileNotFoundError as e:
    print(f"File Error: {e}. Ensure all combined CSV files are in the same folder as this script.")