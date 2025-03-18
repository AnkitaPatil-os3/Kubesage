'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { kubeconfigService } from '../../../../lib/api';
import { Table, Button, Card, Badge, Alert } from 'react-bootstrap';
import Link from 'next/link';
import { useState } from 'react';
import useStore from '../../../../lib/store';

export default function KubeconfigListPage() {
  const queryClient = useQueryClient();
  const { setSelectedKubeconfig } = useStore();
  const [error, setError] = useState('');
  
  // Fetch kubeconfigs
  const { data, isLoading, isError } = useQuery({
    queryKey: ['kubeconfigs'],
    queryFn: kubeconfigService.list,
  });
  
  // Activate kubeconfig mutation
  const activateMutation = useMutation({
    mutationFn: kubeconfigService.activate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kubeconfigs'] });
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to activate kubeconfig');
    },
  });
  
  // Remove kubeconfig mutation
  const removeMutation = useMutation({
    mutationFn: kubeconfigService.removeKubeconfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kubeconfigs'] });
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to remove kubeconfig');
    },
  });
  
  const handleActivate = (filename: string) => {
    activateMutation.mutate(filename);
  };
  
  const handleRemove = (filename: string) => {
    if (window.confirm('Are you sure you want to remove this kubeconfig?')) {
      removeMutation.mutate(filename);
    }
  };
  
  if (isLoading) return <div>Loading kubeconfigs...</div>;
  if (isError) return <Alert variant="danger">Failed to load kubeconfigs</Alert>;
  
  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>Kubeconfig Files</h1>
        <Link href="/clusters/upload" passHref>
          <Button variant="primary">Upload New Kubeconfig</Button>
        </Link>
      </div>
      
      {error && <Alert variant="danger">{error}</Alert>}
      
      <Card>
        <Card.Body>
          {data.kubeconfigs.length === 0 ? (
            <Alert variant="info">
              No kubeconfig files found. Upload your first kubeconfig file to get started.
            </Alert>
          ) : (
            <Table responsive hover>
              <thead>
                <tr>
                  <th>Cluster Name</th>
                  <th>Original Filename</th>
                  <th>Status</th>
                  <th>Operator</th>
                  <th>Created At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.kubeconfigs.map((config) => (
                  <tr key={config.id}>
                    <td>{config.cluster_name || 'Unknown'}</td>
                    <td>{config.original_filename}</td>
                    <td>
                      {config.active ? (
                        <Badge bg="success">Active</Badge>
                      ) : (
                        <Badge bg="secondary">Inactive</Badge>
                      )}
                    </td>
                    <td>
                      {config.is_operator_installed ? (
                        <Badge bg="info">Installed</Badge>
                      ) : (
                        <Badge bg="warning">Not Installed</Badge>
                      )}
                    </td>
                    <td>{new Date(config.created_at).toLocaleString()}</td>
                    <td>
                      <div className="d-flex gap-2">
                        {!config.active && (
                          <Button
                            size="sm"
                            variant="outline-primary"
                            onClick={() => handleActivate(config.filename)}
                            disabled={activateMutation.isPending}
                          >
                            Activate
                          </Button>
                        )}
                        
                        {config.active && !config.is_operator_installed && (
                          <Link href="/clusters/operator" passHref>
                            <Button
                              size="sm"
                              variant="outline-info"
                              onClick={() => setSelectedKubeconfig(config)}
                            >
                              Install Operator
                            </Button>
                          </Link>
                        )}
                        
                        <Button
                          size="sm"
                          variant="outline-danger"
                          onClick={() => handleRemove(config.filename)}
                          disabled={removeMutation.isPending}
                        >
                          Remove
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </div>
  );
}
