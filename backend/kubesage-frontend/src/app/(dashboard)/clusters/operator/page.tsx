'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { kubeconfigService } from '../../../../lib/api';
import { Card, Button, Alert, Spinner } from 'react-bootstrap';
import { useRouter } from 'next/navigation';

export default function InstallOperatorPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isInstalling, setIsInstalling] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  
  const installMutation = useMutation({
    mutationFn: kubeconfigService.installOperator,
    onMutate: () => {
      setIsInstalling(true);
      setError('');
      setResults([]);
    },
    onSuccess: (data) => {
      setResults(data.results || []);
      setSuccess(data.operator_installed);
      
      // Invalidate clusters query to refresh the UI
      queryClient.invalidateQueries({ queryKey: ['kubeconfigs'] });
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Installation failed');
    },
    onSettled: () => {
      setIsInstalling(false);
    }
  });
  
  const handleInstall = () => {
    if (window.confirm('Are you sure you want to install the k8sgpt operator on the active cluster?')) {
      installMutation.mutate();
    }
  };
  
  return (
    <div>
      <h1 className="mb-4">Install K8sGPT Operator</h1>
      
      <Card>
        <Card.Body>
          <div className="mb-4">
            <h5>About K8sGPT Operator</h5>
            <p>
              The K8sGPT Operator is a Kubernetes operator that helps analyze cluster issues
              using AI. It can identify problems and provide natural language explanations
              and recommendations.
            </p>
          </div>
          
          {error && (
            <Alert variant="danger">
              <Alert.Heading>Installation Error</Alert.Heading>
              <p>{error}</p>
            </Alert>
          )}
          
          {success && (
            <Alert variant="success">
              <Alert.Heading>Installation Successful!</Alert.Heading>
              <p>
                The K8sGPT Operator has been successfully installed on your cluster.
                You can now use it to analyze your cluster for issues.
              </p>
            </Alert>
          )}
          
          {results.length > 0 && (
            <div className="mb-4">
              <h5>Installation Results</h5>
              <div className="border rounded p-3 bg-light">
                <pre className="mb-0" style={{ whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(results, null, 2)}
                </pre>
              </div>
            </div>
          )}
          
          <div className="d-flex justify-content-between">
            <Button
              variant="secondary"
              onClick={() => router.push('/clusters/list')}
              disabled={isInstalling}
            >
              Back to Clusters
            </Button>
            
            {!success && (
              <Button
                variant="primary"
                onClick={handleInstall}
                disabled={isInstalling}
              >
                {isInstalling ? (
                  <>
                    <Spinner
                      as="span"
                      animation="border"
                      size="sm"
                      role="status"
                      aria-hidden="true"
                      className="me-2"
                    />
                    Installing...
                  </>
                ) : (
                  'Install Operator'
                )}
              </Button>
            )}
          </div>
        </Card.Body>
      </Card>
    </div>
  );
}
