'use client';

import { useQuery } from '@tanstack/react-query';
import { kubeconfigService } from '../../../../lib/api';
import { Card, Alert, ListGroup, Button, Badge } from 'react-bootstrap';
import { useState } from 'react';
import Link from 'next/link';

export default function NamespacesPage() {
  const [selectedNamespace, setSelectedNamespace] = useState<string | null>(null);
  
  const { 
    data: namespaceData, 
    isLoading, 
    isError, 
    error 
  } = useQuery({
    queryKey: ['namespaces'],
    queryFn: kubeconfigService.getNamespaces,
    retry: 1,
    onError: (err: any) => {
      console.error('Error fetching namespaces:', err);
    }
  });
  
  // Handle no active kubeconfig
  if (isError) {
    const errorMessage = error instanceof Error 
      ? error.message 
      : 'Unknown error';
      
    // Check for specific error messages
    if (errorMessage.includes('No active kubeconfig')) {
      return (
        <Alert variant="warning">
          <Alert.Heading>No Active Kubeconfig</Alert.Heading>
          <p>
            You need to activate a kubeconfig file before you can view namespaces.
          </p>
          <hr />
          <div className="d-flex justify-content-end">
            <Link href="/clusters/list" passHref>
              <Button variant="outline-primary">
                Go to Kubeconfig List
              </Button>
            </Link>
          </div>
        </Alert>
      );
    }
    
    return (
      <Alert variant="danger">
        <Alert.Heading>Error Loading Namespaces</Alert.Heading>
        <p>{errorMessage}</p>
      </Alert>
    );
  }
  
  if (isLoading) {
    return <div>Loading namespaces...</div>;
  }
  
  return (
    <div>
      <h1 className="mb-4">Kubernetes Namespaces</h1>
      
      <Card>
        <Card.Header>
          <div className="d-flex justify-content-between align-items-center">
            <span>Available Namespaces</span>
            <Badge bg="primary">
              {namespaceData.namespaces.length} namespaces found
            </Badge>
          </div>
        </Card.Header>
        <Card.Body>
          <ListGroup>
            {namespaceData.namespaces.map((namespace) => (
              <ListGroup.Item 
                key={namespace}
                action
                active={selectedNamespace === namespace}
                onClick={() => setSelectedNamespace(namespace)}
                className="d-flex justify-content-between align-items-center"
              >
                {namespace}
                
                {isSystemNamespace(namespace) && (
                  <Badge bg="secondary">System</Badge>
                )}
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Card.Body>
      </Card>
    </div>
  );
}

// Helper function to identify system namespaces
function isSystemNamespace(namespace: string): boolean {
  const systemNamespaces = [
    'kube-system', 
    'kube-public', 
    'kube-node-lease',
    'default',
    'k8sgpt-operator-system'
  ];
  return systemNamespaces.includes(namespace);
}
