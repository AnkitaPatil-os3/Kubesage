import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { userService } from '../../../../lib/api';

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        try {
          // Call the login API
          const response = await userService.login(
            credentials.username, 
            credentials.password
          );
          
          if (response.access_token) {
            return {
              id: response.user_id,
              name: credentials.username,
              accessToken: response.access_token,
              expiresAt: response.expires_at,
              isAdmin: response.is_admin || false,
            };
          }
          
          return null;
        } catch (error) {
          console.error('Auth error:', error);
          return null;
        }
      }
    })
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.expiresAt = user.expiresAt;
        token.isAdmin = user.isAdmin;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.expiresAt = token.expiresAt;
      session.user.isAdmin = token.isAdmin;
      return session;
    }
  },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 24 * 60 * 60, // 24 hours
  },
});

export { handler as GET, handler as POST };
