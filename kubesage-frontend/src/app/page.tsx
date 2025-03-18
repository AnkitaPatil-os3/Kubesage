"use client";

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { Container, Row, Col, Card, Button } from 'react-bootstrap';

export default function HomePage() {
  const router = useRouter();
  const { status } = useSession();

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (status === 'authenticated') {
      router.push('/me');
    }
  }, [status, router]);

  return (
    <Container className="py-5">
      <Row className="justify-content-center text-center">
        <Col md={8}>
          <h1 className="display-4 mb-4">Welcome to KubeSage</h1>
          <p className="lead mb-5">
            A modern Kubernetes management platform with AI-powered insights
          </p>
          
          <Row className="gap-4 justify-content-center mb-5">
            <Button 
              variant="primary" 
              size="lg" 
              onClick={() => router.push('/login')}
              className="me-3"
              style={{ width: 'auto' }}
            >
              Login
            </Button>
            <Button 
              variant="outline-primary" 
              size="lg" 
              onClick={() => router.push('/register')}
              style={{ width: 'auto' }}
            >
              Register
            </Button>
          </Row>
        </Col>
      </Row>

      <Row className="mt-5">
        <Col md={4} className="mb-4">
          <Card>
            <Card.Body className="text-center">
              <h3>Manage Clusters</h3>
              <p>Upload and manage multiple Kubernetes clusters from a single dashboard</p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-4">
          <Card>
            <Card.Body className="text-center">
              <h3>AI Insights</h3>
              <p>Get intelligent recommendations to optimize your Kubernetes workloads</p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-4">
          <Card>
            <Card.Body className="text-center">
              <h3>Secure Access</h3>
              <p>Manage team access with fine-grained permissions and secure authentication</p>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
}
