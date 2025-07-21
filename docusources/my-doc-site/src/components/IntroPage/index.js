import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
// import Layout from '@theme/Layout';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: '🤖 AI-Powered ChatOps',
    description: 'Ask questions like "Why is my pod crashing?" and get real-time answers from your clusters.',
    icon: '🧠',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  },
  {
    title: '🔍 Multi-Cluster Explorer',
    description: 'Visualize and manage workloads across all your clusters with ease.',
    icon: '🌐',
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
  },
  {
    title: '🔧 Auto Remediation',
    description: 'Detect issues and apply predefined fixes automatically using AI.',
    icon: '⚡',
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
  },
  {
    title: '🛡️ Security & Compliance',
    description: 'Scan clusters for misconfigurations, CVEs, and policy violations.',
    icon: '🔒',
    gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
  },
  {
    title: '💰 FinOps Insights',
    description: 'Analyze resource usage and get cost recommendations.',
    icon: '📊',
    gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
  },
  {
    title: '🚀 Real-time Monitoring',
    description: 'Get real-time metrics, logs, and events from all your clusters.',
    icon: '📈',
    gradient: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)'
  }
];

const UserTypes = [
  { type: 'Developers', description: 'Self-service debugging', icon: '👨‍💻', color: '#FF6B6B' },
  { type: 'SREs', description: 'Real-time cluster visibility', icon: '🔧', color: '#4ECDC4' },
  { type: 'Security Engineers', description: 'Compliance & risk monitoring', icon: '🛡️', color: '#45B7D1' },
  { type: 'Platform Engineers', description: 'GitOps & multi-tenant management', icon: '⚙️', color: '#96CEB4' }
];

function HeroSection() {
  return (
    <header className={styles.heroBanner}>
      <div className="container">
        <div className={styles.heroContent}>
          <div className={styles.heroText}>
            <h1 className={styles.heroTitle}>
              Welcome to <span className={styles.brandName}>KubeSage</span>
            </h1>
            <p className={styles.heroSubtitle}>
              Your <strong>AI-powered Kubernetes Assistant</strong> designed to simplify 
              troubleshooting, observability, and operations across multiple clusters
            </p>
            <div className={styles.heroButtons}>
              <Link
                className={clsx('button button--primary button--lg', styles.getStartedBtn)}
                to="/docs/getting-started">
                Get Started
              </Link>
              <Link
                className={clsx('button button--secondary button--lg', styles.apiDocsBtn)}
                to="/docs/api">
                API Docs
              </Link>
            </div>
          </div>
          <div className={styles.heroAnimation}>
            <div className={styles.floatingCard}>
              <div className={styles.cardHeader}>
                <div className={styles.cardDots}>
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <span className={styles.cardTitle}>KubeSage Terminal</span>
              </div>
              <div className={styles.cardContent}>
                <div className={styles.terminalLine}>
                  <span className={styles.prompt}>$</span>
                  <span className={styles.command}>kubectl get pods --all-namespaces</span>
                </div>
                <div className={styles.terminalLine}>
                  <span className={styles.aiResponse}>AI: Found 3 failing pods. Analyzing...</span>
                </div>
                <div className={styles.terminalLine}>
                  <span className={styles.suggestion}>Suggestion: Memory limit exceeded</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

function FeatureCard({ title, description, icon, gradient, index }) {
  return (
    <div 
      className={styles.featureCard}
      style={{ 
        animationDelay: `${index * 0.1}s`,
        background: gradient
      }}
    >
      <div className={styles.featureIcon}>{icon}</div>
      <h3 className={styles.featureTitle}>{title}</h3>
      <p className={styles.featureDescription}>{description}</p>
    </div>
  );
}

function UserTypeCard({ type, description, icon, color }) {
  return (
    <div className={styles.userCard}>
      <div className={styles.userIcon} style={{ backgroundColor: color }}>
        {icon}
      </div>
      <h4 className={styles.userType}>{type}</h4>
      <p className={styles.userDescription}>{description}</p>
    </div>
  );
}

function FeaturesSection() {
  return (
    <section className={styles.featuresSection}>
      <div className="container">
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>⚡ Key Features at a Glance</h2>
          <p className={styles.sectionSubtitle}>
            Everything you need to manage Kubernetes clusters efficiently
          </p>
        </div>
        <div className={styles.featuresGrid}>
          {FeatureList.map((feature, idx) => (
            <FeatureCard key={idx} {...feature} index={idx} />
          ))}
        </div>
      </div>
    </section>
  );
}

function UserTypesSection() {
  return (
    <section className={styles.userTypesSection}>
      <div className="container">
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Built For Everyone</h2>
          <p className={styles.sectionSubtitle}>
            KubeSage adapts to your role and workflow
          </p>
        </div>
        <div className={styles.userTypesGrid}>
          {UserTypes.map((user, idx) => (
            <UserTypeCard key={idx} {...user} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ArchitectureSection() {
  return (
    <section className={styles.architectureSection}>
      <div className="container">
        <div className={styles.archContent}>
          <div className={styles.archText}>
            <h2 className={styles.sectionTitle}>🏗️ Modern Architecture</h2>
            <p className={styles.archDescription}>
              KubeSage connects to your clusters using secure kubeconfigs, 
              listens for real-time events, and uses modern technologies:
            </p>
            <ul className={styles.techList}>
              <li>Kubernetes Python Client</li>
              <li>OpenAI or local LLMs</li>
              <li>FastAPI + React</li>
              <li>Docusaurus Documentation</li>
            </ul>
          </div>
          <div className={styles.archDiagram}>
            <div className={styles.diagramNode} style={{ background: '#FF6B6B' }}>
              <span>UI/React</span>
            </div>
            <div className={styles.diagramArrow}>↓</div>
            <div className={styles.diagramNode} style={{ background: '#4ECDC4' }}>
              <span>⚡ FastAPI</span>
            </div>
            <div className={styles.diagramArrow}>↓</div>
            <div className={styles.diagramNode} style={{ background: '#45B7D1' }}>
              <span>AI Engine</span>
            </div>
            <div className={styles.diagramArrow}>↓</div>
            <div className={styles.diagramNode} style={{ background: '#96CEB4' }}>
              <span>☸️ Kubernetes</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className={styles.ctaSection}>
      <div className="container">
        <div className={styles.ctaContent}>
          <h2 className={styles.ctaTitle}>Ready to dive deeper?</h2>
          <p className={styles.ctaSubtitle}>
            Start your journey with KubeSage today
          </p>
          <div className={styles.ctaButtons}>
            <Link
              className={clsx('button button--primary button--lg', styles.ctaBtn)}
              to="/docs/getting-started">
              🚀 Getting Started
            </Link>
            <Link
              className={clsx('button button--outline button--lg', styles.ctaBtn)}
              to="/docs/api">
              📖 API Documentation
            </Link>
          </div>
          <p className={styles.ctaFooter}>
            Built with 💙 by DevOps for DevOps
          </p>
        </div>
      </div>
    </section>
  );
}

export default function IntroPage() {
  return (
    <div className={styles.introPageWrapper}>
      <HeroSection />
      <FeaturesSection />
      <UserTypesSection />
      <ArchitectureSection />
      <CTASection />
    </div>
  );
}