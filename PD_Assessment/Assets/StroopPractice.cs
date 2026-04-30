using UnityEngine;
using TMPro;
using UnityEngine.InputSystem;
using System.Collections;

/// <summary>
/// Manages the practice mode for the Stroop test
/// </summary>
public class StroopPractice : MonoBehaviour
{
    [Header("UI References")]
    [Tooltip("The parent object holding the practice UI")]
    public GameObject practicePanel;
    public TMP_Text stroopDisplay;
    public TMP_Text feedbackText;

    [Header("Inputs")]
    // Mapped to physical VR controller buttons (e.g., A, B, Trigger, Grip)
    public InputActionReference btnRed;
    public InputActionReference btnBlue;
    public InputActionReference btnGreen;
    public InputActionReference btnYellow;

    [Header("Settings")]
    // Time allowed for each word before it changes
    public float timeBetweenWords = 3.0f;

    // Data arrays for generating the stroop words and their corresponding colors
    private string[] stroopWords = { "RED", "BLUE", "GREEN", "YELLOW" };
    private Color[] stroopColors = { Color.red, Color.blue, Color.green, Color.yellow };

    // Tracks the current target color index for checking answers
    private int currentTargetColorIndex;

    // State variables for managing the practice flow
    private bool isPracticing = false;
    private bool waitingForAnswer = false;
    private float timer = 0f;

    // Called to start the practice mode
    public void StartPractice()
    {
        if (practicePanel != null) practicePanel.SetActive(true);
        isPracticing = true;
        timer = 1.0f;
        waitingForAnswer = false;

        // Reset UI elements
        if (feedbackText != null) feedbackText.gameObject.SetActive(false);
        if (stroopDisplay != null) stroopDisplay.text = "";
    }

    // Called to stop the practice mode
    public void StopPractice()
    {
        isPracticing = false;
        if (practicePanel != null) practicePanel.SetActive(false);
    }

    void Update()
    {
        // Only run the practice logic if we're currently practicing
        if (!isPracticing) return;

        timer -= Time.deltaTime;

        // When the timer runs out, generate a new word and reset the timer
        if (timer <= 0)
        {
            GenerateNewWord();
        }

        // If we're waiting for the participant's answer, check for input
        if (waitingForAnswer)
        {
            CheckInput();
        }
    }

    /// <summary>
    /// Generates a new Stroop word with a random color and resets the state for the next answer
    /// </summary>
    void GenerateNewWord()
    {
        // Randomly select a word and a color for the display
        int wordIndex = Random.Range(0, stroopWords.Length);
        currentTargetColorIndex = Random.Range(0, stroopColors.Length);

        if (stroopDisplay != null)
        {
            stroopDisplay.text = stroopWords[wordIndex];
            stroopDisplay.color = stroopColors[currentTargetColorIndex];
            stroopDisplay.gameObject.SetActive(true);
        }

        waitingForAnswer = true;
        timer = timeBetweenWords; // Reset timer for the next word
    }

    /// <summary>
    /// Checks the participant's input against the current target color and provides feedback
    /// </summary>
    void CheckInput()
    {
        int guessedColor = -1;

        // Check each button to see if it was pressed and determine the guessed color index
        if (btnRed != null && btnRed.action.triggered) guessedColor = 0;
        else if (btnBlue != null && btnBlue.action.triggered) guessedColor = 1;
        else if (btnGreen != null && btnGreen.action.triggered) guessedColor = 2;
        else if (btnYellow != null && btnYellow.action.triggered) guessedColor = 3;

        // If a button was pressed, check if the guess is correct and show feedback
        if (guessedColor != -1)
        {
            // Determine if the guessed color matches the current target color index
            bool isCorrect = (guessedColor == currentTargetColorIndex);
            StartCoroutine(ShowFeedback(isCorrect));

            // Reset for the next word
            waitingForAnswer = false;
            if (stroopDisplay != null) stroopDisplay.text = "";
        }
    }

    /// <summary>
    /// Displays feedback for a short duration indicating
    /// whether the participant's answer was correct or wrong
    /// </summary>
    /// <param name="isCorrect"></param>
    /// <returns></returns>
    IEnumerator ShowFeedback(bool isCorrect)
    {
        if (feedbackText != null)
        {
            feedbackText.text = isCorrect ? "CORRECT!" : "WRONG!";
            feedbackText.color = isCorrect ? Color.green : Color.red;
            feedbackText.gameObject.SetActive(true);
            yield return new WaitForSeconds(0.5f);
            feedbackText.gameObject.SetActive(false);
        }
    }
}