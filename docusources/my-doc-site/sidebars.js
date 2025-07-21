// @ts-check

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 * - create an ordered group of docs
 * - render a sidebar for each doc of that group
 * - provide next/previous navigation
 *
 * The sidebars can be generated from the filesystem, or explicitly defined here.
 *
 * Create as many sidebars as you want.
 *
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */
const sidebars = {
  tutorialSidebar: [
    'intro',
    
    'getting-started', // 👈 Add this line
    {
      type: 'category',
      label: 'API Docs',
      items: [
        'api/index',
        {
          type: 'category',
          label: 'User Service',
          items: [
            'api/user/index',
            'api/user/login',
            'api/user/register',
          ],
        },
        {
          type: 'category',
          label: 'Kubeconfig',
          items: [
            'api/kubeconfig/index',
            'api/kubeconfig/get-clusters',
            'api/kubeconfig/update-yaml',
          ],
        },
        {
          type: 'category',
          label: 'ChatLangGraph',
          items: [
            'api/chatlanggraph/index',
            'api/chatlanggraph/chat-api',
          ],
        },
        {
          type: 'category',
          label: 'Remediation',
          items: [
            'api/remediation/index',
            'api/remediation/trigger-remediation',
          ],
        },
        {
          type: 'category',
          label: 'Security',
          items: [
            'api/security/index',
            'api/security/scan',
          ],
        },
      ],
    },
  ],
  
};

export default sidebars;
