import React from "react";
import { motion } from "framer-motion";
import { Icon } from "@iconify/react";
import { 
  Card, 
  CardBody, 
  CardHeader, 
  Button, 
  Tabs, 
  Tab,
  Input,
  Select,
  SelectItem,
  Textarea,
  Checkbox,
  Divider,
  addToast
} from "@heroui/react";

interface ClusterOnboardingProps {
  selectedCluster?: string;
}

export const ClusterOnboarding: React.FC<ClusterOnboardingProps> = () => {
  const [selected, setSelected] = React.useState("manual");
  const [isLoading, setIsLoading] = React.useState(false);
  const [step, setStep] = React.useState(1);
  
  const cloudProviders = [
    { value: "aws", label: "Amazon Web Services (AWS)" },
    { value: "gcp", label: "Google Cloud Platform (GCP)" },
    { value: "azure", label: "Microsoft Azure" },
    { value: "do", label: "Digital Ocean" },
    { value: "other", label: "Other" }
  ];
  
  const kubernetesVersions = [
    { value: "1.29", label: "v1.29 (Latest)" },
    { value: "1.28", label: "v1.28" },
    { value: "1.27", label: "v1.27" },
    { value: "1.26", label: "v1.26" },
    { value: "custom", label: "Custom Version" }
  ];
  
  const handleSubmit = () => {
    setIsLoading(true);
    
    // Simulate API call
    setTimeout(() => {
      addToast({
        title: "Cluster Onboarding Started",
        description: "Your cluster is being onboarded. This may take a few minutes.",
        color: "success"
      });
      setIsLoading(false);
      setStep(1); // Reset to first step
    }, 2000);
  };
  
  const nextStep = () => {
    if (step < 3) {
      setStep(step + 1);
    } else {
      handleSubmit();
    }
  };
  
  const prevStep = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };
  
  const renderStepContent = () => {
    switch(step) {
      case 1:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Basic Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Cluster Name"
                placeholder="e.g., production-cluster"
                startContent={<Icon icon="lucide:tag" className="text-foreground-400" />}
              />
              <Select
                label="Cloud Provider"
                placeholder="Select cloud provider"
                startContent={<Icon icon="lucide:cloud" className="text-foreground-400" />}
              >
                {cloudProviders.map((provider) => (
                  <SelectItem key={provider.value} value={provider.value}>
                    {provider.label}
                  </SelectItem>
                ))}
              </Select>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                label="Kubernetes Version"
                placeholder="Select version"
                startContent={<Icon icon="lucide:git-branch" className="text-foreground-400" />}
              >
                {kubernetesVersions.map((version) => (
                  <SelectItem key={version.value} value={version.value}>
                    {version.label}
                  </SelectItem>
                ))}
              </Select>
              <Input
                label="Region"
                placeholder="e.g., us-west-2"
                startContent={<Icon icon="lucide:map-pin" className="text-foreground-400" />}
              />
            </div>
            <Textarea
              label="Description"
              placeholder="Describe the purpose of this cluster"
              minRows={3}
            />
          </div>
        );
      case 2:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Network & Security</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="VPC/Network ID"
                placeholder="e.g., vpc-12345678"
                startContent={<Icon icon="lucide:network" className="text-foreground-400" />}
              />
              <Input
                label="Subnet IDs"
                placeholder="e.g., subnet-12345678,subnet-87654321"
                startContent={<Icon icon="lucide:network" className="text-foreground-400" />}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Security Group"
                placeholder="e.g., sg-12345678"
                startContent={<Icon icon="lucide:shield" className="text-foreground-400" />}
              />
              <Select
                label="Network Policy"
                placeholder="Select policy"
                startContent={<Icon icon="lucide:filter" className="text-foreground-400" />}
              >
                <SelectItem value="calico">Calico</SelectItem>
                <SelectItem value="cilium">Cilium</SelectItem>
                <SelectItem value="none">None</SelectItem>
              </Select>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Security Options</p>
              <div className="space-y-2">
                <Checkbox defaultSelected>Enable Pod Security Policies</Checkbox>
                <Checkbox defaultSelected>Enable Network Policies</Checkbox>
                <Checkbox defaultSelected>Enable Encryption at Rest</Checkbox>
                <Checkbox>Enable Private Cluster</Checkbox>
              </div>
            </div>
          </div>
        );
      case 3:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Configuration & Review</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Node Size"
                placeholder="e.g., t3.medium"
                startContent={<Icon icon="lucide:server" className="text-foreground-400" />}
              />
              <Input
                label="Node Count"
                type="number"
                placeholder="e.g., 3"
                min={1}
                defaultValue="3"
                startContent={<Icon icon="lucide:layers" className="text-foreground-400" />}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                label="Auto-scaling"
                placeholder="Select option"
                defaultSelectedKeys={["enabled"]}
                startContent={<Icon icon="lucide:trending-up" className="text-foreground-400" />}
              >
                <SelectItem value="enabled">Enabled</SelectItem>
                <SelectItem value="disabled">Disabled</SelectItem>
              </Select>
              <div className="flex gap-4">
                <Input
                  label="Min Nodes"
                  type="number"
                  placeholder="e.g., 2"
                  min={1}
                  defaultValue="2"
                />
                <Input
                  label="Max Nodes"
                  type="number"
                  placeholder="e.g., 10"
                  min={1}
                  defaultValue="10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Add-ons</p>
              <div className="space-y-2">
                <Checkbox defaultSelected>Monitoring (Prometheus & Grafana)</Checkbox>
                <Checkbox defaultSelected>Logging (Elasticsearch & Kibana)</Checkbox>
                <Checkbox defaultSelected>Service Mesh (Istio)</Checkbox>
                <Checkbox>Backup & Restore (Velero)</Checkbox>
              </div>
            </div>
            <Divider />
            <div className="p-3 bg-primary-100 text-primary-700 rounded-medium">
              <p className="text-sm">
                <Icon icon="lucide:info" className="inline mr-1" />
                Review your configuration before creating the cluster. This process may take 5-10 minutes to complete.
              </p>
            </div>
          </div>
        );
      default:
        return null;
    }
  };
  
  return (
    <div className="space-y-6">
      <Card className="w-full">
        <CardHeader className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Icon icon="lucide:plus-circle" className="text-primary" />
            <h2 className="text-xl font-semibold">Cluster Onboarding</h2>
          </div>
          <p className="text-sm text-foreground-500">Add a new Kubernetes cluster to KubeSage</p>
        </CardHeader>
        <CardBody>
          <Tabs 
            aria-label="Onboarding options" 
            selectedKey={selected} 
            onSelectionChange={setSelected as any}
            variant="underlined"
            color="primary"
          >
            <Tab 
              key="manual" 
              title={
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:edit-3" />
                  <span>Manual Setup</span>
                </div>
              }
            >
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="mt-4"
              >
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white">
                        {step}
                      </div>
                      <span className="font-medium">
                        Step {step} of 3: {step === 1 ? 'Basic Information' : step === 2 ? 'Network & Security' : 'Configuration & Review'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-foreground-500">{Math.round((step / 3) * 100)}% Complete</span>
                    </div>
                  </div>
                  <div className="w-full h-1 bg-content3 rounded-full overflow-hidden">
                    <motion.div 
                      className="h-full bg-primary"
                      initial={{ width: `${((step - 1) / 3) * 100}%` }}
                      animate={{ width: `${(step / 3) * 100}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                </div>
                
                {renderStepContent()}
                
                <div className="flex justify-between mt-6">
                  <Button
                    variant="flat"
                    onPress={prevStep}
                    isDisabled={step === 1 || isLoading}
                    startContent={<Icon icon="lucide:arrow-left" />}
                  >
                    Previous
                  </Button>
                  <Button
                    color="primary"
                    onPress={nextStep}
                    isLoading={isLoading}
                    endContent={step < 3 ? <Icon icon="lucide:arrow-right" /> : <Icon icon="lucide:check" />}
                  >
                    {step < 3 ? 'Next' : 'Create Cluster'}
                  </Button>
                </div>
              </motion.div>
            </Tab>
            <Tab 
              key="import" 
              title={
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:download" />
                  <span>Import Existing</span>
                </div>
              }
            >
              <div className="mt-4 space-y-4">
                <div className="p-4 border-2 border-dashed border-content3 rounded-lg text-center">
                  <div className="flex flex-col items-center gap-2">
                    <Icon icon="lucide:upload-cloud" className="text-4xl text-foreground-400" />
                    <h3 className="font-medium">Upload kubeconfig file</h3>
                    <p className="text-sm text-foreground-500">Drag and drop your kubeconfig file here, or click to browse</p>
                    <Button variant="flat" color="primary">
                      Select File
                    </Button>
                  </div>
                </div>
                
                <Divider>
                  <span className="text-foreground-500 text-sm px-2">OR</span>
                </Divider>
                
                <div>
                  <Textarea
                    label="Paste kubeconfig content"
                    placeholder="Paste your kubeconfig YAML here..."
                    minRows={6}
                  />
                </div>
                
                <div className="flex justify-end">
                  <Button
                    color="primary"
                    endContent={<Icon icon="lucide:check" />}
                  >
                    Import Cluster
                  </Button>
                </div>
              </div>
            </Tab>
            <Tab 
              key="automated" 
              title={
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:zap" />
                  <span>Automated</span>
                </div>
              }
            >
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card className="p-4 border border-content3 hover:border-primary transition-colors cursor-pointer">
                    <div className="flex flex-col items-center gap-2 text-center">
                      <Icon icon="logos:aws" className="text-4xl" />
                      <h3 className="font-medium">Amazon EKS</h3>
                      <p className="text-xs text-foreground-500">Connect to your AWS account to create EKS clusters</p>
                      <Button size="sm" color="primary" variant="flat">
                        Connect
                      </Button>
                    </div>
                  </Card>
                  
                  <Card className="p-4 border border-content3 hover:border-primary transition-colors cursor-pointer">
                    <div className="flex flex-col items-center gap-2 text-center">
                      <Icon icon="logos:google-cloud" className="text-4xl" />
                      <h3 className="font-medium">Google GKE</h3>
                      <p className="text-xs text-foreground-500">Connect to your GCP account to create GKE clusters</p>
                      <Button size="sm" color="primary" variant="flat">
                        Connect
                      </Button>
                    </div>
                  </Card>
                  
                  <Card className="p-4 border border-content3 hover:border-primary transition-colors cursor-pointer">
                    <div className="flex flex-col items-center gap-2 text-center">
                      <Icon icon="logos:microsoft-azure" className="text-4xl" />
                      <h3 className="font-medium">Azure AKS</h3>
                      <p className="text-xs text-foreground-500">Connect to your Azure account to create AKS clusters</p>
                      <Button size="sm" color="primary" variant="flat">
                        Connect
                      </Button>
                    </div>
                  </Card>
                </div>
                
                <div className="p-3 bg-warning-100 text-warning-700 rounded-medium">
                  <p className="text-sm">
                    <Icon icon="lucide:alert-triangle" className="inline mr-1" />
                    Automated provisioning requires cloud provider API credentials with appropriate permissions.
                  </p>
                </div>
              </div>
            </Tab>
          </Tabs>
        </CardBody>
      </Card>
    </div>
  );
};