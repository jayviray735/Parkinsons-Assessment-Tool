using UnityEngine;
using UnityEngine.UI;
using System.Collections;
using System.IO;
using System.Text;
using TMPro;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

/// <summary>
/// Core controller for the postural stability assessments.
/// Dynamically toggles between the Static Balance Task and the Dual-Task (Stroop)
/// based on global configuration flags, managing physics-simulated tilt, 
/// high-frequency (50Hz) kinematic logging, and cognitive-motor interference.
/// </summary>
public class StaticBalanceTask : MonoBehaviour
{
    [Header("Testing Configuration")]
    public bool debugForcePlayerOn = false;

    [Header("Task Configuration")]
    [Tooltip("Duration for the normal Static Task (seconds)")]
    public float staticTrialDuration = 35.0f;
    [Tooltip("Duration for the Stroop Dual-Task (seconds)")]
    public float dualTrialDuration = 45.0f;
    private float activeTrialDuration;
    [Tooltip("Number of trials")]
    public int totalTrials = 3;
    [Tooltip("Rest time between trials")]
    public float restDuration = 5.0f;

    [Header("Difficulty Settings")]
    [Tooltip("How much the board tips when you lean (Higher = Harder)")]
    public float playerWeightSensitivity = 25.0f;

    [Tooltip("Controls how responsive the board is (Lower = Harder)")]
    public float boardResponsiveness = 5.0f;

    [Tooltip("Wave Strength (No longer used!)")]
    public float turbulenceStrength = 0.0f;
    public float maxTipAngle = 10.0f;

    [Tooltip("Visual Gain (to exagerrate board movement)")]
    public float visualGain = 1.0f;

    [Tooltip("Score Penalty (how fast the accuracy drops)")]
    public float scoreSensitivity = 5.0f;

    [Header("Spirit Level UI")]
    public RectTransform bubbleDot;
    public float bubbleSensitivity = 4.0f;
    [Tooltip("Red Square UI element")]
    public GameObject centerCrosshairUI;

    [Header("Input Settings")]
    [Tooltip("Drag the VR button action here")]
    public InputActionReference vrConfirmButton;

    [Header("Task 3: Dual-Task (Stroop)")]
    [Tooltip("Tick this to activate Task 3 mode.")]
    public bool enableDualTask = false;
    public TMP_Text stroopDisplay;
    public float timeBetweenWords = 2.0f;

    [Tooltip("Map these to A, B, X, Y on the controllers")]
    public InputActionReference btnRed;
    public InputActionReference btnBlue;
    public InputActionReference btnGreen;
    public InputActionReference btnYellow;

    // Stroop Variables
    private string[] stroopWords = { "RED", "BLUE", "GREEN", "YELLOW" };
    private Color[] stroopColors = { Color.red, Color.blue, Color.green, Color.yellow };
    private int currentTargetColorIndex;
    private float stroopTimer;
    private bool waitingForStroopAnswer = false;
    private float wordDisplayTime;
    public GameObject stroopControlsUI;
    public TMP_Text feedbackText;
    private string currentStroopEvent = "None";
    private float currentStroopRT = 0f;

    [Header("References")]
    public Transform headCamera;
    public TMP_Text timerDisplay;
    public TMP_Text statusDisplay;

    [Header("Data Logging")]
    private string participantID;

    // Internal state
    private bool isPlayerOnPlatform = false;
    private float currentTimer;
    private int currentTrial = 1;
    private float nextSampleTime = 0.0f;
    private bool isTaskRunning = false;
    private bool hasConfirmedStart = false;

    private StringBuilder csvDataLocal;

    private Vector3 initialLocalHeadPos;
    private Vector3 lastLocalPos, lastLocalVel, lastLocalAcc;
    private bool isFirstSample = true;

    void Start()
    {
        // Initialize participant ID and dual-task flag from global configuration
        participantID = TaskConfig.participantID;
        enableDualTask = TaskConfig.runAsDualTask;

        if (enableDualTask)
        {
            activeTrialDuration = dualTrialDuration;
        }
        else
        {
            activeTrialDuration = staticTrialDuration;
        }

        if (headCamera == null && Camera.main != null) 
            headCamera = Camera.main.transform;

        if (headCamera == null && Camera.main != null)
            headCamera = Camera.main.transform;

        // Only if they are somehow off (can recenter with Meta button anyway)
        UpdateStatusUI("Step onto Platform"); 

        // Ensure cross is visible
        if (centerCrosshairUI != null) centerCrosshairUI.SetActive(true);

        // Dynamically configure UI based on task mode
        if (stroopDisplay != null)
        {
            stroopDisplay.gameObject.SetActive(false);
            stroopControlsUI.SetActive(enableDualTask);
        }
    }

