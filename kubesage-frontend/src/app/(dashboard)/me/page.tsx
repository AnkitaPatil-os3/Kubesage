'use client';

import { useQuery } from '@tanstack/react-query';
import { userService } from '../../../lib/api';
import { Card, ListGroup, Button } from 'react-bootstrap';
import Link from 'next/link';

export default function ProfilePage() {
  const { data: user, isLoading, isError } = useQuery({
    queryKey: ['user-profile'],
    queryFn: userService.getProfile,
  });
  
  if (isLoading) return <div>Loading profile...</div>;
  if (isError) return <div>Error loading profile</div>;
  
  return (
    <div className="row justify-content-center">
      <div className="col-md-8">
        <Card>
          <Card.Header as="h4">User Profile</Card.Header>
          <Card.Body>
            <div className="text-center mb-4">
              <div className="avatar-placeholder bg-primary text-white rounded-circle d-flex align-items-center justify-content-center mx-auto mb-3" style={{ width: '100px', height: '100px', fontSize: '2.5rem' }}>
                {user.first_name.charAt(0)}{user.last_name.charAt(0)}
              </div>
              <h3>{user.first_name} {user.last_name}</h3>
              <p className="text-muted">{user.username}</p>
            </div>
            
            <ListGroup variant="flush">
              <ListGroup.Item>
                <strong>Username:</strong> {user.username}
              </ListGroup.Item>
              <ListGroup.Item>
                <strong>Email:</strong> {user.email}
              </ListGroup.Item>
              <ListGroup.Item>
                <strong>First Name:</strong> {user.first_name}
              </ListGroup.Item>
              <ListGroup.Item>
                <strong>Last Name:</strong> {user.last_name}
              </ListGroup.Item>
              <ListGroup.Item>
                <strong>Role:</strong> {user.is_admin ? 'Administrator' : 'User'}
              </ListGroup.Item>
              <ListGroup.Item>
                <strong>Account Status:</strong>{' '}
                <span className={`badge ${user.is_active ? 'bg-success' : 'bg-danger'}`}>
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </ListGroup.Item>
              <ListGroup.Item>
                <strong>Created:</strong>{' '}
                {new Date(user.created_at).toLocaleDateString()}
              </ListGroup.Item>
            </ListGroup>
            
            <div className="d-flex justify-content-center mt-4">
              <Link href="/change-password" passHref>
                <Button variant="outline-primary">Change Password</Button>
              </Link>
            </div>
          </Card.Body>
        </Card>
      </div>
    </div>
  );
}
