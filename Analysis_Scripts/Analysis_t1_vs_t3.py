import pandas as pd
import numpy as np
from scipy import stats

# Load the CSV files (Only Static and Dual)
s_static = pd.read_csv("S_combined_static_stability_metrics.csv")
s_dual = pd.read_csv("S_combined_dual_stability_metrics.csv")

ns_static = pd.read_csv("NS_combined_static_stability_metrics.csv")
ns_dual = pd.read_csv("NS_combined_dual_stability_metrics.csv")

# Aggregate & Rename Columns per Task
stab_cols = ['RMS', 'NPL', 'P2P_Total', 'Jerk']

s_stat_agg = s_static.groupby('Participant_ID')[stab_cols].mean().reset_index()
s_stat_agg.columns = ['Participant_ID', 'Stat_RMS', 'Stat_NPL', 'Stat_P2P', 'Stat_Jerk']

s_dual_agg = s_dual.groupby('Participant_ID')[stab_cols].mean().reset_index()
s_dual_agg.columns = ['Participant_ID', 'Dual_RMS', 'Dual_NPL', 'Dual_P2P', 'Dual_Jerk']

ns_stat_agg = ns_static.groupby('Participant_ID')[stab_cols].mean().reset_index()
ns_stat_agg.columns = ['Participant_ID', 'Stat_RMS', 'Stat_NPL', 'Stat_P2P', 'Stat_Jerk']

ns_dual_agg = ns_dual.groupby('Participant_ID')[stab_cols].mean().reset_index()
ns_dual_agg.columns = ['Participant_ID', 'Dual_RMS', 'Dual_NPL', 'Dual_P2P', 'Dual_Jerk']

# Merge into Master DataFrame
sport_df = s_stat_agg.merge(s_dual_agg, on='Participant_ID')
sport_df['Cohort'] = 'Sport'

nonsport_df = ns_stat_agg.merge(ns_dual_agg, on='Participant_ID')
nonsport_df['Cohort'] = 'Non-Sport'

master_df = pd.concat([sport_df, nonsport_df], ignore_index=True)

# Joint-Normalization (Static & Dual on the same scale)
metrics = ['RMS', 'NPL', 'P2P', 'Jerk']

for m in metrics:
    col_min = min(master_df[f'Stat_{m}'].min(), master_df[f'Dual_{m}'].min())
    col_max = max(master_df[f'Stat_{m}'].max(), master_df[f'Dual_{m}'].max())
    
    master_df[f'Stat_{m}_Norm'] = (master_df[f'Stat_{m}'] - col_min) / (col_max - col_min)
    master_df[f'Dual_{m}_Norm'] = (master_df[f'Dual_{m}'] - col_min) / (col_max - col_min)

# Calculate Composites and Deltas
stat_norm_cols = [f'Stat_{m}_Norm' for m in metrics]
dual_norm_cols = [f'Dual_{m}_Norm' for m in metrics]

master_df['Comp_Stat'] = master_df[stat_norm_cols].mean(axis=1)
master_df['Comp_Dual'] = master_df[dual_norm_cols].mean(axis=1)

# Deltas (Cost of Multitasking: Dual - Static)
master_df['Delta_Comp'] = master_df['Comp_Dual'] - master_df['Comp_Stat']
master_df['Delta_Jerk'] = master_df['Dual_Jerk'] - master_df['Stat_Jerk']

sport_df = master_df[master_df['Cohort'] == 'Sport']
nonsport_df = master_df[master_df['Cohort'] == 'Non-Sport']

# Helper Functions for Stats
def paired_statistic(condition1, condition2):
    return np.mean(condition2 - condition1) # Dual - Static

def ind_statistic(x, y):
    return np.mean(y) - np.mean(x) # NonSport - Sport

def calc_paired_cohens_d(stat, dual):
    diff = dual - stat
    return diff.mean() / diff.std(ddof=1)

def calc_ind_effect_sizes(sport_data, nonsport_data):
    n1, n2 = len(sport_data), len(nonsport_data)
    dof = n1 + n2 - 2
    pooled_std = np.sqrt(((n1 - 1) * sport_data.var(ddof=1) + (n2 - 1) * nonsport_data.var(ddof=1)) / dof)
    cohens_d = (nonsport_data.mean() - sport_data.mean()) / pooled_std
    hedges_g = cohens_d * (1 - (3 / (4 * dof - 1)))
    return cohens_d, hedges_g

