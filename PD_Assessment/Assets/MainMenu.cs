using UnityEngine;
using UnityEngine.SceneManagement;
using TMPro;

public class MainMenuController : MonoBehaviour
{
    [Header("Exact Scene Names")]
    public string balanceSceneName = "StaticScene";  // Used for Tasks 1 & 3
    public string dynamicSceneName = "DynamicScene"; // Used for Task 2
    public TMP_InputField participantInputField;

    public void StartTask1()
    {
        TaskConfig.runAsDualTask = false; // Turn OFF Stroop
        SceneManager.LoadScene(balanceSceneName);
    }

    public void StartTask2()
    {
        SceneManager.LoadScene(dynamicSceneName);
    }

    public void StartTask3()
    {
        TaskConfig.runAsDualTask = true; // Turn ON Stroop
        SceneManager.LoadScene(balanceSceneName);
    }

    public void QuitApplication()
    {
        Debug.Log("Exiting Game...");
        Application.Quit();
    }

    public void UpdateParticipantID()
    {
        if (participantInputField != null)
        {
            TaskConfig.participantID = participantInputField.text;
            Debug.Log("Set ID to: " + TaskConfig.participantID);
        }
    }
}