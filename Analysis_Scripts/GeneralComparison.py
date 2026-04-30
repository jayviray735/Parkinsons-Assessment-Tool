import pandas as pd
import numpy as np
from scipy import stats

# Load the CSV files
s_static = pd.read_csv("S_combined_static_stability_metrics.csv")
s_dual = pd.read_csv("S_combined_dual_stability_metrics.csv")
s_dyn = pd.read_csv("S_combined_dynamic_metrics.csv")

ns_static = pd.read_csv("NS_combined_static_stability_metrics.csv")
ns_dual = pd.read_csv("NS_combined_dual_stability_metrics.csv")
ns_dyn = pd.read_csv("NS_combined_dynamic_metrics.csv")

# Aggregate & Rename Columns per Task
stab_cols = ['RMS', 'NPL', 'P2P_Total', 'Jerk']

# Sport Aggregation
s_stat_agg = s_static.groupby('Participant_ID')[stab_cols].mean().reset_index()
s_stat_agg.columns = ['Participant_ID', 'Stat_RMS', 'Stat_NPL', 'Stat_P2P', 'Stat_Jerk']

s_dual_agg = s_dual.groupby('Participant_ID')[stab_cols].mean().reset_index()
s_dual_agg.columns = ['Participant_ID', 'Dual_RMS', 'Dual_NPL', 'Dual_P2P', 'Dual_Jerk']

s_dyn_agg = s_dyn[['Participant_ID', 'Avg_RT', 'Avg_MT']].rename(
    columns={'Avg_RT': 'Dyn_RT', 'Avg_MT': 'Dyn_MT'})

# Non-Sport Aggregation
ns_stat_agg = ns_static.groupby('Participant_ID')[stab_cols].mean().reset_index()
ns_stat_agg.columns = ['Participant_ID', 'Stat_RMS', 'Stat_NPL', 'Stat_P2P', 'Stat_Jerk']

ns_dual_agg = ns_dual.groupby('Participant_ID')[stab_cols].mean().reset_index()
ns_dual_agg.columns = ['Participant_ID', 'Dual_RMS', 'Dual_NPL', 'Dual_P2P', 'Dual_Jerk']

ns_dyn_agg = ns_dyn[['Participant_ID', 'Avg_RT', 'Avg_MT']].rename(
    columns={'Avg_RT': 'Dyn_RT', 'Avg_MT': 'Dyn_MT'})

# Merge into Master DataFrame
sport_df = s_stat_agg.merge(s_dyn_agg, on='Participant_ID').merge(s_dual_agg, on='Participant_ID')
sport_df['Cohort'] = 'Sport'

nonsport_df = ns_stat_agg.merge(ns_dyn_agg, on='Participant_ID').merge(ns_dual_agg, on='Participant_ID')
nonsport_df['Cohort'] = 'Non-Sport'

master_df = pd.concat([sport_df, nonsport_df], ignore_index=True)

# Global Normalization (Min-Max Scaling 0 to 1)
metrics_to_normalize = [
    'Stat_RMS', 'Stat_NPL', 'Stat_P2P', 'Stat_Jerk',
    'Dyn_RT', 'Dyn_MT',
    'Dual_RMS', 'Dual_NPL', 'Dual_P2P', 'Dual_Jerk'
]

norm_cols = []
for col in metrics_to_normalize:
    norm_col_name = f"{col}_Norm"
    norm_cols.append(norm_col_name)
    col_min = master_df[col].min()
    col_max = master_df[col].max()
    master_df[norm_col_name] = (master_df[col] - col_min) / (col_max - col_min)

# Calculate the Grand Average
master_df['Grand_Average_Score'] = master_df[norm_cols].mean(axis=1)

# Perform the 3 Statistical Tests
sport_grand_avg = master_df[master_df['Cohort'] == 'Sport']['Grand_Average_Score']
nonsport_grand_avg = master_df[master_df['Cohort'] == 'Non-Sport']['Grand_Average_Score']

# Welch's T-Test 
t_stat, p_val_ttest = stats.ttest_ind(sport_grand_avg, nonsport_grand_avg, equal_var=False)

# Permutation Test 
def statistic(sport, nonsport):
    return np.mean(sport) - np.mean(nonsport)

perm_res = stats.permutation_test(
    data=(sport_grand_avg, nonsport_grand_avg), 
    statistic=statistic, 
    permutation_type='independent', 
    n_resamples=10000, 
    alternative='two-sided'
)
p_val_perm = perm_res.pvalue

# Mann-Whitney U Test 
mwu_stat, p_val_mwu = stats.mannwhitneyu(sport_grand_avg, nonsport_grand_avg, alternative='two-sided')

# Print the Results & Effect Sizes
print("=== STEP 1: GRAND AVERAGE RESULTS (ALL METRICS) ===")
print(f"Sport Group - Mean Grand Average Score: {sport_grand_avg.mean():.4f}")
print(f"Non-Sport Group - Mean Grand Average Score: {nonsport_grand_avg.mean():.4f}\n")

print("--- P-VALUE COMPARISON ---")
print(f"1. Welch's T-Test P-value:    {p_val_ttest:.4f}")
print(f"2. Permutation Test P-value:  {p_val_perm:.4f}")
print(f"3. Mann-Whitney U P-value:    {p_val_mwu:.4f}\n")

# Calculate Cohen's d
n1 = len(sport_grand_avg)
n2 = len(nonsport_grand_avg)
degrees_of_freedom = n1 + n2 - 2

pooled_std = np.sqrt(((n1 - 1) * sport_grand_avg.var() + (n2 - 1) * nonsport_grand_avg.var()) / degrees_of_freedom)
cohens_d = (nonsport_grand_avg.mean() - sport_grand_avg.mean()) / pooled_std

# Calculate Hedges' g 
j_correction = 1 - (3 / (4 * degrees_of_freedom - 1))
hedges_g = cohens_d * j_correction

print("--- EFFECT SIZES ---")
print(f"Cohen's d: {cohens_d:.4f}")
print(f"Hedges' g: {hedges_g:.4f}")

plot_df = master_df[['Participant_ID', 'Cohort', 'Grand_Average_Score']].copy()

# Rename the column so it instantly plugs into the Seaborn plotting script
plot_df.rename(columns={'Grand_Average_Score': 'Composite Score'}, inplace=True)

# Save to CSV
output_filename = "composite_scores.csv"
plot_df.to_csv(output_filename, index=False)

print(f"\n=== EXPORT COMPLETE ===")
print(f"Saved plotting data to: {output_filename}")