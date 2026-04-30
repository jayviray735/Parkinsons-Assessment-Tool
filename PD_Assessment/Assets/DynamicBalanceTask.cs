using UnityEngine;
using UnityEngine.UI;
using System.Collections;
using System.IO;
using System.Text;
using TMPro;
using UnityEngine.SceneManagement;
using UnityEngine.InputSystem;

/// <summary>
/// Core controller for the Dynamic Reaching Task.
/// Evaluates bradykinesia (slowness of movement) and motor execution by measuring 
/// Reaction Time (RT) and Movement Time (MT) during goal-directed 3D reaching tasks.
/// Features anti-predictive hovering logic and relative target spatial spawning.
/// </summary>
public class DynamicBalance : MonoBehaviour
{
    [Header("Task Configuration")]
    [Tooltip("Duration of one trial in seconds")]
    public float trialDuration = 45.0f;
    [Tooltip("Number of trials to perform")]
    public int totalTrials = 4;
    [Tooltip("Rest time between trials")]
    public float restDuration = 15.0f;

    [Header("Controller Setup")]
    [Tooltip("Drag RightHand Controller object here")]
    public Transform rightHandController;

    [Header("Orbs")]
    [Tooltip("Prefab for the orb")]
    public GameObject orbPrefab;
    [Tooltip("Minimum reach distance (meters)")]
    public float minSpawnRadius = 0.5f;
    [Tooltip("Maximum reach distance (meters)")]
    public float maxSpawnRadius = 0.7f;
    [Tooltip("Max angle left or right the orb can spawn (degrees)")]
    public float maxSpawnAngle = 45.0f;
    [Tooltip("Size of the hit area (e.g. 0.1 = 10cm)")]
    public float orbHitTolerance = 0.1f;
    [Tooltip("Speed required to trigger Reaction Time (m/s)")]
    public float movementInitiationThreshold = 0.05f;

    [Header("Alignment Setup")]
    [Tooltip("Drag your floor cylinder/disc here")]
    public Transform startDisc;
    [Tooltip("How close to the center they must stand (in meters). 0.2 = 20cm radius")]
    public float discRadius = 0.2f;

    [Header("UI & Input")]
    public TMP_Text timerDisplay;
    public TMP_Text statusDisplay;
    public InputActionReference vrConfirmButton;

    [Header("Data Logging")]
    private string participantID;
    public Transform headCamera;

    // Internal State
    private StringBuilder csvDataLocal;
    private Vector3 initialLocalHeadPos;

    private float nextSampleTime = 0.0f;
    private bool taskStarted = false;
    private bool isTaskRunning = false;
    private int currentTrial = 1;
    private float currentTimer;
    private float smoothedHandSpeed = 0f;

    // Sway
    private Vector3 lastLocalPos, lastLocalVel, lastLocalAcc;
    private bool isFirstSample = true;

    // Kinematics & Orb Logic
    private GameObject currentOrb;
    private Vector3 lastHandPos;
    private float timeOrbSpawned;
    private float timeMovementStarted;
    private bool waitingForReaction = false;
    private bool waitingForHit = false;

    // Logging Variables
    private string currentOrbEvent = "None";
    private float loggedRT = 0f;
    private float loggedMT = 0f;


    void Start()
    {
        participantID = TaskConfig.participantID;

        if (headCamera == null && Camera.main != null) headCamera = Camera.main.transform;

        UpdateStatusUI("Step onto the disc to begin");
    }

    void Update()
    {
        if (!taskStarted)
        {
            taskStarted = true;
            StartCoroutine(RunTrialsRoutine());
        }

        if (isTaskRunning)
        {
            currentTimer -= Time.deltaTime;
            if (timerDisplay != null) timerDisplay.text = $"Time Left: {currentTimer:F1}s";
            HandleReachingLogic();
            HandleLogging();
        }
    }

