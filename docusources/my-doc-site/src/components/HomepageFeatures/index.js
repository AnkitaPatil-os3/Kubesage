import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Smart Kubernetes Troubleshooting',
    Svg: require('@site/static/img/k8s-troubleshoot.png').default,
    description: (
      <>
        KubeSage leverages AI to auto-analyze logs, events, and metrics across your cluster to identify and resolve issues proactively.
      </>
    ),
  },
  {
    title: 'Multi-Cluster Observability',
    Svg: require('@site/static/img/multi-cluster.png').default,
    description: (
      <>
        Gain deep visibility into multiple clusters, monitor health, view workloads, and correlate events across environments in real-time.
      </>
    ),
  },
  {
    title: 'ChatOps for Kubernetes',
    Svg: require('@site/static/img/chatops.png').default,
    description: (
      <>
        Use natural language queries to interact with your Kubernetes clusters. KubeSage converts chat to actionable insights and commands.
      </>
    ),
  },
  {
    title: 'Secure & Compliant by Design',
    Svg: require('@site/static/img/security-shield.png').default,
    description: (
      <>
        KubeSage scans workloads for vulnerabilities, compliance violations, and misconfigurations, keeping your infrastructure audit-ready.
      </>
    ),
  },
  {
    title: 'Self-Healing Infrastructure',
    Svg: require('@site/static/img/auto-remediation.png').default,
    description: (
      <>
        Automatically detect issues and trigger pre-defined remediation workflows to restore system health without manual intervention.
      </>
    ),
  },
  {
    title: 'GitOps & FinOps Integrated',
    Svg: require('@site/static/img/gitops-finops.png').default,
    description: (
      <>
        Align deployments and cost optimization using GitOps for state tracking and FinOps insights to control Kubernetes spending.
      </>
    ),
  },
];

function Feature({Svg, title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <img src={Svg} className={styles.featureSvg} role="img" alt={title} />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
