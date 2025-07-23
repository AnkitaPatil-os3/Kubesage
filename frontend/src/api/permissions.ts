export async function fetchPermissions(token: string): Promise<string[]> {
  try {
    const response = await fetch("https://10.0.32.105:8001/users/permissions", {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/json"
      }
    });
    if (!response.ok) {
      console.error("Failed to fetch permissions:", response.statusText);
      return [];
    }
    const data = await response.json();
    return data.permissions || [];
  } catch (error) {
    console.error("Error fetching permissions:", error);
    return [];
  }
}