    /// <summary>
    /// Processes hand controller kinematics to determine exact Reaction Time (RT) 
    /// and Movement Time (MT), filtering out natural resting tremors.
    /// </summary>
    void HandleReachingLogic()
    {
        if (rightHandController == null) return;

        // Calculate smoothed instantaneous velocity to filter hardware noise/tremors
        float rawSpeed = Vector3.Distance(rightHandController.position, lastHandPos) / Time.deltaTime;
        lastHandPos = rightHandController.position;
        smoothedHandSpeed = Mathf.Lerp(smoothedHandSpeed, rawSpeed, 15f * Time.deltaTime);

        // Waiting for voluntary movement initiation
        if (waitingForReaction && currentOrb != null)
        {
            if (smoothedHandSpeed >= movementInitiationThreshold)
            {
                timeMovementStarted = Time.time;
                loggedRT = timeMovementStarted - timeOrbSpawned;
                waitingForReaction = false;
                waitingForHit = true;
                currentOrbEvent = "Movement Initiated";
            }
        }

        // Mathematical collision detection for high-speed tracking
        if (waitingForHit && currentOrb != null)
        {
            float distanceToOrb = Vector3.Distance(rightHandController.position, currentOrb.transform.position);
            if (distanceToOrb <= orbHitTolerance)
            {
                loggedMT = Time.time - timeMovementStarted;
                currentOrbEvent = "Hit";
                Destroy(currentOrb);
                waitingForHit = false;

                // Enforce neutral return policy before spawning the next stimulus
                StartCoroutine(WaitForHandToStop());
            }
        }
    }

    /// <summary>
    /// Enforces the Movement Initiation Threshold protocol.
    /// Prevents 'predictive hovering' by requiring the user to hold their hand 
    /// completely still (at their chest) before the next target spawns.
    /// </summary>
    IEnumerator WaitForHandToStop()
    {
        // Wait for a fraction of a second to let the physical hit finish
        yield return new WaitForSeconds(0.2f);

        bool isHandStill = false;
        float stillTimer = 0f;

        // Loop continuously until the hand is held still (under 0.1 m/s) for 0.5 consecutive seconds
        while (!isHandStill && isTaskRunning)
        {
            if (smoothedHandSpeed < 0.1f)
            {
                stillTimer += Time.deltaTime;
                if (stillTimer >= 0.5f)
                {
                    isHandStill = true; // Movement stopped for 0.5 seconds, safe to spawn the next orb
                }
            }
            else
            {
                stillTimer = 0f; // Reset timer if movement is detected
            }
            yield return null;
        }

        // The hand is fully stopped at the chest, safe to spawn the next orb
        if (isTaskRunning) SpawnOrb();
    }

    /// <summary>
    /// Dynamically calculates target coordinates relative to the user's localized headset 
    /// position, ensuring anatomical differences do not become confounding variables.
    /// </summary>
    void SpawnOrb()
    {
        if (orbPrefab == null) return;
        float spawnAngle = Random.Range(-maxSpawnAngle, maxSpawnAngle) * Mathf.Deg2Rad;
        float actualRadius = Random.Range(minSpawnRadius, maxSpawnRadius);
        float spawnX = Mathf.Sin(spawnAngle) * actualRadius;
        float spawnZ = Mathf.Cos(spawnAngle) * actualRadius;
        float spawnY = Random.Range(-0.4f, -0.1f);

        Vector3 spawnOffset = new Vector3(spawnX, spawnY, spawnZ);

        // Transform the relative offset into World Space based on the baseline origin
        Vector3 spawnWorldPos = transform.TransformPoint(initialLocalHeadPos + spawnOffset);

        currentOrb = Instantiate(orbPrefab, spawnWorldPos, Quaternion.identity);
        timeOrbSpawned = Time.time;

        waitingForHit = false;
        waitingForReaction = true;

        currentOrbEvent = "Orb Spawned";
        loggedMT = 0f;
        loggedRT = 0f;
    }

    /// <summary>
    /// Custom update loop guaranteeing a 50Hz logging frequency (dt = 0.02s).
    /// Serializes both Relative (Local) and Global (World) kinematics, along with event timestamps.
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

            // Write to CSV
            csvDataLocal.AppendLine(string.Format("{0:F3},{1},{2:F4},{3:F4},{4:F4},{5:F4},{6},{7:F3},{8:F3}",
                Time.time, currentTrial, adjustedLocalPos.x, adjustedLocalPos.z,
                localSwayRadius, localJerk, currentOrbEvent, loggedRT, loggedMT));

            nextSampleTime = Time.time + dt;

