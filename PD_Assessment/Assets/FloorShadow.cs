// This script should be attached to a GameObject that represents the floor shadow.
// But is not currently used.
using UnityEngine;

public class FloorShadow : MonoBehaviour
{
    public Transform targetToFollow; // The Player or Camera
    public float floorHeight = 0.01f; // Just slightly above 0 so it doesn't flicker (Z-fight)

    void Update()
    {
        if (targetToFollow == null) return;

        // Copy the target's X and Z, but keep Y fixed at floor level
        Vector3 newPos = transform.position;
        newPos.x = targetToFollow.position.x;
        newPos.z = targetToFollow.position.z;
        newPos.y = floorHeight;

        transform.position = newPos;
    }
}