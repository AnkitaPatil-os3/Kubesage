import React, { useState, useEffect } from "react";
import { Chip } from "@heroui/react";
import { Icon } from "@iconify/react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  Input,
  Select,
  SelectItem,
  Checkbox,
  Avatar,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableColumn,
  TableHeader,
  TableRow,
} from "@heroui/react";
import { jwtDecode } from "jwt-decode";

// Replace with your actual role options
const ROLE_OPTIONS = ["Super Admin", "Admin", "User"];

const API_BASE_URL = (import.meta as any).env.VITE_USER_SERVICE;

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  roles: any; // Can be string or array
}

interface NewUser {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  roles: string[];
}

interface EditUser extends Omit<NewUser, "password"> {
  password?: string;
}

// INLINE AUTH LOGIC
const isTokenValid = (token: string | null): boolean => {
  if (!token) return false;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return false;
    const decoded: any = jwtDecode(token);
    return decoded.exp > Date.now() / 1000;
  } catch {
    return false;
  }
};

const getValidToken = (): string | null => {
  const token = localStorage.getItem("access_token");
  if (!isTokenValid(token)) {
    localStorage.removeItem("access_token");
    return null;
  }
  return token;
};

const checkAdminStatus = async (): Promise<boolean> => {
  const token = getValidToken();
  if (!token) return false;
  try {
    const res = await fetch(`${API_BASE_URL}/auth/check-admin`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return false;
    const data = await res.json();
    return data.is_admin === true;
  } catch {
    return false;
  }
};

export const UsersAndRBAC: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showAddUser, setShowAddUser] = useState(false);
  const [newUser, setNewUser] = useState<NewUser>({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    is_active: true,
    roles: [],
  });

  const [showEditUser, setShowEditUser] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [editUser, setEditUser] = useState<EditUser>({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    is_active: true,
    roles: [],
    password: "",
  });

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Fetch and normalize users
  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    const token = getValidToken();
    if (!token) return setError("Token invalid. Please login.");

    if (!(await checkAdminStatus())) {
      setError("Admin privileges required.");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/users/?skip=0&limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const text = await res.text();
      if (!res.ok) {
        setError(`Failed to fetch users: ${text}`);
      } else {
        const data = JSON.parse(text);
        const normalized = (Array.isArray(data) ? data : []).map((u: any) => ({
          ...u,
          roles: Array.isArray(u.roles)
            ? u.roles
            : typeof u.roles === "string"
            ? [u.roles]
            : [],
        }));
        setUsers(normalized);
      }
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const token = getValidToken();
    if (!token) {
      setError("Token invalid");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newUser),
      });
      const text = await res.text();
      if (!res.ok) {
        setError(`Add user failed: ${text}`);
      } else {
        setShowAddUser(false);
        setNewUser({ username: "", email: "", password: "", first_name: "", last_name: "", is_active: true, roles: [] });
        fetchUsers();
      }
    } catch {
      setError("Network error adding user");
    } finally {
      setLoading(false);
    }
  };

  const openEditModal = (u: User) => {
    setSelectedUser(u);
    setEditUser({
      username: u.username,
      email: u.email,
      first_name: u.first_name,
      last_name: u.last_name,
      is_active: Boolean(u.is_active),
      roles: Array.isArray(u.roles) ? u.roles : [],
      password: "",
    });
    setShowEditUser(true);
  };

  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    setLoading(true);
    const token = getValidToken();
    if (!token) {
      setError("Token invalid");
      setLoading(false);
      return;
    }

    try {
      const body: any = {
        username: editUser.username,
        email: editUser.email,
        first_name: editUser.first_name,
        last_name: editUser.last_name,
        is_active: editUser.is_active,
        roles: editUser.roles,
      };
      if (editUser.password) body.password = editUser.password;

      const res = await fetch(`${API_BASE_URL}/users/${selectedUser.id}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      const text = await res.text();
      if (!res.ok) {
        setError(`Edit failed: ${text}`);
      } else {
        setShowEditUser(false);
        fetchUsers();
      }
    } catch {
      setError("Network error editing user");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    setLoading(true);
    const token = getValidToken();
    if (!token) {
      setError("Token invalid");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/users/${selectedUser.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      const text = await res.text();
      if (!res.ok) {
        setError(`Delete failed: ${text}`);
      } else {
        setShowDeleteConfirm(false);
        setSelectedUser(null);
        fetchUsers();
      }
    } catch {
      setError("Network error deleting user");
    } finally {
      setLoading(false);
    }
  };

  const getInitials = (name: string) =>
    name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase();

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-semibold">Users & RBAC</h2>
        <Button color="primary" onClick={() => setShowAddUser(true)} startContent={<Icon icon="lucide:user-plus" />}>
          Add User
        </Button>
      </div>

      {error && <p className="text-sm text-red-500 mb-4">{error}</p>}

      <Card>
        <Table isStriped aria-label="User list">
          <TableHeader>
            <TableColumn>Username</TableColumn>
            <TableColumn>Email</TableColumn>
            <TableColumn>Roles</TableColumn>
            <TableColumn>Status</TableColumn>
            <TableColumn>Actions</TableColumn>
          </TableHeader>
          <TableBody>
            {users.map((u) => (
              <TableRow key={u.id}>
                <TableCell>{u.username}</TableCell>
                <TableCell>{u.email}</TableCell>
                <TableCell>
                  {Array.isArray(u.roles) ? (
                    u.roles.map((role, idx) => (
                      <Chip key={idx} size="sm">
                        {role}
                      </Chip>
                    ))
                  ) : (
                    <Chip size="sm" color="warning">
                      {u.roles || "No roles"}
                    </Chip>
                  )}
                </TableCell>
                <TableCell>
                  <Chip color={u.is_active ? "success" : "default"} size="sm">
                    {u.is_active ? "Active" : "Inactive"}
                  </Chip>
                </TableCell>
                <TableCell>
                  <Tooltip content="Edit User">
                    <Button onClick={() => openEditModal(u)} size="sm" variant="light" isIconOnly>
                      <Icon icon="lucide:edit-2" />
                    </Button>
                  </Tooltip>
                  <Tooltip content="Delete User">
                    <Button
                      onClick={() => {
                        setSelectedUser(u);
                        setShowDeleteConfirm(true);
                      }}
                      size="sm"
                      variant="light"
                      color="danger"
                      isIconOnly
                    >
                      <Icon icon="lucide:trash-2" />
                    </Button>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Add User Modal */}
      <Modal isOpen={showAddUser} onOpenChange={setShowAddUser} placement="top-center" size="2xl">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:user-plus" className="text-primary text-2xl" />
                  <span className="text-xl font-bold">Add New User</span>
                </div>
                <p className="text-sm text-foreground-500 font-normal">
                  Fill in the details to create a new user account
                </p>
              </ModalHeader>
              <form onSubmit={handleAddUser}>
                <ModalBody className="p-6 space-y-6">
                  <Card className="bg-content2 border border-divider">
                    <CardHeader>
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Icon icon="lucide:user" className="text-secondary" />
                        Basic Information
                      </h3>
                    </CardHeader>
                    <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Input autoFocus label="Username" placeholder="Enter username" variant="bordered" value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} startContent={<Icon icon="lucide:at-sign" className="text-foreground-400" />} isRequired />
                      <Input label="Email" placeholder="Enter email" type="email" variant="bordered" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} startContent={<Icon icon="lucide:mail" className="text-foreground-400" />} isRequired />
                      <Input label="First Name" placeholder="Enter first name" variant="bordered" value={newUser.first_name} onChange={(e) => setNewUser({ ...newUser, first_name: e.target.value })} startContent={<Icon icon="lucide:user" className="text-foreground-400" />} isRequired />
                      <Input label="Last Name" placeholder="Enter last name" variant="bordered" value={newUser.last_name} onChange={(e) => setNewUser({ ...newUser, last_name: e.target.value })} startContent={<Icon icon="lucide:user" className="text-foreground-400" />} isRequired />
                    </CardBody>
                  </Card>

                  <Card className="bg-content2 border border-divider">
                    <CardHeader>
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Icon icon="lucide:lock" className="text-warning" />
                        Security & Access
                      </h3>
                    </CardHeader>
                    <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Input label="Password" placeholder="Enter password" type="password" variant="bordered" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} startContent={<Icon icon="lucide:key" className="text-foreground-400" />} isRequired />
                      <Select label="Roles" placeholder="Select roles" variant="bordered" selectionMode="multiple" selectedKeys={newUser.roles} onSelectionChange={(keys) => setNewUser({ ...newUser, roles: Array.from(keys) as string[] })} startContent={<Icon icon="lucide:shield" className="text-primary" />} isRequired>
                        {ROLE_OPTIONS.map((role) => (
                          <SelectItem key={role}>{role}</SelectItem>
                        ))}
                      </Select>
                      <div className="flex items-center gap-2 mt-2 md:col-span-2">
                        <Checkbox isSelected={newUser.is_active} onValueChange={(checked) => setNewUser({ ...newUser, is_active: checked })} color="success">
                          <span className="font-medium">Active User</span>
                        </Checkbox>
                      </div>
                    </CardBody>
                  </Card>
                </ModalBody>
                <ModalFooter>
                  <Button color="danger" variant="flat" onPress={onClose}>
                    Cancel
                  </Button>
                  <Button color="primary" type="submit" isLoading={loading} endContent={<Icon icon="lucide:user-plus" />}>
                    Add User
                  </Button>
                </ModalFooter>
              </form>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Edit User Modal (similar to Add, with pre-fill) */}
      <Modal isOpen={showEditUser} onOpenChange={setShowEditUser} placement="top-center" size="2xl">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:edit-2" className="text-primary" />
                  <span>Edit User</span>
                </div>
                {selectedUser && (
                  <p className="text-sm text-foreground-500">
                    Editing: {selectedUser.first_name} {selectedUser.last_name} (@{selectedUser.username})
                  </p>
                )}
              </ModalHeader>
              <form onSubmit={handleEditUser}>
                <ModalBody className="p-6 space-y-6">
                  <Card className="bg-content2 border border-divider">
                    <CardHeader>
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Icon icon="lucide:user" className="text-secondary" />
                        Basic Information
                      </h3>
                    </CardHeader>
                    <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Input autoFocus label="Username" variant="bordered" value={editUser.username} onChange={(e) => setEditUser({ ...editUser, username: e.target.value })} isRequired />
                      <Input label="Email" type="email" variant="bordered" value={editUser.email} onChange={(e) => setEditUser({ ...editUser, email: e.target.value })} isRequired />
                      <Input label="First Name" variant="bordered" value={editUser.first_name} onChange={(e) => setEditUser({ ...editUser, first_name: e.target.value })} isRequired />
                      <Input label="Last Name" variant="bordered" value={editUser.last_name} onChange={(e) => setEditUser({ ...editUser, last_name: e.target.value })} isRequired />
                    </CardBody>
                  </Card>

                  <Card className="bg-content2 border border-divider">
                    <CardHeader>
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Icon icon="lucide:lock" className="text-warning" />
                        Security & Access
                      </h3>
                    </CardHeader>
                    <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Input label="New Password" type="password" variant="bordered" placeholder="Leave empty to keep current" value={editUser.password || ""} onChange={(e) => setEditUser({ ...editUser, password: e.target.value })} description="Leave empty to keep current password" />
                      <Select label="Roles" selectionMode="multiple" variant="bordered" selectedKeys={editUser.roles} onSelectionChange={(keys) => setEditUser({ ...editUser, roles: Array.from(keys) as string[] })} isRequired>
                        {ROLE_OPTIONS.map((role) => (
                          <SelectItem key={role}>{role}</SelectItem>
                        ))}
                      </Select>
                      <div className="flex items-center gap-2 mt-2 md:col-span-2">
                        <Checkbox isSelected={editUser.is_active} onValueChange={(checked) => setEditUser({ ...editUser, is_active: checked })} color="success">
                          <span className="font-medium">Active User</span>
                        </Checkbox>
                      </div>
                    </CardBody>
                  </Card>
                </ModalBody>
                <ModalFooter>
                  <Button color="danger" variant="flat" onPress={() => { onClose(); setSelectedUser(null); }}>
                    Cancel
                  </Button>
                  <Button color="primary" type="submit" isLoading={loading}>
                    Update User
                  </Button>
                </ModalFooter>
              </form>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal isOpen={showDeleteConfirm} onOpenChange={setShowDeleteConfirm} placement="top-center" size="md">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Icon icon="lucide:alert-triangle" className="text-danger" />
                  <span>Confirm Delete</span>
                </div>
              </ModalHeader>
              <ModalBody className="space-y-4">
                {selectedUser && (
                  <>
                    <p>Are you sure you want to delete this user? This action cannot be undone.</p>
                    <Card className="bg-danger/10 border border-danger/20">
                      <CardBody className="p-4 flex items-center gap-3">
                        <Avatar name={getInitials(`${selectedUser.first_name} ${selectedUser.last_name}`)} size="sm" />
                        <div>
                          <p className="font-medium">{selectedUser.first_name} {selectedUser.last_name}</p>
                          <p className="text-xs">{selectedUser.email}</p>
                          <p className="text-xs">@{selectedUser.username}</p>
                        </div>
                      </CardBody>
                    </Card>
                    <div className="bg-warning/10 border border-warning/20 rounded-lg p-3">
                      <div className="flex items-start gap-2">
                        <Icon icon="lucide:alert-triangle" className="text-warning mt-1" />
                        <div>
                          <p className="font-medium text-warning">Warning</p>
                          <p>Deleting this user removes all their data permanently.</p>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </ModalBody>
              <ModalFooter>
                <Button color="default" variant="flat" onPress={() => { onClose(); setSelectedUser(null); }}>
                  Cancel
                </Button>
                <Button color="danger" onPress={handleDeleteUser} isLoading={loading} startContent={<Icon icon="lucide:trash-2" />}>
                  Delete User
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
};