    void Update()
    {
        // If player leaves platform, reset everything
        bool playerReady = isPlayerOnPlatform || debugForcePlayerOn;
        if (!playerReady)
        {
            // Return the platform to neutral position (smoothly)
            transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.identity, Time.deltaTime * 2.0f);
            return;
        }

        if (!hasConfirmedStart)
        {
            hasConfirmedStart = true;
            StartCoroutine(RunTrialsRoutine());
        }

        UpdateSpiritLevel();

        if (isTaskRunning)
        {
            HandlePlatformPhysics();
            HandleTimer();
            if (enableDualTask) HandleStroopTest();
            HandleLogging(); // 50Hz Custom Polling
        }
    }

    /// <summary>
    /// Manages the cognitive load presentation during the Dual Task.
    /// </summary>
    void HandleStroopTest()
    {
        stroopTimer -= Time.deltaTime;

        if (stroopTimer <= 0)
        {
            if (waitingForStroopAnswer)
            {
                // Log Missed Response
                currentStroopEvent = "Missed";
                currentStroopRT = -1f;
            }
            GenerateNewStroopWord();
        }
        if (waitingForStroopAnswer)
        {
            CheckStroopInput();
        }
    }

    void GenerateNewStroopWord()
    {
        int wordIndex = Random.Range(0, stroopWords.Length);
        currentTargetColorIndex = Random.Range(0, stroopColors.Length);

        if (stroopDisplay != null)
        {
            stroopDisplay.text = stroopWords[wordIndex];
            stroopDisplay.color = stroopColors[currentTargetColorIndex];
            stroopDisplay.gameObject.SetActive(true);
        }

        wordDisplayTime = Time.time;
        waitingForStroopAnswer = true;
        stroopTimer = timeBetweenWords;
        currentStroopEvent = "Displayed";
        currentStroopRT = 0f;
    }

    void CheckStroopInput()
    {
        int guessedColor = -1;

        // Check which button was pressed
        if (btnRed != null && btnRed.action.triggered) guessedColor = 0;
        else if (btnBlue != null && btnBlue.action.triggered) guessedColor = 1;
        else if (btnGreen != null && btnGreen.action.triggered) guessedColor = 2;
        else if (btnYellow != null && btnYellow.action.triggered) guessedColor = 3;

        // If any button was pressed
        if (guessedColor != -1)
        {
            currentStroopRT = Time.time - wordDisplayTime;

            if (guessedColor == currentTargetColorIndex)
            {
                currentStroopEvent = "Correct";
                StartCoroutine(ShowFeedback(true));
            }
            else
            {
                currentStroopEvent = "Incorrect";
                StartCoroutine(ShowFeedback(false));
            }

            waitingForStroopAnswer = false;

            if (stroopDisplay != null) stroopDisplay.text = "";
        }
    }

    private System.Collections.IEnumerator ShowFeedback(bool isCorrect)
    {
        if (feedbackText != null)
        {
            // Set the text and color
            feedbackText.text = isCorrect ? "CORRECT!" : "WRONG!";
            feedbackText.color = isCorrect ? Color.green : Color.red;

            // Turn it on
            feedbackText.gameObject.SetActive(true);

            // Wait for half a second
            yield return new WaitForSeconds(0.5f);

            // Turn it back off
            feedbackText.gameObject.SetActive(false);
        }
    }

    /// <summary>
    /// Coroutine orchestrating the strict pre-trial calibration, execution, 
    /// and mandatory rest intervals to ensure experimental consistency.
    /// </summary>
    IEnumerator RunTrialsRoutine()
    {
        // CSV Headers
        csvDataLocal = new StringBuilder();
        csvDataLocal.AppendLine("Timestamp,Trial,Adj_Sway_X,Adj_Sway_Z,Tilt_X,Tilt_Z,Stability_Score,Sway_Radius,Sway_Jerk,Stroop_Event,Stroop_RT");

        for (int i = 1; i <= totalTrials; i++)
        {
            currentTrial = i;

            if (centerCrosshairUI != null) centerCrosshairUI.SetActive(true);
            UpdateStatusUI($"Trial {i}/{totalTrials}\nAlign Green Dot with Red Square & Press 'A' to Begin");

            yield return new WaitUntil(() =>
                (Keyboard.current != null && Keyboard.current.spaceKey.wasPressedThisFrame) ||
                (btnGreen != null && btnGreen.action.triggered) // Using A button to start
            );

            if (centerCrosshairUI != null) centerCrosshairUI.SetActive(false);

            UpdateStatusUI("Stabilising...");
            yield return new WaitForSeconds(2.0f);

            // Capture Initial Head Position for Calculations
            initialLocalHeadPos = transform.InverseTransformPoint(headCamera.position);

            currentTimer = activeTrialDuration;
            isTaskRunning = true;

            stroopTimer = 2.0f;
            waitingForStroopAnswer = false;
            if (stroopDisplay != null) stroopDisplay.text = "";
            currentStroopEvent = "None";
            currentStroopRT = 0f;

            isFirstSample = true;
            lastLocalPos = transform.InverseTransformPoint(headCamera.position) - initialLocalHeadPos;
            lastLocalVel = Vector3.zero;
            lastLocalAcc = Vector3.zero;

            Debug.Log($"Starting Trial {i}");

            // Wait for trial to finish
            while (currentTimer > 0) yield return null;

            isTaskRunning = false;
            if (stroopDisplay != null) stroopDisplay.text = ""; // Hide word when trial ends

            // Rest Phase
            if (i < totalTrials)
            {
                float restTimer = restDuration;
                if (centerCrosshairUI != null) centerCrosshairUI.SetActive(true);
                while (restTimer > 0)
                {
                    transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.identity, Time.deltaTime * 2.0f);  
                    restTimer -= Time.deltaTime;
                    UpdateStatusUI($"Rest: {restTimer:F1}s\nRe-align with Red Square");
                    yield return null;
                }
            }
        }

        EndTask();
    }

    /// <summary>
    /// Translates real-time localized user sway into target Euler angles,
    /// applying Spherical Linear Interpolation (Slerp) to simulate a physical balance board.
    /// </summary>
    void HandlePlatformPhysics()
    {
        // Calculate Sway
        Vector3 currentLocalPos = transform.InverseTransformPoint(headCamera.position);
        float swayX = currentLocalPos.x - initialLocalHeadPos.x;
        float swayZ = currentLocalPos.z - initialLocalHeadPos.z;

        // Apply Visual Gain to exaggerate movement for better feedback
        swayX *= visualGain;
        swayZ *= visualGain;

        // Calculate Rotation
        float targetRotX = swayZ * playerWeightSensitivity;
        float targetRotZ = -swayX * playerWeightSensitivity;

        // Deprecated: Wave Simulation (Removed for Clinical Relevance)
        /* if (turbulenceStrength > 0)
        {
            float noiseX = (Mathf.PerlinNoise(Time.time * 0.5f, 0) - 0.5f) * turbulenceStrength;
            float noiseZ = (Mathf.PerlinNoise(0, Time.time * 0.5f) - 0.5f) * turbulenceStrength;
            targetRotX += noiseX;
            targetRotZ += noiseZ;
        } */

        targetRotX = Mathf.Clamp(targetRotX, -maxTipAngle, maxTipAngle);
        targetRotZ = Mathf.Clamp(targetRotZ, -maxTipAngle, maxTipAngle);

        Quaternion targetRotation = Quaternion.Euler(targetRotX, 0, targetRotZ);
        transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * boardResponsiveness);
    }

    void HandleTimer()
    {
        currentTimer -= Time.deltaTime;

        // Calculate Stability Score based on current tilt angle
        float tipAngle = Quaternion.Angle(transform.rotation, Quaternion.identity);

        // The score is a simple linear function of the tip angle, clamped between 0 and 100.
        float score = Mathf.Clamp(100 - (tipAngle * scoreSensitivity), 0, 100);

        // Update UI
        if (timerDisplay != null) timerDisplay.text = $"{currentTimer:F1}s";
        UpdateStatusUI($"Trial {currentTrial}/{totalTrials}\nStability: {score:F0}%");
    }

    /// <summary>
    /// Custom update loop guaranteeing a 50Hz logging frequency (dt = 0.02s).
    /// Serializes both Relative (Local) and Global (World) kinematics.
    /// </summary>
    void HandleLogging()
    {
        if (Time.time >= nextSampleTime)
        {
            float dt = 0.02f; // Time step (1/50)

            // Local Sway (Relative to Platform)
            Vector3 rawLocalPos = transform.InverseTransformPoint(headCamera.position);
            Vector3 adjustedLocalPos = rawLocalPos - initialLocalHeadPos;
            Vector2 planarLocalPos = new Vector2(adjustedLocalPos.x, adjustedLocalPos.z);
            float localSwayRadius = planarLocalPos.magnitude;
            float localJerk = 0f;

            if (!isFirstSample)
            {
                Vector3 currentLocalVel = (adjustedLocalPos - lastLocalPos) / dt;
                Vector3 currentLocalAcc = (currentLocalVel - lastLocalVel) / dt;
                localJerk = (currentLocalAcc - lastLocalAcc).magnitude / dt;
                lastLocalVel = currentLocalVel;
                lastLocalAcc = currentLocalAcc;
            }
            lastLocalPos = adjustedLocalPos;

            isFirstSample = false;

            // Get Tilt & Score
            float tiltAngle = Quaternion.Angle(transform.rotation, Quaternion.identity);
            float score = Mathf.Clamp(100 - (tiltAngle * scoreSensitivity), 0, 100);

            // Write to Local CSV
            csvDataLocal.AppendLine(string.Format("{0:F3},{1},{2:F4},{3:F4},{4:F2},{5:F2},{6:F0},{7:F4},{8:F4},{9},{10:F3}",
                Time.time, currentTrial, adjustedLocalPos.x, adjustedLocalPos.z,
                transform.eulerAngles.x, transform.eulerAngles.z, score,
                localSwayRadius, localJerk, currentStroopEvent, currentStroopRT));

            nextSampleTime = Time.time + dt;

            // Reset the event string so it doesn't spam the CSV until the next event
            if (currentStroopEvent == "Correct" || currentStroopEvent == "Incorrect" || currentStroopEvent == "Missed")
            {
                currentStroopEvent = "None";
                currentStroopRT = 0f;
            }
        }
    }

    /// <summary>
    /// Governs the 2D UI Spirit Level. 
    /// Acts as a head-tracker during calibration and a tilt-tracker during live trials.
    /// </summary>
    void UpdateSpiritLevel()
    {
        if (bubbleDot != null)
        {
            float newX, newY;

            if (isTaskRunning)
            {
                // During task: Act like a normal spirit level
                float tiltX = transform.localEulerAngles.x;
                float tiltZ = transform.localEulerAngles.z;

                if (tiltX > 180) tiltX -= 360;
                if (tiltZ > 180) tiltZ -= 360;

                newY = tiltX * bubbleSensitivity;
                newX = -tiltZ * bubbleSensitivity;
            }
            else
            {
                // During waiting/rest: Act as a head tracker so they can aim for the cross
                Vector3 localHead = transform.InverseTransformPoint(headCamera.position);
                newX = localHead.x * (bubbleSensitivity * 10f);
                newY = localHead.z * (bubbleSensitivity * 10f);
            }

            // Clamp the bubble within a certain radius so it doesn't go off-screen
            Vector2 anchoredPos = new Vector2(newX, newY);
            anchoredPos = Vector2.ClampMagnitude(anchoredPos, 40f);
            bubbleDot.anchoredPosition = anchoredPos;
        }
    }

    void UpdateStatusUI(string message) { if (statusDisplay != null) statusDisplay.text = message; }
    void OnCollisionEnter(Collision c) { if (c.gameObject.CompareTag("Player")) isPlayerOnPlatform = true; }
    void OnCollisionExit(Collision c) { if (c.gameObject.CompareTag("Player")) isPlayerOnPlatform = false; }

    /// <summary>
    /// Finalizes the trial sequence, writes StringBuilder data to the local Quest 3 storage, 
    /// and safely transitions back to the main menu.
    /// </summary>
    void EndTask()
    {
        string taskName = enableDualTask ? "DualTask" : "StaticTask";
        string timeStr = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");

        string filenameLocal = string.Format("{0}_{1}_RelativeSway_{2}.csv", participantID, taskName, timeStr);
        string folderPath = "/storage/emulated/0/Download/PDTrialData";

        if (!Directory.Exists(folderPath))
        {
            Directory.CreateDirectory(folderPath);
            Debug.Log("Created new data folder at: " + folderPath);
        }

        string pathLocal = Path.Combine(folderPath, filenameLocal);
        File.WriteAllText(pathLocal, csvDataLocal.ToString());
        Debug.Log($"Data saved to {pathLocal}");

        UpdateStatusUI("Task Complete");
        if (timerDisplay != null) timerDisplay.text = "Done";
        UpdateStatusUI("Task Complete!\nReturning to Menu in 5 seconds...");

        if (centerCrosshairUI != null) centerCrosshairUI.SetActive(false);

        // This triggers the 5-second countdown to switch scenes
        StartCoroutine(ReturnToMenu());
    }

        IEnumerator ReturnToMenu()
    {
        yield return new WaitForSeconds(5.0f); // Wait for 5 seconds
        SceneManager.LoadScene("MenuScene");   // Teleport back to the menu
    }
}