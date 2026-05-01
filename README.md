## Project Overview
This repository contains the software for a proof-of-concept Virtual Reality (VR) diagnostic tool aimed at detecting neuromotor deficits associated with early-stage Parkinson's Disease.

The software consists of a two-part pipeline:
1. **The VR Acquisition Layer (Unity/C#):** Three gamified tasks (Static Balance, Dynamic Reaching, and a Cognitive-Motor Dual-Task) that log metrics such as Sway, Jerk, Reaction Time, and Movement Time.
2. **The Analytical Layer (Python):** A data pipeline that aggregates the raw CSV outputs and performs non-parametric statistical evaluations (Permutation testing, Hedges' g) to distinguish varying levels of neuromotor efficiency.

---

## Repository Structure
* `/Unity Project/` - The complete Unity project (C# scripts, scenes, and UI assets). 
* `/Data_Analysis/` - The automated Python statistical pipeline used to evaluate between-group and within-group kinematic data.

* *Ethics Note: Real participant data has been omitted from this public repository to comply with university ethics regarding human-participant data privacy. The provided mock data allows the analytical pipeline to be safely evaluated.*

---

## Running the Unity VR Application

### Prerequisites
* **Unity Editor:** `6000.4.5f1`
* **Build Target:** Android (Required for Meta Quest deployment)
* **Hardware:** Meta Quest 3 + Touch Plus Controllers

### Setup Instructions
1. Clone or download this repository.
2. Open **Unity Hub** -> Click **Add** -> Select the `/Unity Project/` folder.
3. Allow Unity time to resolve the packages and rebuild the local `Library` cache.
4. In the Unity Editor, open `MenuScene` located in `Assets/Scenes/`.
5. Connect the Meta Quest 3 via Quest Link or build the `.apk` directly to the headset to test the 50Hz polling loop.

---

## Part 2: Running the Python Data Analysis

### Prerequisites
The analytical pipeline was built using Python 3.12.2. The following libraries are required:
```bash
pip install pandas numpy scipy matplotlib seaborn
```

### To Run
```bash
python <analysis_filename>.py
```
