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

interface LoginPageProps {
  onLogin: (email: string, password: string) => boolean;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [rememberMe, setRememberMe] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);
  const [errors, setErrors] = React.useState({ email: "", password: "" });
  const history = useHistory();
  
  const validateForm = () => {
    const newErrors = { email: "", password: "" };
    let isValid = true;
    
    if (!email) {
      newErrors.email = "Email is required";
      isValid = false;
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = "Email is invalid";
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
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsLoading(true);
    
    // Simulate API call
    setTimeout(() => {
      const success = onLogin(email, password);
      
      if (success) {
        addToast({
          title: "Login Successful",
          description: "Welcome to KubeSage Dashboard",
          color: "success"
        });
        history.push("/dashboard");
      } else {
        addToast({
          title: "Login Failed",
          description: "Invalid email or password",
          color: "danger"
        });
      }
      
      setIsLoading(false);
    }, 1000);
  };
  
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
                label="Email"
                placeholder="Enter your email"
                type="email"
                value={email}
                onValueChange={setEmail}
                startContent={<Icon icon="lucide:mail" className="text-foreground-400" />}
                isInvalid={!!errors.email}
                errorMessage={errors.email}
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
              
              <div className="relative my-4">
                <Divider className="my-4" />
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-content1 px-2 text-foreground-500 text-sm">
                  Or continue with
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-3">
                <Button 
                  variant="flat" 
                  className="bg-content2"
                  startContent={<Icon icon="logos:google-icon" />}
                  isDisabled={isLoading}
                >
                  Google
                </Button>
                <Button 
                  variant="flat" 
                  className="bg-content2"
                  startContent={<Icon icon="logos:github-icon" />}
                  isDisabled={isLoading}
                >
                  GitHub
                </Button>
                <Button 
                  variant="flat" 
                  className="bg-content2"
                  startContent={<Icon icon="logos:microsoft-icon" />}
                  isDisabled={isLoading}
                >
                  Microsoft
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
        
        <p className="text-center text-foreground-500 mt-4 text-sm">
          Don't have an account? <Button size="sm" variant="light" className="p-0">Sign up</Button>
        </p>
      </motion.div>
    </div>
  );
};