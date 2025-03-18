'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { kubeconfigService } from '../../../../lib/api';
import { Form, Button, Card, Alert, ProgressBar } from 'react-bootstrap';

export default function UploadKubeconfigPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  
  const uploadMutation = useMutation({
    mutationFn: kubeconfigService.upload,
    onSuccess: () => {
      router.push('/clusters/list');
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Upload failed');
      setUploading(false);
    },
  });
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file to upload');
      return;
    }
    
    setUploading(true);
    setError('');
    
    // Simulate upload progress
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        const newProgress = prev + 5;
        if (newProgress >= 95) {
          clearInterval(progressInterval);
          return 95; // Wait for actual completion
        }
        return newProgress;
      });
    }, 100);
    
    try {      await uploadMutation.mutateAsync(file);
      clearInterval(progressInterval);
      setUploadProgress(100);
    } catch (error) {
      clearInterval(progressInterval);
      // Error is handled by the mutation's onError
    }
  };
  
  return (
    <div className="d-flex justify-content-center">
      <Card className="auth-form">
        <Card.Body>
          <h2 className="text-center mb-4">Upload Kubeconfig</h2>
          
          {error && <Alert variant="danger">{error}</Alert>}
          
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Kubeconfig File</Form.Label>
              <Form.Control
                type="file"
                onChange={handleFileChange}
                disabled={uploading}
                accept=".yaml,.yml,.conf,.config,.txt"
              />
              <Form.Text className="text-muted">
                Select your Kubernetes configuration file
              </Form.Text>
            </Form.Group>
