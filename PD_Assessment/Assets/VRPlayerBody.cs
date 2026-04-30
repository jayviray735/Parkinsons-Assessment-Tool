using UnityEngine;

public class VRPlayerBody : MonoBehaviour
{
    void Start()
    {
        // Auto-tag this object as Player
        if (!gameObject.CompareTag("Player"))
        {
            gameObject.tag = "Player";
            Debug.Log("VRPlayerBody: Automatically set tag to 'Player'");
        }

        // Add Rigidbody if missing (Needed for collision detection)
        if (GetComponent<Rigidbody>() == null)
        {
            Rigidbody rb = gameObject.AddComponent<Rigidbody>();
            rb.useGravity = false; // Don't fall
            rb.isKinematic = true; // Moved by headset, not physics
        }

        // Add Collider if missing
        if (GetComponent<Collider>() == null)
        {
            CapsuleCollider col = gameObject.AddComponent<CapsuleCollider>();
            col.height = 1.8f;
            col.radius = 0.15f;
            col.center = new Vector3(0, -0.9f, 0); // Hang down from head
            col.isTrigger = false; // Physical object
        }
    }
}