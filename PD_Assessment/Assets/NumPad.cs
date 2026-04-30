using UnityEngine;
using TMPro;

public class VRNumpad : MonoBehaviour
{
    public TMP_InputField targetInputField;

    // This adds the typed number
    public void AddNumber(string number)
    {
        if (targetInputField != null)
        {
            targetInputField.text += number;
        }
    }

    // This clears the box
    public void ClearInput()
    {
        if (targetInputField != null)
        {
            targetInputField.text = "";
        }
    }

    // Enters the number and saves it to TaskConfig
    public void ConfirmEnter()
    {
        if (targetInputField != null)
        {
            TaskConfig.participantID = targetInputField.text;

            Debug.Log("Participant ID officially saved as: " + TaskConfig.participantID);
        }

        gameObject.SetActive(false);
    }
}