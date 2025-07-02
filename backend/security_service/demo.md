Create an interactive dashboard with the following workflow:

### Step 1: Cluster Selection
- Dropdown menu listing all available clusters
- User selects a cluster from the list

### Step 2: Namespace Selection
- After cluster selection:
  - Dynamic dropdown showing namespaces available in the selected cluster
  - User selects a target namespace

### Step 3: Policy Category Selection
- Dropdown listing Kyverno policy categories (e.g., "Security", "Compliance", "Best Practices")
- User selects a category

### Step 4: Policy Listing
- Display all policies under the selected category in a scrollable list/table
- User selects a specific policy

### Step 5: Policy Editing Options
After policy selection, show two parallel editing interfaces:

#### Option 1: YAML Editor
- Display the raw YAML of the selected policy
- Fully editable text area
- Real-time syntax validation
- Show diff between original/edited versions

#### Option 2: Form-Based Editor
- Form with categorized input fields:
  - Basic metadata (name, description)
  - Rule-specific parameters (patterns, conditions)
  - Validation constraints
- Editable input fields with type validation
- Auto-generate YAML preview from form data

### Step 6: Policy Deployment
- Action buttons below editors:
  - `Apply to Cluster`: Deploys edited policy to selected cluster/namespace
  - `Dry Run`: Test without deployment
  - `Reset`: Revert to original policy
- Visual confirmation on successful application

### UI Requirements
- Step-by-step workflow visualization (progress bar)
- Context display showing current selections:
  `Cluster > Namespace > Category > Policy`
- Responsive layout supporting both editor views side-by-side
- Persistent draft saving during editing
