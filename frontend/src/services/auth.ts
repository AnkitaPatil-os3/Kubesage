 class AuthService {
    // private baseURL = 'https://10.0.2.29:8001';
    private tokenKey = 'access_token';
    private refreshTokenKey = 'refresh_token';
    private userInfoKey = 'user_info';
    private sessionIdKey = 'session_id';
  
    // Generate session ID
    private generateSessionId(): string {
      return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    }
  
    // Get session ID
    getSessionId(): string | null {
      return localStorage.getItem(this.sessionIdKey);
    }
  
    // Get access token
    getAccessToken(): string | null {
      return localStorage.getItem(this.tokenKey);
    }
  
    // Get refresh token
    getRefreshToken(): string | null {
      return localStorage.getItem(this.refreshTokenKey);
    }
  
    // Get cached user info
    getCachedUserInfo(): any | null {
      try {
        const userInfo = localStorage.getItem(this.userInfoKey);
        return userInfo ? JSON.parse(userInfo) : null;
      } catch (error) {
        console.error('Error parsing cached user info:', error);
        return null;
      }
    }
  
    // Store user info in cache
    private setCachedUserInfo(userInfo: any): void {
      localStorage.setItem(this.userInfoKey, JSON.stringify(userInfo));
    }
  
    // Clear all auth data
    clearAuthData(): void {
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem(this.refreshTokenKey);
      localStorage.removeItem(this.userInfoKey);
      localStorage.removeItem(this.sessionIdKey);
      localStorage.removeItem('roles');
      localStorage.removeItem('username');
    }
  
    // Check if user is authenticated
    isAuthenticated(): boolean {
      const token = this.getAccessToken();
      const sessionId = this.getSessionId();
      return !!(token && sessionId);
    }
  
    // Check if token is expired
    private isTokenExpired(token: string): boolean {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const currentTime = Math.floor(Date.now() / 1000);
        return payload.exp < currentTime;
      } catch (error) {
        console.error('Error checking token expiration:', error);
        return true;
      }
    }
  
    // Refresh access token
    private async refreshAccessToken(): Promise<boolean> {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) {
        return false;
      }
  
      try {
        const response = await fetch(`/api/v1.0/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
  
        if (response.ok) {
          const data = await response.json();
          localStorage.setItem(this.tokenKey, data.access_token);
          if (data.refresh_token) {
            localStorage.setItem(this.refreshTokenKey, data.refresh_token);
          }
          return true;
        } else {
          console.error('Token refresh failed:', response.statusText);
          return false;
        }
      } catch (error) {
        console.error('Token refresh error:', error);
        return false;
      }
    }
  
    // Make authenticated request
    async authenticatedRequest(url: string, options: RequestInit = {}): Promise<Response> {
      let token = this.getAccessToken();
      
      if (!token) {
        throw new Error('No access token available');
      }
  
      // Check if token is expired and try to refresh
      if (this.isTokenExpired(token)) {
        console.log('Token expired, attempting refresh...');
        const refreshed = await this.refreshAccessToken();
        if (!refreshed) {
          this.clearAuthData();
          throw new Error('Session expired. Please login again.');
        }
        token = this.getAccessToken();
      }
  
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      };
  
      const response = await fetch(url, {
        ...options,
        headers,
      });
  
      // Handle 401 responses
      if (response.status === 401) {
        console.log('Received 401, attempting token refresh...');
        const refreshed = await this.refreshAccessToken();
        if (refreshed) {
          // Retry the request with new token
          const newToken = this.getAccessToken();
          const retryResponse = await fetch(url, {
            ...options,
            headers: {
              ...headers,
              'Authorization': `Bearer ${newToken}`,
            },
          });
          
          if (retryResponse.status === 401) {
            this.clearAuthData();
            throw new Error('Session expired. Please login again.');
          }
          
          return retryResponse;
        } else {
          this.clearAuthData();
          throw new Error('Session expired. Please login again.');
        }
      }
  
      return response;
    }
  
    // Login method
    async login(username: string, password: string): Promise<{ success: boolean; user?: any; error?: string }> {
        try {
          const response = await fetch(`/api/v1.0/auth/token`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
              username: username,
              password: password,
            }).toString(),
          });
    
          if (response.ok) {
            const data = await response.json();
            
            // Store tokens
            localStorage.setItem(this.tokenKey, data.access_token);
            if (data.refresh_token) {
              localStorage.setItem(this.refreshTokenKey, data.refresh_token);
            }
            
            // Generate and store session ID
            const sessionId = this.generateSessionId();
            localStorage.setItem(this.sessionIdKey, sessionId);
    
            // Fetch user info
            try {
              const userResponse = await fetch(`/api/v1.0/users/me`, {
                headers: {
                  'Authorization': `Bearer ${data.access_token}`,
                  'Content-Type': 'application/json',
                },
              });
    
              if (userResponse.ok) {
                const userData = await userResponse.json();
                this.setCachedUserInfo(userData);
                
                return {
                  success: true,
                  user: userData,
                };
              } else {
                console.error('Failed to fetch user info:', userResponse.statusText);
                return {
                  success: true,
                  user: { username }, // Fallback user object
                };
              }
            } catch (userError) {
              console.error('Error fetching user info:', userError);
              return {
                success: true,
                user: { username }, // Fallback user object
              };
            }
          } else {
            const errorData = await response.json().catch(() => ({}));
            let errorMessage = errorData.detail || 'Invalid username or password';
            
            // Map "database connection failed" to more user-friendly message for login failures
            if (errorMessage.toLowerCase().includes('database connection failed')) {
              errorMessage = 'Incorrect Username or Password';
            }
            
            return {
              success: false,
              error: errorMessage,
            };
          }
        } catch (error: any) {
          console.error('Login error:', error);
          return {
            success: false,
            error: error.message || 'Network error occurred',
          };
        }
      }
    
      // Get current user
      async getCurrentUser(): Promise<any | null> {
        try {
          // First check cache
          const cachedUser = this.getCachedUserInfo();
          if (cachedUser) {
            return cachedUser;
          }
    
          // If no cache, fetch from server
          const response = await this.authenticatedRequest(`/api/v1.0/users/me`);
          
          if (response.ok) {
            const userData = await response.json();
            this.setCachedUserInfo(userData);
            return userData;
          } else {
            console.error('Failed to get current user:', response.statusText);
            return null;
          }
        } catch (error) {
          console.error('Error getting current user:', error);
          return null;
        }
      }
    
      // Check admin status
      async checkAdminStatus(): Promise<{ is_admin: boolean; roles?: string }> {
        try {
          const response = await this.authenticatedRequest(`/api/v1.0/auth/check-admin`);
          
          if (response.ok) {
            const data = await response.json();
            return {
              is_admin: data.is_admin,
              roles: data.roles,
            };
          } else {
            return { is_admin: false };
          }
        } catch (error) {
          console.error('Error checking admin status:', error);
          return { is_admin: false };
        }
      }
    
      // Logout method
      async logout(): Promise<{ success: boolean; error?: string }> {
        try {
          const token = this.getAccessToken();
          
          if (token) {
            // Call logout endpoint
            const response = await fetch(`/api/v1.0/auth/logout`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
            });
    
            if (!response.ok) {
              console.warn('Logout endpoint failed, but continuing with local cleanup');
            }
          }
    
          // Always clear local data regardless of server response
          this.clearAuthData();
          
          return { success: true };
        } catch (error: any) {
          console.error('Logout error:', error);
          
          // Even if logout fails, clear local data
          this.clearAuthData();
          
          return {
            success: true, // Return success since we cleared local data
            error: error.message,
          };
        }
      }
    
      // Validate session
      async validateSession(): Promise<boolean> {
        try {
          if (!this.isAuthenticated()) {
            return false;
          }
    
          const user = await this.getCurrentUser();
          return !!user;
        } catch (error) {
          console.error('Session validation error:', error);
          return false;
        }
      }
    }
    
    const authService = new AuthService();
    export default authService;
    
 