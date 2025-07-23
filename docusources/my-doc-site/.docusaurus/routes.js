import React from 'react';
import ComponentCreator from '@docusaurus/ComponentCreator';

export default [
  {
    path: '/kubesagedocumentation/__docusaurus/debug',
    component: ComponentCreator('/kubesagedocumentation/__docusaurus/debug', '285'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/__docusaurus/debug/config',
    component: ComponentCreator('/kubesagedocumentation/__docusaurus/debug/config', '714'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/__docusaurus/debug/content',
    component: ComponentCreator('/kubesagedocumentation/__docusaurus/debug/content', 'd8d'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/__docusaurus/debug/globalData',
    component: ComponentCreator('/kubesagedocumentation/__docusaurus/debug/globalData', '19d'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/__docusaurus/debug/metadata',
    component: ComponentCreator('/kubesagedocumentation/__docusaurus/debug/metadata', '006'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/__docusaurus/debug/registry',
    component: ComponentCreator('/kubesagedocumentation/__docusaurus/debug/registry', 'c30'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/__docusaurus/debug/routes',
    component: ComponentCreator('/kubesagedocumentation/__docusaurus/debug/routes', '9e8'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog',
    component: ComponentCreator('/kubesagedocumentation/blog', 'ebb'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/2019/05/28/first-blog-post',
    component: ComponentCreator('/kubesagedocumentation/blog/2019/05/28/first-blog-post', '639'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/2019/05/29/long-blog-post',
    component: ComponentCreator('/kubesagedocumentation/blog/2019/05/29/long-blog-post', 'de6'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/2021/08/01/mdx-blog-post',
    component: ComponentCreator('/kubesagedocumentation/blog/2021/08/01/mdx-blog-post', '1aa'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/archive',
    component: ComponentCreator('/kubesagedocumentation/blog/archive', '9c4'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/authors',
    component: ComponentCreator('/kubesagedocumentation/blog/authors', '902'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/authors/all-sebastien-lorber-articles',
    component: ComponentCreator('/kubesagedocumentation/blog/authors/all-sebastien-lorber-articles', '2c8'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/authors/yangshun',
    component: ComponentCreator('/kubesagedocumentation/blog/authors/yangshun', '9a9'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags',
    component: ComponentCreator('/kubesagedocumentation/blog/tags', 'b88'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags/docusaurus',
    component: ComponentCreator('/kubesagedocumentation/blog/tags/docusaurus', '67b'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags/example',
    component: ComponentCreator('/kubesagedocumentation/blog/tags/example', 'a23'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags/facebook',
    component: ComponentCreator('/kubesagedocumentation/blog/tags/facebook', 'c1c'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags/hello',
    component: ComponentCreator('/kubesagedocumentation/blog/tags/hello', 'a1e'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags/introduction',
    component: ComponentCreator('/kubesagedocumentation/blog/tags/introduction', '201'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags/mdx',
    component: ComponentCreator('/kubesagedocumentation/blog/tags/mdx', 'd63'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags/news',
    component: ComponentCreator('/kubesagedocumentation/blog/tags/news', '37c'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags/update',
    component: ComponentCreator('/kubesagedocumentation/blog/tags/update', '021'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/tags/welcome',
    component: ComponentCreator('/kubesagedocumentation/blog/tags/welcome', '72f'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/blog/welcome',
    component: ComponentCreator('/kubesagedocumentation/blog/welcome', 'f3a'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/markdown-page',
    component: ComponentCreator('/kubesagedocumentation/markdown-page', '300'),
    exact: true
  },
  {
    path: '/kubesagedocumentation/docs',
    component: ComponentCreator('/kubesagedocumentation/docs', '324'),
    routes: [
      {
        path: '/kubesagedocumentation/docs',
        component: ComponentCreator('/kubesagedocumentation/docs', '780'),
        routes: [
          {
            path: '/kubesagedocumentation/docs',
            component: ComponentCreator('/kubesagedocumentation/docs', 'b4e'),
            routes: [
              {
                path: '/kubesagedocumentation/docs/api/',
                component: ComponentCreator('/kubesagedocumentation/docs/api/', 'e7d'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/chatlanggraph/',
                component: ComponentCreator('/kubesagedocumentation/docs/api/chatlanggraph/', '14d'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/chatlanggraph/chat-api',
                component: ComponentCreator('/kubesagedocumentation/docs/api/chatlanggraph/chat-api', 'a58'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/kubeconfig/',
                component: ComponentCreator('/kubesagedocumentation/docs/api/kubeconfig/', 'b2a'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/kubeconfig/get-clusters',
                component: ComponentCreator('/kubesagedocumentation/docs/api/kubeconfig/get-clusters', 'ed3'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/kubeconfig/update-yaml',
                component: ComponentCreator('/kubesagedocumentation/docs/api/kubeconfig/update-yaml', '01f'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/remediation/',
                component: ComponentCreator('/kubesagedocumentation/docs/api/remediation/', '120'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/remediation/trigger-remediation',
                component: ComponentCreator('/kubesagedocumentation/docs/api/remediation/trigger-remediation', 'e2c'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/security/',
                component: ComponentCreator('/kubesagedocumentation/docs/api/security/', 'a5c'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/security/scan',
                component: ComponentCreator('/kubesagedocumentation/docs/api/security/scan', '382'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/user/',
                component: ComponentCreator('/kubesagedocumentation/docs/api/user/', 'e31'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/user/login',
                component: ComponentCreator('/kubesagedocumentation/docs/api/user/login', '5c4'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/api/user/register',
                component: ComponentCreator('/kubesagedocumentation/docs/api/user/register', 'b8d'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/getting-started',
                component: ComponentCreator('/kubesagedocumentation/docs/getting-started', 'abe'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/intro',
                component: ComponentCreator('/kubesagedocumentation/docs/intro', 'abf'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/kubesagedocumentation/docs/tutorial-basics/congratulations',
                component: ComponentCreator('/kubesagedocumentation/docs/tutorial-basics/congratulations', '480'),
                exact: true
              },
              {
                path: '/kubesagedocumentation/docs/tutorial-basics/create-a-blog-post',
                component: ComponentCreator('/kubesagedocumentation/docs/tutorial-basics/create-a-blog-post', 'd18'),
                exact: true
              },
              {
                path: '/kubesagedocumentation/docs/tutorial-basics/create-a-document',
                component: ComponentCreator('/kubesagedocumentation/docs/tutorial-basics/create-a-document', '722'),
                exact: true
              },
              {
                path: '/kubesagedocumentation/docs/tutorial-basics/create-a-page',
                component: ComponentCreator('/kubesagedocumentation/docs/tutorial-basics/create-a-page', 'c03'),
                exact: true
              },
              {
                path: '/kubesagedocumentation/docs/tutorial-basics/deploy-your-site',
                component: ComponentCreator('/kubesagedocumentation/docs/tutorial-basics/deploy-your-site', '60d'),
                exact: true
              },
              {
                path: '/kubesagedocumentation/docs/tutorial-basics/markdown-features',
                component: ComponentCreator('/kubesagedocumentation/docs/tutorial-basics/markdown-features', '0a5'),
                exact: true
              },
              {
                path: '/kubesagedocumentation/docs/tutorial-extras/manage-docs-versions',
                component: ComponentCreator('/kubesagedocumentation/docs/tutorial-extras/manage-docs-versions', '927'),
                exact: true
              },
              {
                path: '/kubesagedocumentation/docs/tutorial-extras/translate-your-site',
                component: ComponentCreator('/kubesagedocumentation/docs/tutorial-extras/translate-your-site', 'dd8'),
                exact: true
              }
            ]
          }
        ]
      }
    ]
  },
  {
    path: '/kubesagedocumentation/',
    component: ComponentCreator('/kubesagedocumentation/', '8d6'),
    exact: true
  },
  {
    path: '*',
    component: ComponentCreator('*'),
  },
];
