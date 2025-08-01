export type UserRole = 'super_admin' | 'platform_engineer' | 'devops' | 'developer' | 'security_engineer';

export const rolePermissions: Record<UserRole, string[]> = {
    super_admin: ['all'],

    platform_engineer: [
        'dashboard',
        'clusters',
        'applications',
        'workloads',
        'analyze',
        'chatops',
        'insights',
        'observability',
        'carbon-emission',
        'cost',
        'backup',
        'security',
        'settings',
        'integrations',
        'help',
    ],

    devops: [
        'dashboard',
        'clusters',
        'applications',
        'workloads',
        'chatops',
        'insights',
        'observability',
        'cost',
        'remediations',
        'backup',
        'settings',
        'integrations',
        'help',
    ],

    developer: [
        'dashboard',
        'applications',
        'workloads',
        'observability',
        'analyze',
        'chatops',
        'insights',
        'settings',
        'help',
    ],

    security_engineer: [
        'dashboard',
        'security',
        'secrets',
        'compliance',
        'remediations',
        'anomalies',
        'settings',
        'help',
    ]
};
