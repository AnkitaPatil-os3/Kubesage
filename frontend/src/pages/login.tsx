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
import authService from "../services/auth";
 
export const LoginPage: React.FC<{ onLogin?: (username: string, password: string) => boolean }> = ({ onLogin = () => true }) => {
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [rememberMe, setRememberMe] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);
  const [errors, setErrors] = React.useState({ username: "", password: "" });
  const [authCheckComplete, setAuthCheckComplete] = React.useState(false);
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
      // Use enhanced auth service
      const result = await authService.login(username.trim(), password.trim());
      
      if (result.success && result.user) {
        // Store user roles for role-based access
        localStorage.setItem("roles", JSON.stringify(result.user.roles || []));
        localStorage.setItem("username", result.user.username);
        
        addToast({
          title: "Login Successful",
          description: `Welcome back, ${result.user.username}!`,
          color: "success"
        });
        
        try {
          onLogin(username, password);
        } catch (err) {
          console.error("Error in onLogin callback:", err);
          addToast({
            title: "Login Warning",
            description: "Login successful but callback failed",
            color: "warning"
          });
        }
        
        // Check for admin redirect
        const roles = result.user.roles || "";
        if (roles.includes("Super Admin")) {
          console.log("Super Admin access granted");
          // Uncomment to enable admin redirect
          // history.push("/admin");
        }
        
        history.push("/dashboard");
      } else {
        console.error("Login failed:", result.error);
        addToast({
          title: "Login Failed",
          description: result.error || "Invalid username or password",
          color: "danger"
        });
      }
    } catch (error: any) {
      console.error("Login failed: An error occurred during login", error);
      addToast({
        title: "Login Failed",
        description: error.message || "An error occurred during login",
        color: "danger"
      });
    } finally {
      setIsLoading(false);
    }
  };
 
  const handleLogout = async () => {
    try {
      await authService.logout();
      addToast({
        title: "Logged Out",
        description: "You have been logged out successfully",
        color: "primary"
      });
      history.push("/login");
    } catch (error) {
      console.error("Logout error:", error);
      addToast({
        title: "Logout Error",
        description: "Error occurred during logout",
        color: "danger"
      });
    }
  };
 
  // Check if user is already authenticated - FIXED VERSION
  React.useEffect(() => {
    const checkExistingAuth = async () => {
      try {
        // Only check if we haven't completed auth check yet
        if (authCheckComplete) return;
 
        console.log("Checking existing authentication...");
        
        if (authService.isAuthenticated()) {
          console.log("User already authenticated, checking with backend...");
          
          // Verify with backend without causing infinite loop
          const cachedUser = authService.getCachedUserInfo();
          if (cachedUser) {db
            console.log("User already authenticated, redirecting...");
            history.replace("/dashboard"); // Use replace instead of push to avoid history issues
            return;
          }
          
          // If no cached user, try to get current user
          try {
            const user = await authService.getCurrentUser();
            if (user) {
              console.log("Backend authentication verified, redirecting...");
              history.replace("/dashboard");
              return;
            }
          } catch (error) {
            console.log("Backend authentication failed, staying on login");
            // Clear invalid auth data
            authService.clearAuthData();
          }
        }
        
        console.log("No valid authentication found, staying on login page");
      } catch (error) {
        console.error("Auth check error:", error);
        authService.clearAuthData();
      } finally {
        setAuthCheckComplete(true);
      }
    };
 
    checkExistingAuth();
  }, []); // Remove authCheckComplete from dependencies to prevent loop
 
  // Don't render login form until auth check is complete
  if (!authCheckComplete) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background to-content2">
        <div className="text-center">
          <div className="w-16 h-16 rounded-xl bg-primary flex items-center justify-center mb-4 mx-auto">
            <Icon icon="lucide:layers" className="text-white text-3xl" />
          </div>
          <h1 className="text-2xl font-bold mb-2">KubeSage</h1>
          <p className="text-foreground-500">Checking authentication...</p>
        </div>
      </div>
    );
  }
  
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
              
              {/* <div className="flex items-center justify-between">
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
              </div> */}
              
              <Button
                color="primary"
                type="submit"
                fullWidth
                isLoading={isLoading}
                startContent={!isLoading && <Icon icon="lucide:log-in" />}
              >
                {isLoading ? "Signing In..." : "Sign In"}
              </Button>
              
              
            </form>
          </CardBody>
        </Card>
      </motion.div>
    </div>
  );
};
 
 