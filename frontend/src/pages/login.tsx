import React from "react";
import { useHistory } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon } from "@iconify/react";
import {
  Card,
  CardBody,
  CardHeader,
  Input,
  Button,
  Checkbox,
  Divider,
  addToast
} from "@heroui/react";
 
export const LoginPage: React.FC<{ onLogin?: (username: string, password: string) => boolean }> = ({ onLogin = () => true }) => {
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [rememberMe, setRememberMe] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);
  const [errors, setErrors] = React.useState({ username: "", password: "" });
  const history = useHistory();
  
  const validateForm = () => {
    const newErrors = { username: "", password: "" };
    let isValid = true;
    
    if (!username) {
      newErrors.username = "Username is required";
      isValid = false;
    }
    
    if (!password) {
      newErrors.password = "Password is required";
      isValid = false;
    } else if (password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
      isValid = false;
    }
    
    setErrors(newErrors);
    return isValid;
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
 
    if (!validateForm()) return;
 
    setIsLoading(true);
 
    try {
      const response = await fetch("https://10.0.32.105:8001/auth/token", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded"
        },
        body: new URLSearchParams({
          username: username.trim(),
          password: password.trim()
        }).toString()
      });
 
      if (response.ok) {
        const data = await response.json();
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);

        // Fetch user info to get roles
        const userRes = await fetch("https://10.0.32.105:8001/users/me", {
          headers: {
            "Authorization": `Bearer ${data.access_token}`,
            "accept": "application/json"
          }
        });
        if (userRes.ok) {
          const userData = await userRes.json();
          console.log("User data:", userData); // Debugging line
          localStorage.setItem("roles", JSON.stringify(userData.roles || []));

          // Fetch permissions from backend
          try {
            const permRes = await fetch("https://10.0.32.105:8001/users/permissions", {
              method: "GET",
              headers: {
                "Authorization": `Bearer ${data.access_token}`,
                "Accept": "application/json"
              }
            });
            if (permRes.ok) {
              const permData = await permRes.json();
              localStorage.setItem("permissions", JSON.stringify(permData.permissions || []));
            } else {
              localStorage.setItem("permissions", "[]");
            }
          } catch (error) {
            console.error("Failed to fetch permissions:", error);
            localStorage.setItem("permissions", "[]");
          }
        } else {
          localStorage.setItem("roles", "[]");
        }

        addToast({
          title: "Login Successful",
          description: "Welcome to KubeSage Dashboard",
          color: "success"
        });
        try {
          onLogin(username, password);
        } catch (err) {
          console.error("Error in onLogin callback:", err);
          addToast({
            title: "Login Failed",
            description: "An error occurred during login callback",
            color: "danger"
          });
          setIsLoading(false);
          return;
        }
        history.push("/dashboard");
      } else {
        console.error("Login failed: Invalid username or password");
        addToast({
          title: "Login Failed",
          description: "Invalid username or password",
          color: "danger"
        });
      }
    } catch (error) {
      console.error("Login failed: An error occurred during login", error);
      addToast({
        title: "Login Failed",
        description: "An error occurred during login",
        color: "danger"
      });
    } finally {
      setIsLoading(false);
    }
  };
 
  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    addToast({
      title: "Logged Out",
      description: "You have been logged out successfully",
      color: "primary"
    });
    history.push("/login");
  };
////  
  const roles = JSON.parse(localStorage.getItem("roles") || "[]");
  console.log("User roles:", roles); // Debugging line
  React.useEffect(() => {
    if (roles.includes("super_admin")) {
      // Redirect to admin UI or perform admin-specific logic
      console.log("Super Admin access granted"); // Debugging line
      // history.push("/admin"); // Uncomment this line to enable redirection to admin page
    }
  }, [roles, history]);
  ////
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background to-content2">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Card className="backdrop-blur-md bg-content1/90 shadow-xl border border-content2">
          <CardHeader className="flex flex-col items-center gap-2 pb-0">
            <motion.div
              className="w-16 h-16 rounded-xl bg-primary flex items-center justify-center mb-2"
              whileHover={{ scale: 1.05, rotate: 5 }}
              whileTap={{ scale: 0.95 }}
            >
              <Icon icon="lucide:layers" className="text-white text-3xl" />
            </motion.div>
            <h1 className="text-2xl font-bold">KubeSage</h1>
            <p className="text-foreground-500 text-center">
              AI-Powered Kubernetes Management
            </p>
          </CardHeader>
          
          <CardBody className="py-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Username"
                placeholder="Enter your username"
                type="text"
                value={username}
                onValueChange={setUsername}
                startContent={<Icon icon="lucide:mail" className="text-foreground-400" />}
                isInvalid={!!errors.username}
                errorMessage={errors.username}
                isDisabled={isLoading}
              />
              
              <Input
                label="Password"
                placeholder="Enter your password"
                type="password"
                value={password}
                onValueChange={setPassword}
                startContent={<Icon icon="lucide:lock" className="text-foreground-400" />}
                isInvalid={!!errors.password}
                errorMessage={errors.password}
                isDisabled={isLoading}
              />
              
              <div className="flex items-center justify-between">
                <Checkbox
                  size="sm"
                  isSelected={rememberMe}
                  onValueChange={setRememberMe}
                  isDisabled={isLoading}
                >
                  Remember me
                </Checkbox>
                <Button variant="light" size="sm" className="p-0" isDisabled={isLoading}>
                  Forgot password?
                </Button>
              </div>
              
              <Button
                color="primary"
                type="submit"
                fullWidth
                isLoading={isLoading}
                startContent={!isLoading && <Icon icon="lucide:log-in" />}
              >
                Sign In
              </Button>
              
             
            </form>
          </CardBody>
        </Card>
        
        
      </motion.div>
    </div>
  );
};