            // Clear the event trigger for the next frame
            if (currentOrbEvent == "Orb Spawned" || currentOrbEvent == "Hit" || currentOrbEvent == "Movement Initiated")
            {
                currentOrbEvent = "None";
                loggedMT = 0f;
                loggedRT = 0f;
            }
        }
    }

    // Deprecated: This was the original simple spawn logic before implementing the neutral return policy.
    /*
    IEnumerator SpawnNextOrbAfterDelay(float delay)
    {
        yield return new WaitForSeconds(delay);
        if (isTaskRunning) SpawnOrb();
    }
    */

    /// <summary>
    /// Coroutine orchestrating the trial sequence, strict spatial alignment checks,
    /// and mandatory rest intervals.
    /// </summary>
    IEnumerator RunTrialsRoutine()
    {
        // Headers for file
        csvDataLocal = new StringBuilder();
        csvDataLocal.AppendLine("Timestamp,Trial,Adj_Local_Sway_X,Adj_Local_Sway_Z,Local_Sway_Radius,Local_Sway_Jerk,Orb_Event,Reaction_Time,Movement_Time");

        for (int i = 1; i <= totalTrials; i++)
        {
            currentTrial = i;
            bool readyToStart = false;

            // Strict alignment requirement: User must be on the central origin disc
            while (!readyToStart)
            {
                bool isOnDisc = false;

                // Calculate distance between headset and disc (ignoring Y height)
                if (startDisc != null && headCamera != null)
                {
                    Vector2 headPos2D = new Vector2(headCamera.position.x, headCamera.position.z);
                    Vector2 discPos2D = new Vector2(startDisc.position.x, startDisc.position.z);
                    float distance = Vector2.Distance(headPos2D, discPos2D);
                    isOnDisc = (distance <= discRadius);
                }

                if (isOnDisc)
                {
                    UpdateStatusUI($"Trial {i}/{totalTrials}\nPress 'A' to Begin");

                    // Check for button press only if they are on the disc
                    if ((Keyboard.current != null && Keyboard.current.spaceKey.wasPressedThisFrame) ||
                        (vrConfirmButton != null && vrConfirmButton.action.triggered))
                    {
                        readyToStart = true;
                    }
                }
                else
                {
                    UpdateStatusUI($"Trial {i}/{totalTrials}\nPlease step onto the center disc");
                }

                yield return null; // Wait for the next frame and check again
            }

            UpdateStatusUI("Stabilizing...");
            yield return new WaitForSeconds(2.0f);

            // Establish Baselines at the exact moment of trial initialization
            initialLocalHeadPos = transform.InverseTransformPoint(headCamera.position);

            currentTimer = trialDuration;
            isFirstSample = true;

            lastLocalPos = transform.InverseTransformPoint(headCamera.position) - initialLocalHeadPos;
            lastLocalVel = Vector3.zero;
            lastLocalAcc = Vector3.zero;

            if (rightHandController != null) lastHandPos = rightHandController.position;

            isTaskRunning = true;
            UpdateStatusUI(""); // Clear status text so they focus entirely on the orbs

            StartCoroutine(WaitForHandToStop());

            // Run trial until timer hits 0
            while (currentTimer > 0) yield return null;

            // Stop the trial
            isTaskRunning = false;
            if (currentOrb != null) Destroy(currentOrb);

            // Rest Phase
            if (i < totalTrials)
            {
                float restTimer = restDuration;

                while (restTimer > 0)
                {
                    restTimer -= Time.deltaTime;
                    UpdateStatusUI($"Rest: {restTimer:F1}s\nReturn to the center disc");
                    yield return null;
                }
            }
        }

        EndTask();
    }

    void UpdateStatusUI(string message) { if (statusDisplay != null) statusDisplay.text = message; }

    /// <summary>
    /// Finalizes the trial sequence, writes StringBuilder data to the local Quest 3 storage, 
    /// and safely transitions back to the main menu.
    /// </summary>
    void EndTask()
    {
        string timeStr = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
        string filenameLocal = string.Format("{0}_DynamicBalance_RelativeSway_{1}.csv", participantID, timeStr);

        string folderPath = "/storage/emulated/0/Download/PDTrialData";

        if (!Directory.Exists(folderPath))
        {
            Directory.CreateDirectory(folderPath);
            Debug.Log("Created new data folder at: " + folderPath);
        }

        string pathLocal = Path.Combine(folderPath, filenameLocal);

        File.WriteAllText(pathLocal, csvDataLocal.ToString());
        Debug.Log($"Data saved to {pathLocal}");
        UpdateStatusUI("Task Complete!\nReturning to Menu in 5 seconds...");
        if (timerDisplay != null) timerDisplay.text = "Done";
        StartCoroutine(ReturnToMenu());
    }

    IEnumerator ReturnToMenu()
    {
        yield return new WaitForSeconds(5.0f); // Wait for 5 seconds
        SceneManager.LoadScene("MenuScene");   // Teleport back to the menu
    }
}