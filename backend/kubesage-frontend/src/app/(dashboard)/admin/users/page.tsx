'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userService } from '../../../../lib/api';
import { Table, Button, Card, Badge, Alert, Modal, Form } from 'react-bootstrap';
import { useState } from 'react';
import { useSession } from 'next-auth/react';

export default function UserManagementPage() {
  const { data: session } = useSession();
  const queryClient = useQueryClient();
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    is_active: true,
    is_admin: false
  });
  
  // Fetch users
  const { data: users, isLoading, isError } = useQuery({
    queryKey: ['users'],
    queryFn: userService.getUsers,
  });
  
  // Delete user mutation
  const deleteMutation = useMutation({
    mutationFn: userService.deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
  
  // Update user mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => userService.updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      handleCloseModal();
    },
  });
  
  const handleDelete = (userId) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      deleteMutation.mutate(userId);
    }
  };
  
  const handleEdit = (user) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      is_active: user.is_active,
      is_admin: user.is_admin
    });
    setShowEditModal(true);
  };
  
  const handleCloseModal = () => {
    setShowEditModal(false);
    setEditingUser(null);
  };
  
  const handleInputChange = (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setFormData({
      ...formData,
      [e.target.name]: value
    });
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (editingUser) {
      updateMutation.mutate({
        id: editingUser.id,
        data: formData
      });
    }
  };
  
  if (isLoading) return <div>Loading users...</div>;
  if (isError) return <Alert variant="danger">Failed to load users</Alert>;
  
  return (
    <div>
      <h1 className="mb-4">User Management</h1>
      
      <Card>
        <Card.Body>
          <Table responsive hover>
            <thead>
              <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Email</th>
                <th>Name</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
                          {users.map((user) => (
                            <tr key={user.id}>
                              <td>{user.id}</td>
                              <td>{user.username}</td>
                              <td>{user.email}</td>
                              <td>{user.first_name} {user.last_name}</td>
                              <td>
                                {user.is_admin ? (
                                  <Badge bg="primary">Admin</Badge>
                                ) : (
                                  <Badge bg="secondary">User</Badge>
                                )}
                              </td>
                              <td>
                                {user.is_active ? (
                                  <Badge bg="success">Active</Badge>
                                ) : (
                                  <Badge bg="danger">Inactive</Badge>
                                )}
                              </td>
                              <td>
                                <div className="d-flex gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline-primary"
                                    onClick={() => handleEdit(user)}
                                  >
                                    Edit
                                  </Button>
                      
                                  {session?.user?.id !== user.id && (
                                    <Button
                                      size="sm"
                                      variant="outline-danger"
                                      onClick={() => handleDelete(user.id)}
                                      disabled={deleteMutation.isPending}
                                    >
                                      Delete
                                    </Button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    </Card.Body>
                  </Card>
      
                  {/* Edit User Modal */}
                  <Modal show={showEditModal} onHide={handleCloseModal}>
                    <Modal.Header closeButton>
                      <Modal.Title>Edit User</Modal.Title>
                    </Modal.Header>
                    <Modal.Body>
                      <Form onSubmit={handleSubmit}>
                        <Form.Group className="mb-3">
                          <Form.Label>Username</Form.Label>
                          <Form.Control
                            type="text"
                            name="username"
                            value={formData.username}
                            onChange={handleInputChange}
                            required
                          />
                        </Form.Group>
            
                        <Form.Group className="mb-3">
                          <Form.Label>Email</Form.Label>
                          <Form.Control
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleInputChange}
                            required
                          />
                        </Form.Group>
            
                        <Form.Group className="mb-3">
                          <Form.Label>First Name</Form.Label>
                          <Form.Control
                            type="text"
                            name="first_name"
                            value={formData.first_name}
                            onChange={handleInputChange}
                            required
                          />
                        </Form.Group>
            
                        <Form.Group className="mb-3">
                          <Form.Label>Last Name</Form.Label>
                          <Form.Control
                            type="text"
                            name="last_name"
                            value={formData.last_name}
                            onChange={handleInputChange}
                            required
                          />
                        </Form.Group>
            
                        <Form.Group className="mb-3">
                          <Form.Check
                            type="checkbox"
                            label="Active"
                            name="is_active"
                            checked={formData.is_active}
                            onChange={handleInputChange}
                          />
                        </Form.Group>
            
                        <Form.Group className="mb-3">
                          <Form.Check
                            type="checkbox"
                            label="Administrator"
                            name="is_admin"
                            checked={formData.is_admin}
                            onChange={handleInputChange}
                          />
                        </Form.Group>
                      </Form>
                    </Modal.Body>
                    <Modal.Footer>
                      <Button variant="secondary" onClick={handleCloseModal}>
                        Cancel
                      </Button>
                      <Button 
                        variant="primary" 
                        onClick={handleSubmit}
                        disabled={updateMutation.isPending}
                      >
                        {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                      </Button>
                    </Modal.Footer>
                  </Modal>
                </div>
              )