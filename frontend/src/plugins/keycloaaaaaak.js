import Keycloak from "keycloak-js";
import axios from "axios"; // Import axios for HTTP requests
 
const keycloakConfig = {
  url: import.meta.env.VITE_APP_KEYCLOCK_URL, // Replace with your Keycloak server URL
  realm: import.meta.env.VITE_APP_KEYCLOCK_REALM,
  clientId: import.meta.env.VITE_APP_KEYCLOCK_CLIENT
};
 
const keycloak = new Keycloak(keycloakConfig);
 
export const initializeKeycloak = (onAuthenticatedCallback) => {
  keycloak
    .init({ onLoad: "login-required", checkLoginIframe: false })
    .then((authenticated) => {
      if (authenticated) {
        console.log("User successfully authenticated.");
 
        // Set expiration time (assuming token expiration in milliseconds)
        const expireTime =
          new Date().getTime() + keycloak.tokenParsed.exp * 1000;
 
        // Store userInfo with value and expire keys
        const userInfo = {
          // value: {
          id: keycloak.tokenParsed.sub,
          userName: keycloak.tokenParsed.preferred_username,
          nickname: keycloak.tokenParsed.name || "Nickname",
          email: keycloak.tokenParsed.email || "N/A",
          roles: keycloak.tokenParsed.realm_access.roles || [],
          // },
          expire: expireTime
        };

        localStorage.setItem("userInfo", JSON.stringify(userInfo));
 
        // Store accessToken with value and expire keys
        const keycloakId = {
          value: keycloak.tokenParsed.sub,
          expire: expireTime,
        };
        localStorage.setItem("keycloakId", JSON.stringify(keycloakId));
 
        // Store accessToken with value and expire keys
        const accessToken = {
          value: keycloak.token,
          expire: expireTime,
        };
        localStorage.setItem("accessToken", JSON.stringify(accessToken));
 
        // Store refreshToken with value and expire keys
        const refreshToken = {
          value: keycloak.refreshToken,
          expire: expireTime,
        };
        localStorage.setItem("refreshToken", JSON.stringify(refreshToken));
 
 
        // Combine userInfo and accessToken into a single object
        const payload = {
          A1: userInfo, // user data
          A2: accessToken, // token data as an object
        };
        // svc.local.sut-srv:3000/api/v1/users
        // Send user data to Django backend to save or update the user
        axios
          .post(`/api/v1/save-keycloak-user/`, payload, {
            headers: {
              "Content-Type": "application/json",
            },
          })
          .then((response) => {
            console.log("User information stored:", response.data);
            onAuthenticatedCallback();
          })
          .catch((error) => {
            console.error("Error during API request:", error.response || error);
          });
 
      } else {
        console.warn("User not authenticated; reloading page for login.");
        window.location.reload();
      }
    })
    .catch((error) => {
      console.error("Keycloak authentication failed:", error);
    });
};
 
export function useKeycloak() {
  return keycloak;
}
 
// Logout function to log the user out from both the application and Keycloak
export function logoutUser() {
  keycloak.logout({
    redirectUri: import.meta.env.VITE_APP_UI_URL, // Redirect the user to this URL after logout
  });
}
 
// Example function to call the logoutUser function from your UI
export function handleUserLogout() {
  logoutUser();
}
 
export default keycloak;