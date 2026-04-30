import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

# ==========================================
# CONFIGURATION & FILE PATHS
# ==========================================
DATA_DIR = Path("../Sample_Data")

FILES = {
    'Sport': {
        'Static': DATA_DIR / 'sport_mock_static_data.csv',
        'Dual': DATA_DIR / 'sport_mock_dual_data.csv'
    },
    'NonSport': {
        'Static': DATA_DIR / 'nonsport_mock_static_data.csv',
        'Dual': DATA_DIR / 'nonsport_mock_dual_data.csv'
    }
}

# ==========================================
# STATISTICAL FUNCTIONS
# ==========================================
def paired_permutation_p_value(condition1, condition2, iterations=10000):
    """Permutation test for paired/repeated measures (Static vs Dual)."""
    diffs = np.array(condition2) - np.array(condition1)
    obs_mean_diff = np.abs(np.mean(diffs))
    
    count = 0
    for _ in range(iterations):
        # Randomly flip the sign of the differences
        signs = np.random.choice([-1, 1], size=len(diffs))
        permuted_diffs = diffs * signs
        if np.abs(np.mean(permuted_diffs)) >= obs_mean_diff:
            count += 1
            
    return count / iterations

def independent_permutation_p_value(group1, group2, iterations=10000):
    """Permutation test for independent measures (Sport Deltas vs NonSport Deltas)."""
    combined = np.concatenate([group1, group2])
    n1 = len(group1)
    obs_diff = np.abs(np.mean(group1) - np.mean(group2))
    
    count = 0
    for _ in range(iterations):
        np.random.shuffle(combined)
        if np.abs(np.mean(combined[:n1]) - np.mean(combined[n1:])) >= obs_diff:
            count += 1
            
    return count / iterations

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    metrics = ['RMS', 'NPL', 'P2P_Total', 'Jerk']
    paired_results = []
    interaction_results = []

    try:
        # Load and aggregate data (1 row per participant)
        s_stat = pd.read_csv(FILES['Sport']['Static']).groupby('Participant_ID')[metrics].mean()
        s_dual = pd.read_csv(FILES['Sport']['Dual']).groupby('Participant_ID')[metrics].mean()
        
        ns_stat = pd.read_csv(FILES['NonSport']['Static']).groupby('Participant_ID')[metrics].mean()
        ns_dual = pd.read_csv(FILES['NonSport']['Dual']).groupby('Participant_ID')[metrics].mean()
        
        # Ensure we only compare participants that exist in BOTH static and dual
        s_common = s_stat.index.intersection(s_dual.index)
        ns_common = ns_stat.index.intersection(ns_dual.index)
        
        for m in metrics:
            # PAIRED WITHIN-GROUP EFFECTS (Static vs Dual)
            # Sport Cohort
            s_stat_vals = s_stat.loc[s_common, m].values
            s_dual_vals = s_dual.loc[s_common, m].values
            t_s, p_t_s = stats.ttest_rel(s_stat_vals, s_dual_vals)
            p_perm_s = paired_permutation_p_value(s_stat_vals, s_dual_vals)
            
            paired_results.append({
                'Cohort': 'Sport', 'Metric': m,
                'Static_Mean': round(np.mean(s_stat_vals), 4),
                'Dual_Mean': round(np.mean(s_dual_vals), 4),
                'Paired_T_p_val': round(p_t_s, 4),
                'Permutation_p_val': round(p_perm_s, 4)
            })
            
            # Non-Sport Cohort
            ns_stat_vals = ns_stat.loc[ns_common, m].values
            ns_dual_vals = ns_dual.loc[ns_common, m].values
            t_ns, p_t_ns = stats.ttest_rel(ns_stat_vals, ns_dual_vals)
            p_perm_ns = paired_permutation_p_value(ns_stat_vals, ns_dual_vals)
            
            paired_results.append({
                'Cohort': 'NonSport', 'Metric': m,
                'Static_Mean': round(np.mean(ns_stat_vals), 4),
                'Dual_Mean': round(np.mean(ns_dual_vals), 4),
                'Paired_T_p_val': round(p_t_ns, 4),
                'Permutation_p_val': round(p_perm_ns, 4)
            })

            # INTERACTION EFFECTS (Cost of Multitasking)
            # Delta = Dual - Static (How much worse did they get?)
            s_deltas = s_dual_vals - s_stat_vals
            ns_deltas = ns_dual_vals - ns_stat_vals
            
            t_int, p_t_int = stats.ttest_ind(s_deltas, ns_deltas, equal_var=False)
            p_perm_int = independent_permutation_p_value(s_deltas, ns_deltas)
            
            # Effect Size (Cohen's d for independent groups)
            n1, n2 = len(s_deltas), len(ns_deltas)
            dof = n1 + n2 - 2
            pooled_std = np.sqrt(((n1 - 1) * np.var(s_deltas, ddof=1) + (n2 - 1) * np.var(ns_deltas, ddof=1)) / dof)
            cohens_d = (np.mean(ns_deltas) - np.mean(s_deltas)) / pooled_std if pooled_std != 0 else 0
            
            interaction_results.append({
                'Metric': m,
                'Sport_Delta_Mean': round(np.mean(s_deltas), 4),
                'NonSport_Delta_Mean': round(np.mean(ns_deltas), 4),
                'Interaction_T_p_val': round(p_t_int, 4),
                'Interaction_Perm_p_val': round(p_perm_int, 4),
                'Cohens_d': round(cohens_d, 4)
            })

        # OUTPUT
        df_paired = pd.DataFrame(paired_results)
        df_interaction = pd.DataFrame(interaction_results)
        
        print("=== 1. PAIRED EFFECTS (INTERNAL COHORT DEGRADATION) ===")
        print(df_paired.to_string(index=False))
        
        print("\n=== 2. INTERACTION EFFECTS (COST OF MULTITASKING DIFFERENCES) ===")
        print(df_interaction.to_string(index=False))
        
        df_paired.to_csv("paired_effects_results.csv", index=False)
        df_interaction.to_csv("interaction_effects_results.csv", index=False)
        print("\nResults exported to CSV files.")

    except FileNotFoundError as e:
        print(f"Error: Could not find mock data file. {e.filename}")

if __name__ == "__main__":
    main()