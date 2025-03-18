'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { userService } from '../../../lib/api';
import { Card, Form, Button, Alert } from 'react-bootstrap';
import { useRouter } from 'next/navigation';

export default function ChangePasswordPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  
  const changePasswordMutation = useMutation({
    mutationFn: (data) => userService.changePassword(data),
    onSuccess: () => {
      setSuccess(true);
      setFormData({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });
      
      // Redirect to profile after 2 seconds
      setTimeout(() => {
        router.push('/me');
      }, 2000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to change password');
    },
  });
  
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    // Validate passwords
    if (formData.new_password !== formData.confirm_password) {
      setError('New passwords do not match');
      return;
    }
    
    if (formData.new_password.length < 8) {
      setError('New password must be at least 8 characters long');
      return;
    }
    
    // Submit data
    changePasswordMutation.mutate({
      current_password: formData.current_password,
      new_password: formData.new_password,
    });
  };
  
  return (
    <div className="d-flex justify-content-center">
      <Card className="auth-form">
        <Card.Body>
          <h2 className="text-center mb-4">Change Password</h2>
          
          {error && <Alert variant="danger">{error}</Alert>}
          {success && (
            <Alert variant="success">
              Password changed successfully! Redirecting...
            </Alert>
          )}
          
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Current Password</Form.Label>
              <Form.Control
                type="password"
                name="current_password"
                value={formData.current_password}
                onChange={handleInputChange}
                required
                disabled={success}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>New Password</Form.Label>
              <Form.Control
                type="password"
                name="new_password"
                value={formData.new_password}
                onChange={handleInputChange}
                required
                disabled={success}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Confirm New Password</Form.Label>
              <Form.Control
                type="password"
                name="confirm_password"
                value={formData.confirm_password}
                onChange={handleInputChange}
                required
                disabled={success}
              />
            </Form.Group>
            
            <div className="d-flex justify-content-between mt-4">
              <Button
                variant="secondary"
                onClick={() => router.push('/me')}
                disabled={changePasswordMutation.isPending || success}
              >
                Cancel
              </Button>
              
              <Button
                variant="primary"
                type="submit"
                disabled={changePasswordMutation.isPending || success}
              >
                {changePasswordMutation.isPending ? 'Changing...' : 'Change Password'}
              </Button>
            </div>
          </Form>
        </Card.Body>
      </Card>
    </div>
  );
}
