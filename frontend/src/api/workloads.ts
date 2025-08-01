const API_BASE_URL = "https://10.0.2.30:8002/kubeconfig";

export const fetchResourceYaml = async (
  clusterId: number,
  namespace: string,
  resourceType: string,
  name: string
): Promise<string> => {
  const token = localStorage.getItem('access_token');
  const response = await fetch(
    `${API_BASE_URL}/clusters/${clusterId}/yaml/${namespace}/${resourceType}/${name}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch YAML: ${response.statusText}`);
  }
  
  return response.text();
};

export const updateResourceYaml = async (
  clusterId: number,
  namespace: string,
  resourceType: string,
  name: string,
  yamlContent: string
): Promise<{ success: boolean; message: string }> => {
  const token = localStorage.getItem('access_token');
  const response = await fetch(
    `${API_BASE_URL}/clusters/${clusterId}/yaml/${namespace}/${resourceType}/${name}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'text/plain'
      },
      body: yamlContent
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to update YAML: ${response.statusText}`);
  }
  
  return response.json();
};
