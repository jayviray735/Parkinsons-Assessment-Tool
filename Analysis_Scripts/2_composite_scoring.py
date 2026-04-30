import pandas as pd
import numpy as np
from pathlib import Path

# ==========================================
# CONFIGURATION & FILE PATHS
# ==========================================
DATA_DIR = Path("../Sample_Data")

FILES = {
    'Sport': {
        'Static': DATA_DIR / 'sport_mock_static_data.csv',
        'Dual': DATA_DIR / 'sport_mock_dual_data.csv',
        'Dynamic': DATA_DIR / 'sport_mock_dynamic_data.csv'
    },
    'NonSport': {
        'Static': DATA_DIR / 'nonsport_mock_static_data.csv',
        'Dual': DATA_DIR / 'nonsport_mock_dual_data.csv',
        'Dynamic': DATA_DIR / 'nonsport_mock_dynamic_data.csv'
    }
}

def load_and_aggregate(cohort):
    """Loads all tasks for a specific cohort and aggregates them by Participant."""
    sway_cols = ['Participant_ID', 'RMS', 'NPL', 'P2P_Total', 'Jerk']
    dyn_cols = ['Participant_ID', 'Avg_RT', 'Avg_MT']
    
    # Load data
    stat = pd.read_csv(FILES[cohort]['Static'])[sway_cols]
    dual = pd.read_csv(FILES[cohort]['Dual'])[sway_cols]
    dyn = pd.read_csv(FILES[cohort]['Dynamic'])[dyn_cols]
    
    # Group to mean (1 row per participant)
    stat_agg = stat.groupby('Participant_ID').mean().reset_index()
    dual_agg = dual.groupby('Participant_ID').mean().reset_index()
    dyn_agg = dyn.groupby('Participant_ID').mean().reset_index()
    
    # Rename columns to differentiate tasks
    stat_agg.columns = ['Participant_ID', 'Stat_RMS', 'Stat_NPL', 'Stat_P2P', 'Stat_Jerk']
    dual_agg.columns = ['Participant_ID', 'Dual_RMS', 'Dual_NPL', 'Dual_P2P', 'Dual_Jerk']
    dyn_agg.columns = ['Participant_ID', 'Dyn_RT', 'Dyn_MT']
    
    # Merge into a single dataframe for this cohort
    merged = stat_agg.merge(dual_agg, on='Participant_ID').merge(dyn_agg, on='Participant_ID')
    merged['Cohort'] = cohort
    return merged

def main():
    try:
        # Compile Cohorts
        sport_df = load_and_aggregate('Sport')
        nonsport_df = load_and_aggregate('NonSport')
        master_df = pd.concat([sport_df, nonsport_df], ignore_index=True)
        
        # Global Normalization (Min-Max Scaling 0 to 1)
        # Required to combine disparate units (e.g. Jerk vs. Reaction Time)
        metrics_to_normalize = [
            'Stat_RMS', 'Stat_NPL', 'Stat_P2P', 'Stat_Jerk',
            'Dual_RMS', 'Dual_NPL', 'Dual_P2P', 'Dual_Jerk',
            'Dyn_RT', 'Dyn_MT'
        ]
        
        norm_cols = []
        for col in metrics_to_normalize:
            norm_col_name = f"{col}_Norm"
            norm_cols.append(norm_col_name)
            col_min = master_df[col].min()
            col_max = master_df[col].max()
            master_df[norm_col_name] = (master_df[col] - col_min) / (col_max - col_min)
            
        # Calculate the Grand Composite Score
        master_df['Composite Score'] = master_df[norm_cols].mean(axis=1)
        
        # Calculate Multitasking Interaction (Cost of Cognitive Load)
        master_df['Delta_Jerk (Dual - Static)'] = master_df['Dual_Jerk'] - master_df['Stat_Jerk']
        
        # Export for Violin Plot Generation
        plot_df = master_df[['Participant_ID', 'Cohort', 'Composite Score', 'Delta_Jerk (Dual - Static)']].copy()
        
        output_file = "plotting_data_composites.csv"
        plot_df.to_csv(output_file, index=False)
        
        print("=== COMPOSITE SCORING COMPLETE ===")
        print(f"Data successfully normalized and saved to '{output_file}' for visualization.")
        print(plot_df.groupby('Cohort').mean())

    except Exception as e:
        print(f"Error during composite calculation: {e}. Please ensure all 6 mock data files are present.")

if __name__ == "__main__":
    main()