# PAIRED WITHIN-GROUP TESTS
print("\n" + "="*60)
print("  PAIRED WITHIN-GROUP TESTS (STATIC VS DUAL)")
print("="*60)

for cohort, df in [("SPORT COHORT", sport_df), ("NON-SPORT COHORT", nonsport_df)]:
    print(f"\n--- {cohort} ---")
    
    # Composite Score
    c_stat, c_dual = df['Comp_Stat'], df['Comp_Dual']
    t_val_c, p_ttest_c = stats.ttest_rel(c_stat, c_dual)
    p_perm_c = stats.permutation_test(data=(c_stat, c_dual), statistic=paired_statistic, permutation_type='samples', n_resamples=10000, alternative='two-sided').pvalue
    d_c = calc_paired_cohens_d(c_stat, c_dual)
    
    print(" [Composite Score]")
    print(f"   Means:           Static = {c_stat.mean():.4f} | Dual = {c_dual.mean():.4f}")
    print(f"   Paired T-test:   p = {p_ttest_c:.4f}")
    print(f"   Permutation:     p = {p_perm_c:.4f}")
    print(f"   Cohen's d:       d = {d_c:.4f}  (Effect size of internal change)\n")
    
    # Raw Mean Jerk
    j_stat, j_dual = df['Stat_Jerk'], df['Dual_Jerk']
    t_val_j, p_ttest_j = stats.ttest_rel(j_stat, j_dual)
    p_perm_j = stats.permutation_test(data=(j_stat, j_dual), statistic=paired_statistic, permutation_type='samples', n_resamples=10000, alternative='two-sided').pvalue
    d_j = calc_paired_cohens_d(j_stat, j_dual)
    
    print(" [Raw Mean Jerk]")
    print(f"   Means:           Static = {j_stat.mean():.2f} | Dual = {j_dual.mean():.2f}")
    print(f"   Paired T-test:   p = {p_ttest_j:.4f}")
    print(f"   Permutation:     p = {p_perm_j:.4f}")
    print(f"   Cohen's d:       d = {d_j:.4f}  (Effect size of internal change)")

# INTERACTION EFFECT (DELTAS)
print("\n" + "="*60)
print("  INTERACTION EFFECT (COST OF MULTITASKING)")
print("="*60)

# Composite Score Interaction
delta_c_s, delta_c_ns = sport_df['Delta_Comp'], nonsport_df['Delta_Comp']
t_val_ic, p_ttest_ic = stats.ttest_ind(delta_c_s, delta_c_ns, equal_var=False)
p_perm_ic = stats.permutation_test(data=(delta_c_s, delta_c_ns), statistic=ind_statistic, permutation_type='independent', n_resamples=10000, alternative='two-sided').pvalue
d_ic, g_ic = calc_ind_effect_sizes(delta_c_s, delta_c_ns)

print("\n--- 1. OVERALL COMPOSITE INTERACTION ---")
print(f" Sport Delta:     {delta_c_s.mean():.4f}")
print(f" Non-Sport Delta: {delta_c_ns.mean():.4f}")
print("-" * 40)
print(f" Welch's T-test:  p = {p_ttest_ic:.4f}")
print(f" Permutation:     p = {p_perm_ic:.4f}")
print(f" Cohen's d:       d = {d_ic:.4f}")
print(f" Hedges' g:       g = {g_ic:.4f}")

# Raw Mean Jerk Interaction
delta_j_s, delta_j_ns = sport_df['Delta_Jerk'], nonsport_df['Delta_Jerk']
t_val_ij, p_ttest_ij = stats.ttest_ind(delta_j_s, delta_j_ns, equal_var=False)
p_perm_ij = stats.permutation_test(data=(delta_j_s, delta_j_ns), statistic=ind_statistic, permutation_type='independent', n_resamples=10000, alternative='two-sided').pvalue
d_ij, g_ij = calc_ind_effect_sizes(delta_j_s, delta_j_ns)

print("\n--- 2. RAW JERK INTERACTION ---")
print(f" Sport Delta:     {delta_j_s.mean():.2f}")
print(f" Non-Sport Delta: {delta_j_ns.mean():.2f}")
print("-" * 40)
print(f" Welch's T-test:  p = {p_ttest_ij:.4f}")
print(f" Permutation:     p = {p_perm_ij:.4f}")
print(f" Cohen's d:       d = {d_ij:.4f}")
print(f" Hedges' g:       g = {g_ij:.4f}")
print("="*60)