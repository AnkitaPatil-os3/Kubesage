"use client";

import Link from 'next/link';
import { Navbar, Nav, Container, Button } from 'react-bootstrap';
import { useSession, signOut } from 'next-auth/react';
import useStore from '../../lib/store';

export default function MainNavbar() {
  const { data: session, status } = useSession();
  const { darkMode, toggleDarkMode } = useStore();
  
  return (
    <Navbar expand="lg" bg={darkMode ? 'dark' : 'light'} variant={darkMode ? 'dark' : 'light'}>
      <Container>
        <Navbar.Brand as={Link} href="/">
          KubeSage
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="ms-auto">
            {status === 'authenticated' ? (
              <>
                <Nav.Link as={Link} href="/me">Profile</Nav.Link>
                <Nav.Link as={Link} href="/clusters/list">Clusters</Nav.Link>
                <Nav.Link as={Link} href="/clusters/namespaces">Namespaces</Nav.Link>
                <Button 
                  variant="outline-primary" 
                  onClick={() => signOut({ callbackUrl: '/' })}
                  className="ms-2"
                >
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Nav.Link as={Link} href="/login">Login</Nav.Link>
                <Nav.Link as={Link} href="/register">Register</Nav.Link>
              </>
            )}
            <Button 
              variant="link" 
              onClick={toggleDarkMode}
              className="ms-2"
            >
              {darkMode ? '☀️' : '🌙'}
            </Button>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}
